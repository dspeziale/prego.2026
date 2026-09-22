"""Santi del giorno (data/santi/GG-MM.json).

Un file per giorno del calendario, raccolto da santodelgiorno.it con
`scripts/collect_santi.py`: il santo principale e l'elenco degli altri
santi e beati venerati in quella data. I santi sono legati al giorno del
mese, non all'anno, quindi l'archivio vale per ogni anno.
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SantiStore:
    """Lettura dei santi del giorno dalla cartella dei JSON."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    @staticmethod
    def code(day: date) -> str:
        return f"{day.day:02d}-{day.month:02d}"

    def load(self, day: date) -> Optional[Dict[str, Any]]:
        """Santi del giorno; None se il file manca o non è leggibile."""
        path = self._directory / f"{self.code(day)}.json"
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Santi non leggibili (%s): %s", path, exc)
            return None

    def count(self) -> int:
        """Quanti giorni del calendario sono coperti."""
        if not self._directory.is_dir():
            return 0
        return sum(1 for _ in self._directory.glob("??-??.json"))
