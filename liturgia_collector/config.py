"""Gestione della configurazione (config.json)."""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

DEFAULTS: Dict[str, Any] = {
    "output": "output",
    "json_output": "json",
    "timeout": 20,
    "retry": 3,
    "user_agent": DEFAULT_USER_AGENT,
    "base_url_mass": "https://www.chiesacattolica.it/liturgia-del-giorno/",
    "base_url_hours": "https://www.chiesacattolica.it/la-liturgia-delle-ore/",
    "base_url_saint": "https://www.chiesacattolica.it/santo-del-giorno/",
    "retry_backoff_seconds": 2.0,
}


class Config:
    """Configurazione dell'applicazione, caricata da config.json."""

    def __init__(self, values: Dict[str, Any], base_dir: Path) -> None:
        merged = {**DEFAULTS, **values}
        self.output_dir: Path = (base_dir / str(merged["output"])).resolve()
        self.json_dir: Path = (base_dir / str(merged["json_output"])).resolve()
        self.timeout: int = int(merged["timeout"])
        self.retry: int = int(merged["retry"])
        self.user_agent: str = str(merged["user_agent"])
        self.base_url_mass: str = str(merged["base_url_mass"])
        self.base_url_hours: str = str(merged["base_url_hours"])
        self.base_url_saint: str = str(merged["base_url_saint"])
        self.retry_backoff_seconds: float = float(merged["retry_backoff_seconds"])

    @classmethod
    def load(cls, path: Path) -> "Config":
        """Carica la configurazione da file; usa i default se assente."""
        values: Dict[str, Any] = {}
        if path.is_file():
            try:
                values = json.loads(path.read_text(encoding="utf-8"))
                logger.info("Configurazione caricata da %s", path)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "config.json non leggibile (%s): uso i valori di default", exc
                )
        else:
            logger.warning("File %s assente: uso i valori di default", path)
        return cls(values, base_dir=path.parent)

    def __repr__(self) -> str:
        return (
            f"Config(output={self.output_dir}, timeout={self.timeout}, "
            f"retry={self.retry})"
        )
