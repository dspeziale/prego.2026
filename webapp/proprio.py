"""Archivio del Proprio biennale (letture proprie dei santi).

Un file JSON per ricorrenza, nominato giorno-mese (es. 21-01.json)
nella cartella `proprio/` alla radice del progetto.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MONTHS_IT = (
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
)

READING_LABELS = (
    "Prima Lettura", "Seconda Lettura", "Terza Lettura", "Quarta Lettura",
    "Vangelo",
)

RANKS = (
    "Solennità", "Festa", "Memoria", "Memoria facoltativa", "Commemorazione",
)

_RE_CODE = re.compile(r"^(\d{2})-(\d{2})$")


class ProprioStore:
    """Persistenza dei giorni del Proprio su file giorno-mese.json."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    @staticmethod
    def code(day: int, month: int) -> str:
        """Codice giorno-mese del file (es. '21-01')."""
        return f"{day:02d}-{month:02d}"

    @staticmethod
    def is_valid_code(code: str) -> bool:
        match = _RE_CODE.match(code)
        if not match:
            return False
        day, month = int(match.group(1)), int(match.group(2))
        return 1 <= day <= 31 and 1 <= month <= 12

    def path_for(self, code: str) -> Path:
        return self._directory / f"{code}.json"

    def load(self, code: str) -> Optional[Dict[str, Any]]:
        """Carica una ricorrenza; None se assente o non valida."""
        if not self.is_valid_code(code):
            return None
        path = self.path_for(code)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Proprio non leggibile (%s): %s", path, exc)
            return None

    def save(self, entry: Dict[str, Any]) -> Path:
        """Scrive la ricorrenza e restituisce il percorso del file."""
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self.path_for(entry["data"])
        payload = json.dumps(entry, ensure_ascii=False, indent=4)
        path.write_text(payload + "\n", encoding="utf-8", newline="\n")
        logger.info("Scritto %s", path)
        return path

    def delete(self, code: str) -> bool:
        """Elimina la ricorrenza; True se il file esisteva."""
        if not self.is_valid_code(code):
            return False
        path = self.path_for(code)
        if path.is_file():
            path.unlink()
            logger.info("Eliminato %s", path)
            return True
        return False

    def list_entries(self) -> List[Dict[str, Any]]:
        """Tutte le ricorrenze, ordinate per mese e giorno."""
        entries = []
        if not self._directory.is_dir():
            return entries
        for path in self._directory.glob("*.json"):
            if not self.is_valid_code(path.stem):
                continue
            entry = self.load(path.stem)
            if entry:
                entries.append(entry)
        return sorted(
            entries,
            key=lambda e: (e.get("mese_numero", 0), e.get("giorno", 0)),
        )

    @staticmethod
    def from_form(form: Dict[str, str]) -> Dict[str, Any]:
        """Costruisce la ricorrenza dai campi della form.

        Solleva ValueError con un messaggio leggibile se i dati
        obbligatori mancano o non sono validi.
        """
        try:
            day = int(form.get("giorno", ""))
            month = int(form.get("mese", ""))
        except ValueError:
            raise ValueError("Giorno o mese non validi.")
        if not (1 <= day <= 31 and 1 <= month <= 12):
            raise ValueError("Giorno o mese fuori intervallo.")
        saint = (form.get("santo") or "").strip()
        if not saint:
            raise ValueError("Il nome del santo è obbligatorio.")
        readings = []
        for index, label in enumerate(READING_LABELS, start=1):
            reading = {
                "titolo": label,
                "riferimento": (form.get(f"lettura_{index}_riferimento") or "").strip(),
                "sottotitolo": (form.get(f"lettura_{index}_sottotitolo") or "").strip(),
                "fonte": (form.get(f"lettura_{index}_fonte") or "").strip(),
                "testo": (form.get(f"lettura_{index}_testo") or "").strip(),
                "responsorio": (form.get(f"lettura_{index}_responsorio") or "").strip(),
            }
            if reading["riferimento"] or reading["testo"]:
                readings.append(reading)
        return {
            "data": ProprioStore.code(day, month),
            "giorno": day,
            "mese": MONTHS_IT[month - 1],
            "mese_numero": month,
            "data_estesa": f"{day} {MONTHS_IT[month - 1]}",
            "santo": saint,
            "tipo": (form.get("tipo") or "").strip() or None,
            "letture": readings,
            "orazione": (form.get("orazione") or "").strip(),
        }
