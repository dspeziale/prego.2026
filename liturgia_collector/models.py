"""Modelli di dominio dell'applicazione."""

from datetime import date
from typing import Any, Dict, Optional

from .utils import int_to_roman


class DateInfo:
    """Informazioni liturgiche complete di una data.

    Combina i dati calcolati algoritmicamente (anno liturgico, ciclo,
    tempo, settimana) con quelli estratti dal sito CEI (celebrazione,
    colore, settimana del salterio).
    """

    def __init__(
        self,
        day: date,
        weekday: str,
        liturgical_year: str,
        lectionary_cycle: str,
        season: str,
        season_week: Optional[int],
        celebration: Optional[str] = None,
        rank: Optional[str] = None,
        color: Optional[str] = None,
        psalter_week: Optional[str] = None,
        saint: Optional[str] = None,
        saint_image: Optional[str] = None,
        saint_details: Optional[Dict[str, Any]] = None,
        hour_sections: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self.day = day
        self.weekday = weekday
        self.liturgical_year = liturgical_year
        self.lectionary_cycle = lectionary_cycle
        self.season = season
        self.season_week = season_week
        self.celebration = celebration
        self.rank = rank
        self.color = color
        self.psalter_week = psalter_week
        self.saint = saint
        self.saint_image = saint_image
        # Santo del giorno strutturato: nome, martirologio, altri santi.
        self.saint_details = saint_details
        # Sezioni logiche delle ore, indicizzate per slug
        # (es. 'lodi-mattutine' -> {'inno': ..., 'orazione': ...};
        # 'antifone_e_salmi' è una lista di tre gruppi).
        self.hour_sections: Dict[str, Dict[str, Any]] = hour_sections or {}

    def to_dict(self) -> Dict[str, Any]:
        """Rappresentazione serializzabile in JSON (metadata.json)."""
        return {
            "data": self.day.isoformat(),
            "giorno_settimana": self.weekday,
            "anno_liturgico": self.liturgical_year,
            "ciclo_biennale": self.lectionary_cycle,
            "tempo_liturgico": self.season,
            # In numeri romani; '0' per i giorni tra le Ceneri e la
            # I domenica di Quaresima, null dove non si applica.
            "settimana_del_tempo": (
                int_to_roman(self.season_week)
                if self.season_week is not None else None
            ),
            "celebrazione": self.celebration,
            "grado": self.rank,
            "colore": self.color,
            "settimana_del_salterio": self.psalter_week,
            "santo_del_giorno": self.saint,
            "immagine_santo": self.saint_image,
            "santo": self.saint_details,
            "liturgia_del_giorno": self.hour_sections.get(
                "liturgia-del-giorno"
            ),
            "ufficio_delle_letture": self.hour_sections.get(
                "ufficio-delle-letture"
            ),
            "lodi_mattutine": self.hour_sections.get("lodi-mattutine"),
            "ora_media": self.hour_sections.get("ora-media"),
            "vespri": self.hour_sections.get("vespri"),
            "compieta": self.hour_sections.get("compieta"),
            "compieta_primi_vespri": self.hour_sections.get(
                "compieta-dopo-i-primi-vespri"
            ),
            "compieta_secondi_vespri": self.hour_sections.get(
                "compieta-dopo-i-secondi-vespri"
            ),
        }

    def __repr__(self) -> str:
        return (
            f"DateInfo({self.day.isoformat()}, {self.season!r}, "
            f"settimana={self.season_week}, anno={self.liturgical_year}/"
            f"{self.lectionary_cycle}, celebrazione={self.celebration!r})"
        )


class LiturgicalDocument:
    """Un singolo testo liturgico pronto per la scrittura su disco."""

    def __init__(self, slug: str, filename: str, url: str, text: str) -> None:
        self.slug = slug
        self.filename = filename
        self.url = url
        self.text = text

    @property
    def is_empty(self) -> bool:
        """True se il documento non contiene testo utile."""
        return not self.text.strip()

    def __repr__(self) -> str:
        return f"LiturgicalDocument({self.slug!r}, {len(self.text)} caratteri)"
