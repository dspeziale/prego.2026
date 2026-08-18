"""Registro dei download dell'app Android.

Una riga JSON per ogni download in `data/downloads.jsonl`: il formato
append-only sopporta le scritture concorrenti molto meglio di un unico
file JSON riscritto da capo ogni volta.

Attenzione: su Vercel il filesystem è in sola lettura, quindi le
registrazioni non vengono conservate. La pagina di amministrazione lo
segnala esplicitamente invece di mostrare un registro vuoto e mentire.
"""

import json
import logging
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

MAX_USER_AGENT = 300
RECENT_DAYS = 14

# (etichetta, marcatore nello User-Agent): vince il primo che combacia,
# quindi l'ordine conta perché Edge, Opera e Samsung Internet si
# dichiarano anche Chrome, e Chrome si dichiara anche Safari.
BROWSERS: Tuple[Tuple[str, str], ...] = (
    ("Edge", "Edg/"),
    ("Opera", "OPR/"),
    ("Samsung Internet", "SamsungBrowser"),
    ("Firefox", "Firefox/"),
    ("Chrome", "Chrome/"),
    ("Safari", "Safari/"),
)

SYSTEMS: Tuple[Tuple[str, str], ...] = (
    ("Android", "Android"),
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Windows", "Windows"),
    ("macOS", "Mac OS X"),
    ("Linux", "Linux"),
)


def describe(user_agent: str) -> str:
    """Sistema e browser leggibili, dedotti dallo User-Agent."""
    agent = user_agent or ""
    system = next((label for label, mark in SYSTEMS if mark in agent), None)
    browser = next((label for label, mark in BROWSERS if mark in agent), None)
    parts = [part for part in (system, browser) if part]
    return " · ".join(parts) if parts else "Sconosciuto"


class DownloadStore:
    """Registro append-only dei download dell'app Android."""

    def __init__(self, path: Path, read_only: bool = False) -> None:
        self._path = path
        self._read_only = read_only

    @property
    def writable(self) -> bool:
        """False quando il deploy non consente di annotare i download."""
        return not self._read_only

    def record(self, ip: str, user_agent: str, filename: str) -> bool:
        """Annota un download; False se non è stato possibile scrivere."""
        entry = {
            "quando": datetime.now().isoformat(timespec="seconds"),
            "ip": (ip or "").strip(),
            "user_agent": (user_agent or "")[:MAX_USER_AGENT],
            "file": filename,
        }
        line = json.dumps(entry, ensure_ascii=False)
        if self._read_only:
            # Il filesystem non è scrivibile (Vercel): la riga finisce
            # comunque nel log del server, da dove si può recuperare e
            # riversare nel registro quando serve.
            logger.info("DOWNLOAD %s", line)
            return False
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line + chr(10))
        except OSError as exc:
            logger.warning("Download non registrato (%s)", exc)
            return False
        return True

    def entries(self) -> List[Dict[str, Any]]:
        """I download dal più recente, con la descrizione del dispositivo."""
        rows: List[Dict[str, Any]] = []
        if not self._path.is_file():
            return rows
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Registro dei download non leggibile: %s", exc)
            return rows
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Riga ignorata nel registro: %.60s", line)
                continue
            row["dispositivo"] = describe(row.get("user_agent", ""))
            rows.append(row)
        rows.sort(key=lambda row: row.get("quando", ""), reverse=True)
        return rows

    @staticmethod
    def summary(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Numeri di sintesi calcolati sulle righe già caricate."""
        per_day = Counter(
            row.get("quando", "")[:10] for row in entries if row.get("quando")
        )
        addresses = {row.get("ip") for row in entries if row.get("ip")}
        return {
            "totale": len(entries),
            "indirizzi": len(addresses),
            "oggi": per_day.get(date.today().isoformat(), 0),
            "ultimo": entries[0].get("quando") if entries else None,
            # Dal giorno più recente a scendere, per il grafico a barre.
            "per_giorno": sorted(per_day.items(), reverse=True)[:RECENT_DAYS],
            "massimo_giornaliero": max(per_day.values()) if per_day else 0,
            "dispositivi": Counter(
                row.get("dispositivo", "Sconosciuto") for row in entries
            ).most_common(),
        }
