"""Calendario liturgico romano (forma ordinaria, calendario generale).

Calcola algoritmicamente le informazioni annuali che gcatholic.org
(https://gcatholic.org/calendar/2026/General-C-it) pubblica in forma
tabellare: anno liturgico A/B/C, ciclo feriale I/II, tempo liturgico,
settimana del tempo, principali celebrazioni mobili e fisse.

Le celebrazioni del santorale qui presenti sono un sottoinsieme di
riferimento (solennità e feste del Calendario Romano Generale): il dato
autorevole per l'Italia viene comunque estratto dalla pagina CEI e ha
priorità su questa tabella (vedi Collector).
"""

import logging
from datetime import date, timedelta
from typing import Dict, Optional, Tuple

from .models import DateInfo
from .utils import sunday_on_or_before, weekday_name_it

logger = logging.getLogger(__name__)

# (nome, grado, colore)
Celebration = Tuple[str, str, str]

SEASON_ADVENT = "Avvento"
SEASON_CHRISTMAS = "Tempo di Natale"
SEASON_ORDINARY = "Tempo Ordinario"
SEASON_LENT = "Quaresima"
SEASON_TRIDUUM = "Triduo Pasquale"
SEASON_EASTER = "Tempo di Pasqua"

SEASON_DEFAULT_COLORS: Dict[str, str] = {
    SEASON_ADVENT: "Viola",
    SEASON_CHRISTMAS: "Bianco",
    SEASON_ORDINARY: "Verde",
    SEASON_LENT: "Viola",
    SEASON_TRIDUUM: "Rosso",
    SEASON_EASTER: "Bianco",
}

# Santorale fisso (solennità e feste principali): (mese, giorno) -> celebrazione.
FIXED_CELEBRATIONS: Dict[Tuple[int, int], Celebration] = {
    (1, 1): ("Maria Santissima Madre di Dio", "Solennità", "Bianco"),
    (1, 6): ("Epifania del Signore", "Solennità", "Bianco"),
    (1, 25): ("Conversione di San Paolo apostolo", "Festa", "Bianco"),
    (2, 2): ("Presentazione del Signore", "Festa", "Bianco"),
    (2, 22): ("Cattedra di San Pietro apostolo", "Festa", "Bianco"),
    (3, 19): ("San Giuseppe, sposo della B.V. Maria", "Solennità", "Bianco"),
    (3, 25): ("Annunciazione del Signore", "Solennità", "Bianco"),
    (4, 25): ("San Marco evangelista", "Festa", "Rosso"),
    (5, 3): ("Santi Filippo e Giacomo apostoli", "Festa", "Rosso"),
    (5, 14): ("San Mattia apostolo", "Festa", "Rosso"),
    (5, 31): ("Visitazione della Beata Vergine Maria", "Festa", "Bianco"),
    (6, 24): ("Natività di San Giovanni Battista", "Solennità", "Bianco"),
    (6, 29): ("Santi Pietro e Paolo apostoli", "Solennità", "Rosso"),
    (7, 3): ("San Tommaso apostolo", "Festa", "Rosso"),
    (7, 11): ("San Benedetto abate, patrono d'Europa", "Festa", "Bianco"),
    (7, 22): ("Santa Maria Maddalena", "Festa", "Bianco"),
    (7, 25): ("San Giacomo apostolo", "Festa", "Rosso"),
    (8, 6): ("Trasfigurazione del Signore", "Festa", "Bianco"),
    (8, 10): ("San Lorenzo diacono e martire", "Festa", "Rosso"),
    (8, 15): ("Assunzione della Beata Vergine Maria", "Solennità", "Bianco"),
    (8, 24): ("San Bartolomeo apostolo", "Festa", "Rosso"),
    (9, 8): ("Natività della Beata Vergine Maria", "Festa", "Bianco"),
    (9, 14): ("Esaltazione della Santa Croce", "Festa", "Rosso"),
    (9, 21): ("San Matteo apostolo ed evangelista", "Festa", "Rosso"),
    (9, 29): ("Santi Arcangeli Michele, Gabriele e Raffaele", "Festa", "Bianco"),
    (10, 18): ("San Luca evangelista", "Festa", "Rosso"),
    (10, 28): ("Santi Simone e Giuda apostoli", "Festa", "Rosso"),
    (11, 1): ("Tutti i Santi", "Solennità", "Bianco"),
    (11, 2): ("Commemorazione di tutti i fedeli defunti", "Commemorazione", "Viola"),
    (11, 9): ("Dedicazione della Basilica Lateranense", "Festa", "Bianco"),
    (11, 30): ("Sant'Andrea apostolo", "Festa", "Rosso"),
    (12, 8): ("Immacolata Concezione della B.V. Maria", "Solennità", "Bianco"),
    (12, 25): ("Natale del Signore", "Solennità", "Bianco"),
    (12, 26): ("Santo Stefano, primo martire", "Festa", "Rosso"),
    (12, 27): ("San Giovanni apostolo ed evangelista", "Festa", "Bianco"),
    (12, 28): ("Santi Innocenti martiri", "Festa", "Rosso"),
}


