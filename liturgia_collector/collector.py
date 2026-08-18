"""Orchestrazione della raccolta quotidiana (ETL).

Extract   LiturgicalScraper  (HTTP con retry)
Transform HtmlCleaner        (HTML -> testo pulito)
          LiturgicalCalendar (metadati algoritmici)
Load      TxtWriter / MetadataWriter
"""

import logging
import re
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

from .calendar import LiturgicalCalendar
from .cleaner import ContentNotFoundError, HtmlCleaner
from .config import Config
from .models import DateInfo, LiturgicalDocument
from .scraper import LiturgicalScraper, ScraperError
from .writer import MetadataWriter, TxtWriter

logger = logging.getLogger(__name__)

# (slug del sito, nome file di output)
HourSpec = Tuple[str, str]

BASE_HOURS: Tuple[HourSpec, ...] = (
    ("ufficio-delle-letture", "ufficio-delle-letture"),
    ("lodi-mattutine", "lodi-mattutine"),
    ("ora-media", "ora-media"),
    ("vespri", "vespri"),
    ("compieta", "compieta"),
)

SATURDAY_HOURS: Tuple[HourSpec, ...] = (
    ("primi-vespri", "primi-vespri"),
    ("compieta-dopo-i-primi-vespri", "compieta-primi-vespri"),
)

SUNDAY_HOURS: Tuple[HourSpec, ...] = (
    ("secondi-vespri", "secondi-vespri"),
    ("compieta-dopo-i-secondi-vespri", "compieta-secondi-vespri"),
)

MASS_SLUG = "liturgia-del-giorno"
SAINT_SLUG = "santo-del-giorno"

# Ore le cui sezioni logiche vengono riportate anche in metadata.json.
HOURS_WITH_SECTIONS = (
    "ufficio-delle-letture",
    "lodi-mattutine",
    "ora-media",
    "vespri",
    "compieta",
    "compieta-dopo-i-primi-vespri",
    "compieta-dopo-i-secondi-vespri",
)

_RE_RANK = (
    (re.compile(r"SOLENNIT", re.I), "Solennità"),
    (re.compile(r"\bFESTA\b", re.I), "Festa"),
    (re.compile(r"MEMORIA\s+FACOLTATIVA", re.I), "Memoria facoltativa"),
    (re.compile(r"\bMEMORIA\b", re.I), "Memoria"),
)


