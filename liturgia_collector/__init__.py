"""LiturgiaCollector.

Raccoglie quotidianamente i testi liturgici dal sito della Conferenza
Episcopale Italiana (chiesacattolica.it) e li salva in TXT puliti,
pronti per una pipeline AI (embedding, RAG, indicizzazione).
"""

__version__ = "1.0.0"

from .calendar import LiturgicalCalendar
from .cleaner import HtmlCleaner
from .collector import Collector
from .config import Config
from .models import DateInfo, LiturgicalDocument
from .scraper import LiturgicalScraper
from .writer import MetadataWriter, TxtWriter

__all__ = [
    "Collector",
    "Config",
    "DateInfo",
    "HtmlCleaner",
    "LiturgicalCalendar",
    "LiturgicalDocument",
    "LiturgicalScraper",
    "MetadataWriter",
    "TxtWriter",
]
