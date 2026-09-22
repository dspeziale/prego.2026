"""Ping di avvio dell'app Android e statistiche d'uso.

A ogni avvio l'app manda `POST /api/ping` con un identificativo casuale
dell'installazione (nessun dato personale), versione, Android, modello e
lingua. Su Vercel il filesystem è in sola lettura, quindi i ping vanno
in un Vercel Blob privato (token `BLOB_READ_WRITE_TOKEN`), raggiunto via
REST senza dipendenze aggiuntive:

    installazioni/<id>/<versione>.json   stato dell'installazione: riscritto a
                                          ogni avvio, così `uploadedAt` è
                                          l'ultimo utilizzo con quella versione
    avvii/<AAAA-MM-GG>/<id>-<ora>.json   un file per avvio (conteggi per giorno)

Le statistiche si calcolano quasi solo dall'elenco dei file (percorso e
data di caricamento): i contenuti si leggono solo per gli ultimi ping.
Senza token lo store è disattivato: i ping finiscono nel log e la
pagina lo dice.
"""

import json
import logging
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
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
    """Errore dello store dei ping (rete o API)."""


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


class PingStore:
    """Ping su Vercel Blob (privato). Con token vuoto è disattivato."""

    def __init__(self, token: str) -> None:
        self._token = (token or "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self._token)

    # ------------------------------------------------------------------
    # scrittura
    # ------------------------------------------------------------------

    def record(self, ping: Dict[str, Any], now: Optional[datetime] = None) -> bool:
        """Registra un avvio; False se lo store non è configurato."""
        now = now or datetime.now(timezone.utc)
        stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = {**ping, "quando": stamp}
        if not self.enabled:
            logger.info("PING %s", json.dumps(entry, ensure_ascii=False))
            return False
        body = json.dumps(entry, ensure_ascii=False).encode("utf-8")
        version_slug = ping["versione"].replace(".", "_")
        self._put(f"installazioni/{ping['id']}/{version_slug}.json", body)
        day = now.strftime("%Y-%m-%d")
        clock = now.strftime("%H%M%S")
        self._put(f"avvii/{day}/{ping['id']}-{clock}.json", body)
        return True

    # ------------------------------------------------------------------
    # lettura
    # ------------------------------------------------------------------

    def stats(self, today: Optional[date] = None) -> Dict[str, Any]:
        """Numeri per la pagina di amministrazione."""
        today = today or datetime.now(timezone.utc).date()
        installs = self._list("installazioni/")
        # per installazione: ultima versione usata e ultimo avvio
        latest: Dict[str, Dict[str, Any]] = {}
        for blob in installs:
            parts = blob["pathname"].split("/")
            if len(parts) != 3:
                continue
            install_id, version_file = parts[1], parts[2]
            version = version_file[:-5].replace("_", ".")
            seen = _parse_time(blob.get("uploadedAt"))
            current = latest.get(install_id)
            if current is None or (seen and seen > current["ultimo"]):
                latest[install_id] = {"ultimo": seen, "versione": version, "url": blob["url"]}

        def active_since(days: int) -> int:
            limit = datetime.combine(today - timedelta(days=days - 1), datetime.min.time(), timezone.utc)
            return sum(1 for item in latest.values() if item["ultimo"] and item["ultimo"] >= limit)

        per_day: List[Dict[str, Any]] = []
        for offset in range(RECENT_DAYS):
            day = today - timedelta(days=offset)
            launches = self._list(f"avvii/{day.isoformat()}/")
            ids = {blob["pathname"].split("/")[-1].rsplit("-", 1)[0] for blob in launches}
            per_day.append({"giorno": day.isoformat(), "avvii": len(launches), "utenti": len(ids)})

        recent_blobs = sorted(
            self._list(f"avvii/{today.isoformat()}/")
            + self._list(f"avvii/{(today - timedelta(days=1)).isoformat()}/"),
            key=lambda blob: blob.get("uploadedAt", ""), reverse=True,
        )[:RECENT_PINGS]
        recent = []
        for blob in recent_blobs:
            try:
                recent.append(self._get_json(blob["url"]))
            except PingError as exc:
                logger.warning("Ping non leggibile %s: %s", blob["pathname"], exc)
        for item in recent:
            item["android_label"] = f"Android {item.get('android') or '?'}"

        versions = Counter(item["versione"] for item in latest.values())
        android = Counter(item.get("android") or "?" for item in recent)
        return {
            "installazioni": len(latest),
            "attivi_oggi": active_since(1),
            "attivi_7": active_since(7),
            "attivi_30": active_since(30),
            "avvii_oggi": per_day[0]["avvii"] if per_day else 0,
            "per_giorno": per_day,
            "massimo_giornaliero": max((d["avvii"] for d in per_day), default=0),
            "versioni": versions.most_common(),
            "android": android.most_common(),
            "recenti": recent,
            "ultimo": max((item["ultimo"] for item in latest.values() if item["ultimo"]), default=None),
        }

    # ------------------------------------------------------------------
    # REST Vercel Blob
    # ------------------------------------------------------------------

    def _headers(self, **extra: str) -> Dict[str, str]:
        return {
            "authorization": f"Bearer {self._token}",
            "x-api-version": BLOB_API_VERSION,
            **extra,
        }

    def _put(self, pathname: str, body: bytes) -> None:
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

    def _list(self, prefix: str) -> List[Dict[str, Any]]:
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
                raise PingError(f"Blob LIST {prefix}: HTTP {response.status_code}")
            data = response.json()
            blobs.extend(data.get("blobs") or [])
            cursor = data.get("cursor")
            if not data.get("hasMore") or not cursor:
                return blobs

    def _get_json(self, url: str) -> Dict[str, Any]:
        try:
            response = requests.get(url, headers=self._headers(), timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise PingError(str(exc)) from exc


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