class LiturgicalCalendar:
    """Calcolo delle informazioni liturgiche per una data qualsiasi."""

    def date_info(self, day: date) -> DateInfo:
        """Costruisce il DateInfo algoritmico per la data indicata."""
        season, week = self._season_and_week(day)
        celebration = self._celebration(day)
        end_year = self._liturgical_end_year(day)
        info = DateInfo(
            day=day,
            weekday=weekday_name_it(day),
            liturgical_year=self._year_letter(end_year),
            lectionary_cycle="I" if end_year % 2 else "II",
            season=season,
            season_week=week,
            celebration=celebration[0] if celebration else None,
            rank=celebration[1] if celebration else self._default_rank(day),
            color=celebration[2] if celebration else SEASON_DEFAULT_COLORS[season],
        )
        logger.info("Calendario: %r", info)
        return info

    # ------------------------------------------------------------------
    # Feste mobili
    # ------------------------------------------------------------------

    @staticmethod
    def easter(year: int) -> date:
        """Domenica di Pasqua (computus gregoriano anonimo)."""
        a = year % 19
        b, c = divmod(year, 100)
        d, e = divmod(b, 4)
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i, k = divmod(c, 4)
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month, day = divmod(h + l - 7 * m + 114, 31)
        return date(year, month, day + 1)

    @staticmethod
    def first_advent_sunday(year: int) -> date:
        """Prima Domenica di Avvento dell'anno civile indicato."""
        return sunday_on_or_before(date(year, 12, 24)) - timedelta(weeks=3)

    @staticmethod
    def baptism_of_the_lord(year: int) -> date:
        """Battesimo del Signore: domenica successiva all'Epifania (6/1)."""
        epiphany = date(year, 1, 6)
        return epiphany + timedelta(days=(6 - epiphany.weekday()) % 7 or 7)

    # ------------------------------------------------------------------
    # Anno liturgico e ciclo
    # ------------------------------------------------------------------

    def _liturgical_end_year(self, day: date) -> int:
        """Anno civile in cui termina l'anno liturgico della data."""
        return day.year + 1 if day >= self.first_advent_sunday(day.year) else day.year

    @staticmethod
    def _year_letter(end_year: int) -> str:
        """Lettera del lezionario festivo: A/B/C in base all'anno finale."""
        return {1: "A", 2: "B", 0: "C"}[end_year % 3]

    # ------------------------------------------------------------------
    # Tempi liturgici e settimane
    # ------------------------------------------------------------------

    def _season_and_week(self, day: date) -> Tuple[str, Optional[int]]:
        """Determina tempo liturgico e numero di settimana."""
        year = day.year
        easter = self.easter(year)
        ash_wednesday = easter - timedelta(days=46)
        pentecost = easter + timedelta(days=49)
        holy_thursday = easter - timedelta(days=3)
        advent1 = self.first_advent_sunday(year)
        baptism = self.baptism_of_the_lord(year)

        if day >= date(year, 12, 25):
            return SEASON_CHRISTMAS, None
        if day >= advent1:
            return SEASON_ADVENT, self._weeks_since(advent1, day)
        if day <= baptism:
            return SEASON_CHRISTMAS, None
        if day < ash_wednesday:
            return SEASON_ORDINARY, self._weeks_since(baptism, day)
        if day < holy_thursday:
            # I giorni tra le Ceneri e la I domenica di Quaresima sono
            # convenzionalmente indicati come settimana 0.
            lent1 = ash_wednesday + timedelta(days=4)
            week = 0 if day < lent1 else self._weeks_since(lent1, day)
            return SEASON_LENT, week
        if day < easter:
            return SEASON_TRIDUUM, None
        if day <= pentecost:
            return SEASON_EASTER, self._weeks_since(easter, day)
        # Tempo Ordinario dopo Pentecoste: numerazione a ritroso in modo
        # che l'ultima settimana (Cristo Re) sia sempre la 34ª.
        christ_the_king = advent1 - timedelta(weeks=1)
        weeks_to_end = (christ_the_king - sunday_on_or_before(day)).days // 7
        return SEASON_ORDINARY, 34 - weeks_to_end

    @staticmethod
    def _weeks_since(season_start_sunday: date, day: date) -> int:
        """Settimana (1-based) contando dalle domeniche del tempo."""
        return (sunday_on_or_before(day) - season_start_sunday).days // 7 + 1

    # ------------------------------------------------------------------
    # Celebrazioni
    # ------------------------------------------------------------------

    def _celebration(self, day: date) -> Optional[Celebration]:
        """Celebrazione dal santorale fisso o dalle feste mobili."""
        movable = self._movable_celebrations(day.year)
        if day in movable:
            return movable[day]
        return FIXED_CELEBRATIONS.get((day.month, day.day))

    def _movable_celebrations(self, year: int) -> Dict[date, Celebration]:
        """Solennità e feste mobili dell'anno civile (uso italiano)."""
        easter = self.easter(year)
        pentecost = easter + timedelta(days=49)
        return {
            self.baptism_of_the_lord(year): (
                "Battesimo del Signore", "Festa", "Bianco"),
            easter - timedelta(days=46): (
                "Mercoledì delle Ceneri", "Feria", "Viola"),
            easter - timedelta(days=7): (
                "Domenica delle Palme", "Domenica", "Rosso"),
            easter - timedelta(days=3): (
                "Giovedì Santo", "Triduo", "Bianco"),
            easter - timedelta(days=2): (
                "Venerdì Santo", "Triduo", "Rosso"),
            easter - timedelta(days=1): (
                "Sabato Santo", "Triduo", "Bianco"),
            easter: ("Pasqua di Risurrezione", "Solennità", "Bianco"),
            # In Italia l'Ascensione è trasferita alla VII domenica di Pasqua.
            easter + timedelta(days=42): (
                "Ascensione del Signore", "Solennità", "Bianco"),
            pentecost: ("Pentecoste", "Solennità", "Rosso"),
            pentecost + timedelta(days=7): (
                "Santissima Trinità", "Solennità", "Bianco"),
            # In Italia il Corpus Domini è trasferito alla domenica.
            pentecost + timedelta(days=14): (
                "Santissimo Corpo e Sangue di Cristo", "Solennità", "Bianco"),
            pentecost + timedelta(days=19): (
                "Sacratissimo Cuore di Gesù", "Solennità", "Bianco"),
            self.first_advent_sunday(year) - timedelta(weeks=1): (
                "Nostro Signore Gesù Cristo Re dell'Universo",
                "Solennità", "Bianco"),
        }

    @staticmethod
    def _default_rank(day: date) -> str:
        """Grado di default quando non c'è alcuna celebrazione."""
        return "Domenica" if day.weekday() == 6 else "Feria"

    # ------------------------------------------------------------------
    # Salterio
    # ------------------------------------------------------------------

    _PSALTER_ROMAN = ("I", "II", "III", "IV")
    _PSALTER_SEASONS = (SEASON_ADVENT, SEASON_LENT, SEASON_EASTER, SEASON_ORDINARY)

    @classmethod
    def psalter_week(cls, season: str, season_week: Optional[int]) -> Optional[str]:
        """Settimana del salterio (I-IV) dedotta dalla settimana del tempo.

        Il salterio segue un ciclo di 4 settimane agganciato alla
        numerazione del tempo liturgico: serve da fallback quando la
        pagina CEI non la riporta (feste e solennità con ufficio
        proprio), ricavandola dal contesto feriale in cui il giorno cade.
        Con settimana 0 (giorni dopo le Ceneri) il modulo restituisce IV,
        come previsto dalla Liturgia delle Ore.
        """
        if season not in cls._PSALTER_SEASONS or season_week is None:
            return None
        return cls._PSALTER_ROMAN[(season_week - 1) % 4]
