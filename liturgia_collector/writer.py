"""Scrittura dei risultati su disco (TXT e JSON).

`BaseWriter` è il punto di estensione per formati futuri
(PDF, EPUB, Markdown, SQLite, PostgreSQL, Elasticsearch, embedding):
implementare `write` in una nuova sottoclasse e registrarla nel Collector.
"""

import json
import logging
from pathlib import Path

from .models import DateInfo, LiturgicalDocument

logger = logging.getLogger(__name__)


class BaseWriter:
    """Interfaccia comune dei writer di documenti liturgici."""

    def write(self, target_dir: Path, document: LiturgicalDocument) -> Path:
        """Scrive il documento e restituisce il percorso creato."""
        raise NotImplementedError

    @staticmethod
    def ensure_dir(target_dir: Path) -> Path:
        """Crea (se serve) la cartella di destinazione."""
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir


class TxtWriter(BaseWriter):
    """Scrive il testo liturgico pulito in un file .txt UTF-8."""

    EXTENSION = ".txt"

    def write(self, target_dir: Path, document: LiturgicalDocument) -> Path:
        path = self.ensure_dir(target_dir) / f"{document.filename}{self.EXTENSION}"
        path.write_text(document.text, encoding="utf-8", newline="\n")
        logger.info("Scritto %s (%d caratteri)", path, len(document.text))
        return path


class MetadataWriter(BaseWriter):
    """Scrive le informazioni liturgiche della giornata in JSON.

    I file sono raccolti nella cartella comune `json/` alla radice del
    progetto (config: 'json_output'), uno per data: YYYY-MM-DD.json.
    """

    def write_metadata(self, json_dir: Path, info: DateInfo) -> Path:
        """Serializza il DateInfo in <json_dir>/<data>.json."""
        path = self.ensure_dir(json_dir) / f"{info.day.isoformat()}.json"
        payload = json.dumps(info.to_dict(), ensure_ascii=False, indent=4)
        path.write_text(payload + "\n", encoding="utf-8", newline="\n")
        logger.info("Scritto %s", path)
        return path

    def write(self, target_dir: Path, document: LiturgicalDocument) -> Path:
        raise NotImplementedError(
            "MetadataWriter scrive DateInfo: usare write_metadata()"
        )
