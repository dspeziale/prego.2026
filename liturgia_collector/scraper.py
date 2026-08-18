"""Download delle pagine liturgiche dal sito CEI (chiesacattolica.it).

Le pagine sono interamente renderizzate lato server (nessun contenuto
liturgico caricato via AJAX), quindi requests + BeautifulSoup bastano.
"""

import logging
import time
from datetime import date
from typing import Dict

import requests

from .config import Config

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Errore definitivo di download dopo tutti i tentativi."""


class LiturgicalScraper:
    """Client HTTP con retry, timeout e User-Agent realistico."""

    DATE_PARAM = "data-liturgia"
    HOUR_PARAM = "ora"

    def __init__(self, config: Config) -> None:
        self._config = config
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": config.user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "it-IT,it;q=0.9",
            }
        )

    def fetch_daily_mass(self, day: date) -> str:
        """HTML della pagina 'Liturgia del Giorno' (Messa)."""
        params = {self.DATE_PARAM: self._format_date(day)}
        return self._get(self._config.base_url_mass, params)

    def fetch_hour(self, day: date, hour_slug: str) -> str:
        """HTML di un'ora della Liturgia delle Ore (es. 'lodi-mattutine')."""
        params = {
            self.DATE_PARAM: self._format_date(day),
            self.HOUR_PARAM: hour_slug,
        }
        return self._get(self._config.base_url_hours, params)

    def fetch_saint_of_the_day(self, day: date) -> str:
        """HTML della pagina 'Santo del Giorno' (Martirologio)."""
        params = {self.DATE_PARAM: self._format_date(day)}
        return self._get(self._config.base_url_saint, params)

    def close(self) -> None:
        """Chiude la sessione HTTP."""
        self._session.close()

    # ------------------------------------------------------------------

    @staticmethod
    def _format_date(day: date) -> str:
        """Data nel formato YYYYMMDD richiesto dal sito."""
        return day.strftime("%Y%m%d")

    def _get(self, url: str, params: Dict[str, str]) -> str:
        """GET con retry automatico e backoff esponenziale."""
        last_error: Exception = ScraperError("nessun tentativo eseguito")
        for attempt in range(1, self._config.retry + 1):
            try:
                logger.info(
                    "GET %s %s (tentativo %d/%d)",
                    url, params, attempt, self._config.retry,
                )
                response = self._session.get(
                    url, params=params, timeout=self._config.timeout
                )
                response.raise_for_status()
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                logger.warning(
                    "Tentativo %d/%d fallito per %s: %s",
                    attempt, self._config.retry, url, exc,
                )
                if attempt < self._config.retry:
                    delay = self._config.retry_backoff_seconds * attempt
                    time.sleep(delay)
        message = f"Download fallito dopo {self._config.retry} tentativi: {url}"
        logger.error(message)
        raise ScraperError(message) from last_error
