"""Funzioni di utilità condivise: logging, normalizzazione testo, date."""

import logging
import re
from datetime import date, timedelta
from typing import Optional

WEEKDAYS_IT = (
    "Lunedì",
    "Martedì",
    "Mercoledì",
    "Giovedì",
    "Venerdì",
    "Sabato",
    "Domenica",
)

_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50}

_NBSP = chr(160)  # NO-BREAK SPACE

# Caratteri invisibili presenti a tratti nell'HTML CEI (zero width
# space, ZWNJ/ZWJ, word joiner, BOM, soft hyphen): vanno rimossi.
_RE_INVISIBLE = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u00ad]")

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """Configura il logging dell'applicazione (console)."""
    logging.basicConfig(level=level, format=_LOG_FORMAT, datefmt="%H:%M:%S")


def weekday_name_it(day: date) -> str:
    """Nome italiano del giorno della settimana."""
    return WEEKDAYS_IT[day.weekday()]


def sunday_on_or_before(day: date) -> date:
    """La domenica coincidente con `day` o immediatamente precedente."""
    return day - timedelta(days=(day.weekday() + 1) % 7)


_ROMAN_PAIRS = (
    (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
    (5, "V"), (4, "IV"), (1, "I"),
)


def int_to_roman(value: int) -> str:
    """Converte un intero positivo (1-89) in numero romano."""
    if value <= 0:
        return str(value)
    parts = []
    for number, symbol in _ROMAN_PAIRS:
        count, value = divmod(value, number)
        parts.append(symbol * count)
    return "".join(parts)


def roman_to_int(roman: str) -> Optional[int]:
    """Converte un numero romano (es. 'XIV') in intero; None se non valido."""
    roman = roman.strip().upper()
    if not roman or any(ch not in _ROMAN_VALUES for ch in roman):
        return None
    total = 0
    for ch, nxt in zip(roman, roman[1:] + " "):
        value = _ROMAN_VALUES[ch]
        total += -value if _ROMAN_VALUES.get(nxt, 0) > value else value
    return total


def normalize_text(text: str) -> str:
    """Normalizza il testo estratto dall'HTML.

    - converte NBSP e tabulazioni in spazi semplici
    - comprime gli spazi multipli
    - elimina gli spazi ai bordi di ogni riga
    - comprime le righe vuote multiple in UNA sola riga vuota
    """
    text = _RE_INVISIBLE.sub("", text)
    text = text.replace(_NBSP, " ").replace("\t", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r" {2,}", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
