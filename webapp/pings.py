"""Ping di avvio dell'app Android e statistiche d'uso.

A ogni avvio l'app manda `POST /api/ping` con un identificativo casuale
dell'installazione (nessun dato personale), versione, Android, modello e
lingua. I ping vanno in un archivio con questo schema di percorsi:

    installazioni/<id>/<versione>.json   stato dell'installazione: riscritto a
                                          ogni avvio, così la data del file è
                                          l'ultimo utilizzo con quella versione
    avvii/<AAAA-MM-GG>/<id>-<ora>.json   un file per avvio (conteggi per giorno)

Due archivi possibili, scelti in app.py:

* `FileBackend`: una cartella su disco (`PREGO_PINGS_DIR`, es. un volume
  persistente su Coolify). Nessuna dipendenza esterna.
* `BlobBackend`: un Vercel Blob privato via REST (`BLOB_READ_WRITE_TOKEN`),
  per i deploy con filesystem in sola lettura.

Le statistiche si calcolano quasi solo dagli elenchi (percorso e data):
i contenuti si leggono solo per gli ultimi ping. Senza archivio i ping
finiscono nel log e la pagina lo dice.
"""

import json
import logging
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

BLOB_API = "https://blob.vercel-storage.com"
BLOB_API_VERSION = "7"
TIMEOUT = 8

_RE_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_RE_VERSION = re.compile(r"^\d{1,3}(\.\d{1,3}){0,3}$")
MAX_FIELD = 64
RECENT_DAYS = 14
RECENT_PINGS = 20


class PingError(Exception):
    """Errore dell'archivio dei ping (disco, rete o API)."""


def clean_ping(payload: Any) -> Optional[Dict[str, Any]]:
    """Valida e normalizza il corpo del ping; None se inaccettabile."""
    if not isinstance(payload, dict):
        return None
    install_id = str(payload.get("id") or "").strip().lower()
    version = str(payload.get("versione") or "").strip()
    if not _RE_ID.match(install_id) or not _RE_VERSION.match(version):
        return None

    def text(key: str) -> str:
        value = payload.get(key)
        return str(value).strip()[:MAX_FIELD] if value is not None else ""

    def number(key: str) -> int:
        try:
            return max(0, min(int(payload.get(key) or 0), 10_000_000))
        except (TypeError, ValueError):
            return 0

    return {
        "id": install_id,
        "versione": version,
        "versionCode": number("versionCode"),
        "android": text("android"),
        "sdk": number("sdk"),
        "modello": text("modello"),
        "lingua": text("lingua")[:16],
        "avvii": number("avvii"),
    }


# --------------------------------------------------------------------------
# Archivi: stessa interfaccia (put / list / get_json)
# --------------------------------------------------------------------------