class Collector:
    """Coordina scraping, pulizia, calendario e scrittura per una data."""

    def __init__(
        self,
        config: Config,
        scraper: Optional[LiturgicalScraper] = None,
        cleaner: Optional[HtmlCleaner] = None,
        calendar: Optional[LiturgicalCalendar] = None,
        txt_writer: Optional[TxtWriter] = None,
        metadata_writer: Optional[MetadataWriter] = None,
    ) -> None:
        self._config = config
        self._scraper = scraper or LiturgicalScraper(config)
        self._cleaner = cleaner or HtmlCleaner()
        self._calendar = calendar or LiturgicalCalendar()
        self._txt_writer = txt_writer or TxtWriter()
        self._metadata_writer = metadata_writer or MetadataWriter()

    def collect(self, day: date) -> bool:
        """Raccoglie tutti i testi liturgici della data indicata.

        Restituisce True se almeno un documento è stato scritto.
        """
        logger.info("=== Raccolta liturgia per %s ===", day.isoformat())
        target_dir = self._config.output_dir / day.isoformat()
        info = self._calendar.date_info(day)

        written = 0
        written += self._collect_daily_mass(day, target_dir, info)
        written += self._collect_saint(day, target_dir, info)
        for hour_slug, filename in self._hours_for(day):
            written += self._collect_hour(day, hour_slug, filename, target_dir, info)

        if info.psalter_week is None:
            # Feste e solennità con ufficio proprio: la pagina CEI non
            # riporta il salterio, lo si deduce dal contesto feriale.
            info.psalter_week = self._calendar.psalter_week(
                info.season, info.season_week
            )
            if info.psalter_week:
                logger.info(
                    "Salterio non presente sul sito: dedotto %s dalla "
                    "settimana %s del %s",
                    info.psalter_week, info.season_week, info.season,
                )

        self._metadata_writer.write_metadata(self._config.json_dir, info)
        logger.info(
            "=== Completato %s: %d documenti scritti in %s ===",
            day.isoformat(), written, target_dir,
        )
        return written > 0

    def close(self) -> None:
        """Rilascia le risorse di rete."""
        self._scraper.close()

    # ------------------------------------------------------------------

    @staticmethod
    def _hours_for(day: date) -> Tuple[HourSpec, ...]:
        """Ore da scaricare: le 5 di base più le vigiliari di sabato/domenica."""
        extra: Tuple[HourSpec, ...] = ()
        if day.weekday() == 5:  # sabato
            extra = SATURDAY_HOURS
        elif day.weekday() == 6:  # domenica
            extra = SUNDAY_HOURS
        return BASE_HOURS + extra

    def _collect_daily_mass(
        self, day: date, target_dir: Path, info: DateInfo
    ) -> int:
        """Scarica, pulisce e scrive la Messa del giorno; arricchisce i metadati."""
        try:
            html = self._scraper.fetch_daily_mass(day)
            self._enrich_from_mass_page(info, html)
            text = self._cleaner.clean_daily_mass(html)
        except (ScraperError, ContentNotFoundError) as exc:
            logger.error("Messa del giorno non raccolta: %s", exc)
            return 0
        info.hour_sections[MASS_SLUG] = self._cleaner.split_hour_sections(
            text, MASS_SLUG
        )
        document = LiturgicalDocument(MASS_SLUG, MASS_SLUG, MASS_SLUG, text)
        self._txt_writer.write(target_dir, document)
        return 1

    def _collect_saint(self, day: date, target_dir: Path, info: DateInfo) -> int:
        """Scarica, pulisce e scrive il Santo del giorno (Martirologio)."""
        try:
            html = self._scraper.fetch_saint_of_the_day(day)
            info.saint = self._cleaner.extract_saint_name(html)
            info.saint_image = self._cleaner.extract_saint_image(html)
            info.saint_details = self._cleaner.extract_saint_sections(html)
            text = self._cleaner.clean_saint_of_the_day(html)
        except (ScraperError, ContentNotFoundError) as exc:
            logger.warning("Santo del giorno non raccolto: %s", exc)
            return 0
        document = LiturgicalDocument(SAINT_SLUG, SAINT_SLUG, SAINT_SLUG, text)
        self._txt_writer.write(target_dir, document)
        return 1

    def _collect_hour(
        self,
        day: date,
        hour_slug: str,
        filename: str,
        target_dir: Path,
        info: DateInfo,
    ) -> int:
        """Scarica, pulisce e scrive una singola ora liturgica."""
        try:
            html = self._scraper.fetch_hour(day, hour_slug)
            if info.psalter_week is None:
                info.psalter_week = self._cleaner.extract_psalter_week(html)
            text = self._cleaner.clean_hour(html)
        except ScraperError as exc:
            logger.error("Ora %r non raccolta: %s", hour_slug, exc)
            return 0
        except ContentNotFoundError as exc:
            # Le ore vigiliari possono mancare in giorni particolari.
            logger.warning("Ora %r senza contenuto (%s): saltata", hour_slug, exc)
            return 0
        if hour_slug in HOURS_WITH_SECTIONS:
            info.hour_sections[hour_slug] = self._cleaner.split_hour_sections(
                text, hour_slug
            )
        document = LiturgicalDocument(hour_slug, filename, hour_slug, text)
        self._txt_writer.write(target_dir, document)
        return 1

    def _enrich_from_mass_page(self, info: DateInfo, html: str) -> None:
        """La pagina CEI è autorevole per celebrazione, colore e grado."""
        header = self._cleaner.extract_day_header(html)
        celebration = header.get("celebration")
        if celebration:
            info.celebration = celebration
            info.rank = self._infer_rank(celebration) or info.rank
        if header.get("color"):
            info.color = header["color"]

    @staticmethod
    def _infer_rank(celebration: str) -> Optional[str]:
        """Deduce il grado della celebrazione dal titolo CEI."""
        for pattern, rank in _RE_RANK:
            if pattern.search(celebration):
                return rank
        return None


def collect_dates(config: Config, days: List[date]) -> int:
    """Raccoglie una lista di date; restituisce il numero di giornate riuscite."""
    collector = Collector(config)
    succeeded = 0
    try:
        for day in days:
            try:
                if collector.collect(day):
                    succeeded += 1
            except Exception:  # noqa: BLE001 - una data non blocca le altre
                logger.exception("Errore imprevisto nella raccolta di %s", day)
    finally:
        collector.close()
    return succeeded
