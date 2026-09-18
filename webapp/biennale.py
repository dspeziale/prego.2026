"""Archivio del lezionario Biennale per giorno liturgico.

Un file JSON per combinazione tempo/settimana/giorno/anno, nominato
con lo slug dei campi (es. ordinario-xiv-mercoledi-a.json) nella
cartella `biennale/` alla radice del progetto.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SEASONS = (
    "Tempo Ordinario", "Avvento", "Tempo di Natale",
    "Quaresima", "Triduo Pasquale", "Tempo di Pasqua",
)

WEEKDAYS = (
    "Lunedì", "Martedì", "Mercoledì", "Giovedì",
    "Venerdì", "Sabato", "Domenica",
)

YEARS = ("A", "B", "C", "A/B/C")

CYCLES = ("I", "II")

MONTHS_IT = (
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
)

ROMAN_WEEKS = (
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
    "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX",
    "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI", "XXVII", "XXVIII",
    "XXIX", "XXX", "XXXI", "XXXII", "XXXIII", "XXXIV",
)

BIENNALE_READING_LABELS = (
    "Prima Lettura", "Seconda Lettura", "Vangelo", "Terza Lettura",
)

_RE_CODE = re.compile(r"^[a-z0-9-]+$")

_ACCENTS = str.maketrans("àèéìòù", "aeeiou")


def _slug(value: str) -> str:
    """Slug minuscolo senza accenti né prefisso 'Tempo (di)'."""
    value = re.sub(r"^Tempo (di )?", "", value or "", flags=re.I)
    value = value.strip().lower().translate(_ACCENTS)
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


class BiennaleStore:
    """Persistenza dei giorni del Biennale su file slug.json."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    @staticmethod
    def code(entry: Dict[str, Any]) -> str:
        """Slug del file dai campi identificativi non vuoti."""
        parts = [
            _slug(entry.get("tempo_liturgico") or ""),
            _slug(entry.get("settimana_del_tempo") or ""),
            _slug(entry.get("giorno_settimana") or ""),
            _slug(entry.get("anno_liturgico") or ""),
            _slug(entry.get("ciclo_biennale") or ""),
        ]
        return "-".join(part for part in parts if part)

    @staticmethod
    def date_code(season: str, day: int, month: int, cycle: Optional[str]) -> str:
        """Slug delle ferie a data fissa (17-24 dicembre, Tempo di Natale).

        Es. 'natale-2-gennaio-i', 'avvento-17-dicembre-ii': le letture di
        quei giorni sono proprie della data, non della settimana.
        """
        parts = [_slug(season), str(day), _slug(MONTHS_IT[month - 1]), _slug(cycle or "")]
        return "-".join(part for part in parts if part)

    @staticmethod
    def is_valid_code(code: str) -> bool:
        return bool(code) and bool(_RE_CODE.match(code))

    def path_for(self, code: str) -> Path:
        return self._directory / f"{code}.json"

    def load(self, code: str) -> Optional[Dict[str, Any]]:
        """Carica un giorno del biennale; None se assente."""
        if not self.is_valid_code(code):
            return None
        path = self.path_for(code)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Biennale non leggibile (%s): %s", path, exc)
            return None

    def save(self, entry: Dict[str, Any]) -> Path:
        """Scrive il giorno del biennale e restituisce il percorso."""
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self.path_for(entry["codice"])
        payload = json.dumps(entry, ensure_ascii=False, indent=4)
        path.write_text(payload + "\n", encoding="utf-8", newline="\n")
        logger.info("Scritto %s", path)
        return path

    def delete(self, code: str) -> bool:
        """Elimina il giorno; True se il file esisteva."""
        if not self.is_valid_code(code):
            return False
        path = self.path_for(code)
        if path.is_file():
            path.unlink()
            logger.info("Eliminato %s", path)
            return True
        return False

    def list_entries(self) -> List[Dict[str, Any]]:
        """Tutti i giorni, ordinati per tempo, settimana, giorno, anno."""
        entries = []
        if not self._directory.is_dir():
            return entries
        for path in self._directory.glob("*.json"):
            entry = self.load(path.stem)
            if entry:
                entries.append(entry)

        def sort_key(entry: Dict[str, Any]):
            season = entry.get("tempo_liturgico") or ""
            week = entry.get("settimana_del_tempo") or ""
            day = entry.get("giorno_settimana") or ""
            year = entry.get("anno_liturgico") or ""
            cycle = entry.get("ciclo_biennale") or ""
            season_pos = SEASONS.index(season) if season in SEASONS else 99
            week_pos = ROMAN_WEEKS.index(week) if week in ROMAN_WEEKS else 99
            day_pos = WEEKDAYS.index(day) if day in WEEKDAYS else 99
            return (season_pos, week_pos, day_pos, year, cycle)

        return sorted(entries, key=sort_key)

    @staticmethod
    def from_form(form: Dict[str, str]) -> Dict[str, Any]:
        """Costruisce il giorno del biennale dai campi della form.

        Solleva ValueError se i campi identificativi sono insufficienti.
        """
        season = (form.get("tempo_liturgico") or "").strip()
        weekday = (form.get("giorno_settimana") or "").strip()
        if not season or not weekday:
            raise ValueError("Tempo liturgico e giorno sono obbligatori.")
        entry = {
            "tempo_liturgico": season,
            "settimana_del_tempo": (form.get("settimana_del_tempo") or "").strip() or None,
            "giorno_settimana": weekday,
            "anno_liturgico": (form.get("anno_liturgico") or "").strip() or None,
            "ciclo_biennale": (form.get("ciclo_biennale") or "").strip() or None,
            "letture": [],
        }
        for index, label in enumerate(BIENNALE_READING_LABELS, start=1):
            reading = {
                "titolo": label,
                "riferimento": (form.get(f"lettura_{index}_riferimento") or "").strip(),
                "sottotitolo": (form.get(f"lettura_{index}_sottotitolo") or "").strip(),
                "fonte": (form.get(f"lettura_{index}_fonte") or "").strip(),
                "testo": (form.get(f"lettura_{index}_testo") or "").strip(),
                "responsorio": (form.get(f"lettura_{index}_responsorio") or "").strip(),
            }
            if reading["riferimento"] or reading["testo"]:
                entry["letture"].append(reading)
        # voce a data fissa (campo nascosto della form di modifica): il
        # codice resta quello per data, così il file non cambia nome
        date_match = re.fullmatch(r"(\d{2})-(\d{2})", (form.get("data") or "").strip())
        if date_match:
            day, month = int(date_match.group(1)), int(date_match.group(2))
            if 1 <= day <= 31 and 1 <= month <= 12:
                entry["data"] = f"{day:02d}-{month:02d}"
                entry["data_estesa"] = f"{day} {MONTHS_IT[month - 1]}"
                entry["codice"] = BiennaleStore.date_code(
                    season, day, month, entry["ciclo_biennale"]
                )
                return entry
        entry["codice"] = BiennaleStore.code(entry)
        if not BiennaleStore.is_valid_code(entry["codice"]):
            raise ValueError("Impossibile generare il nome del file.")
        return entry