class FileBackend:
    """Archivio su disco: un file per percorso, data = mtime del file."""

    name = "cartella"

    def __init__(self, directory: Path) -> None:
        self._root = Path(directory)

    def describe(self) -> str:
        return f"cartella {self._root}"

    def put(self, pathname: str, body: bytes) -> None:
        target = self._root / pathname
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_bytes(body)
            tmp.replace(target)
        except OSError as exc:
            raise PingError(f"scrittura {target}: {exc}") from exc

    def list(self, prefix: str) -> List[Dict[str, Any]]:
        base = self._root / prefix
        if not base.is_dir():
            return []
        entries: List[Dict[str, Any]] = []
        try:
            for path in base.rglob("*.json"):
                stat = path.stat()
                entries.append({
                    "pathname": path.relative_to(self._root).as_posix(),
                    "uploadedAt": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                    .strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "url": str(path),
                })
        except OSError as exc:
            raise PingError(f"lettura {base}: {exc}") from exc
        return entries

    def get_json(self, ref: str) -> Dict[str, Any]:
        try:
            return json.loads(Path(ref).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise PingError(str(exc)) from exc


class BlobBackend:
    """Vercel Blob privato via REST."""

    name = "Vercel Blob"

    def __init__(self, token: str) -> None:
        self._token = token.strip()

    def describe(self) -> str:
        return "Vercel Blob"

    def _headers(self, **extra: str) -> Dict[str, str]:
        return {
            "authorization": f"Bearer {self._token}",
            "x-api-version": BLOB_API_VERSION,
            **extra,
        }

    def put(self, pathname: str, body: bytes) -> None:
        try:
            response = requests.put(
                f"{BLOB_API}/{pathname}", data=body, timeout=TIMEOUT,
                headers=self._headers(**{
                    "x-content-type": "application/json",
                    "x-add-random-suffix": "0",
                    "x-allow-overwrite": "1",
                    "x-vercel-blob-access": "private",
                }),
            )
        except requests.RequestException as exc:
            raise PingError(f"Blob non raggiungibile: {exc}") from exc
        if response.status_code != 200:
            raise PingError(f"Blob PUT {pathname}: HTTP {response.status_code} {response.text[:120]}")

    def list(self, prefix: str) -> List[Dict[str, Any]]:
        blobs: List[Dict[str, Any]] = []
        cursor = None
        while True:
            params = {"prefix": prefix, "limit": "1000"}
            if cursor:
                params["cursor"] = cursor
            try:
                response = requests.get(f"{BLOB_API}/", params=params,
                                        headers=self._headers(), timeout=TIMEOUT)
            except requests.RequestException as exc:
                raise PingError(f"Blob non raggiungibile: {exc}") from exc
            if response.status_code != 200:
                raise PingError(
                    f"Blob LIST {prefix}: HTTP {response.status_code} "
                    f"({response.text[:80]}). Token di un altro store o store rimosso?"
                )
            data = response.json()
            blobs.extend(data.get("blobs") or [])
            cursor = data.get("cursor")
            if not data.get("hasMore") or not cursor:
                return blobs

    def get_json(self, ref: str) -> Dict[str, Any]:
        try:
            response = requests.get(ref, headers=self._headers(), timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise PingError(str(exc)) from exc


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------

class PingStore:
    """Registra i ping e calcola le statistiche su un archivio."""

    def __init__(self, backend: Optional[Any] = None) -> None:
        self._backend = backend

    @property
    def enabled(self) -> bool:
        return self._backend is not None

    @property
    def descrizione(self) -> str:
        return self._backend.describe() if self._backend else "nessun archivio"

    def record(self, ping: Dict[str, Any], now: Optional[datetime] = None) -> bool:
        """Registra un avvio; False se non c'è archivio (solo log)."""
        now = now or datetime.now(timezone.utc)
        entry = {**ping, "quando": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
        if not self.enabled:
            logger.info("PING %s", json.dumps(entry, ensure_ascii=False))
            return False
        body = json.dumps(entry, ensure_ascii=False).encode("utf-8")
        version_slug = ping["versione"].replace(".", "_")
        self._backend.put(f"installazioni/{ping['id']}/{version_slug}.json", body)
        # ora con i microsecondi: due avvii nello stesso secondo non si
        # sovrascrivono
        self._backend.put(
            f"avvii/{now.strftime('%Y-%m-%d')}/{ping['id']}-{now.strftime('%H%M%S%f')}.json", body
        )
        return True

    def stats(self, today: Optional[date] = None) -> Dict[str, Any]:
        """Numeri per la pagina di amministrazione."""
        if not self.enabled:
            raise PingError("archivio dei ping non configurato")
        today = today or datetime.now(timezone.utc).date()
        latest: Dict[str, Dict[str, Any]] = {}
        for entry in self._backend.list("installazioni/"):
            parts = entry["pathname"].split("/")
            if len(parts) != 3:
                continue
            install_id, version_file = parts[1], parts[2]
            version = version_file[:-5].replace("_", ".")
            seen = _parse_time(entry.get("uploadedAt"))
            current = latest.get(install_id)
            if current is None or (seen and (current["ultimo"] is None or seen > current["ultimo"])):
                latest[install_id] = {"ultimo": seen, "versione": version}

        def active_since(days: int) -> int:
            limit = datetime.combine(today - timedelta(days=days - 1), datetime.min.time(), timezone.utc)
            return sum(1 for item in latest.values() if item["ultimo"] and item["ultimo"] >= limit)

        per_day: List[Dict[str, Any]] = []
        for offset in range(RECENT_DAYS):
            day = today - timedelta(days=offset)
            launches = self._backend.list(f"avvii/{day.isoformat()}/")
            ids = {e["pathname"].split("/")[-1].rsplit("-", 1)[0] for e in launches}
            per_day.append({"giorno": day.isoformat(), "avvii": len(launches), "utenti": len(ids)})

        recent_entries = sorted(
            self._backend.list(f"avvii/{today.isoformat()}/")
            + self._backend.list(f"avvii/{(today - timedelta(days=1)).isoformat()}/"),
            key=lambda e: e.get("uploadedAt", ""), reverse=True,
        )[:RECENT_PINGS]
        recent = []
        for entry in recent_entries:
            try:
                recent.append(self._backend.get_json(entry["url"]))
            except PingError as exc:
                logger.warning("Ping non leggibile %s: %s", entry["pathname"], exc)
        recent.sort(key=lambda p: p.get("quando", ""), reverse=True)

        return {
            "installazioni": len(latest),
            "attivi_oggi": active_since(1),
            "attivi_7": active_since(7),
            "attivi_30": active_since(30),
            "avvii_oggi": per_day[0]["avvii"] if per_day else 0,
            "per_giorno": per_day,
            "massimo_giornaliero": max((d["avvii"] for d in per_day), default=0),
            "versioni": Counter(item["versione"] for item in latest.values()).most_common(),
            "android": Counter(p.get("android") or "?" for p in recent).most_common(),
            "recenti": recent,
            "ultimo": max((item["ultimo"] for item in latest.values() if item["ultimo"]), default=None),
        }


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
