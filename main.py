"""Entry point di LiturgiaCollector.

Uso:
    python main.py                              # la liturgia di oggi
    python main.py 2026-07-08                   # una data specifica
    python main.py 2026-07-08 2026-07-12        # più date singole
    python main.py 2026-07-01..2026-07-31       # un intervallo di date
    python main.py 2026-07-08 2026-08-01..2026-08-05   # misto
"""

import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List

from liturgia_collector.collector import collect_dates
from liturgia_collector.config import Config
from liturgia_collector.utils import setup_logging

logger = logging.getLogger("main")

CONFIG_FILE = Path(__file__).resolve().parent / "config.json"
DATE_FORMAT = "%Y-%m-%d"
RANGE_SEPARATOR = ".."
MAX_RANGE_DAYS = 366


def parse_dates(argv: List[str]) -> List[date]:
    """Converte gli argomenti in date; senza argomenti usa oggi.

    Ogni argomento può essere una data singola (YYYY-MM-DD) oppure un
    intervallo inclusivo INIZIO..FINE. Le date duplicate vengono
    eliminate mantenendo l'ordine.
    """
    if not argv:
        return [date.today()]
    days: List[date] = []
    for raw in argv:
        days.extend(_parse_token(raw))
    unique: List[date] = []
    for day in days:
        if day not in unique:
            unique.append(day)
    return unique


def _parse_token(raw: str) -> List[date]:
    """Espande un argomento in una lista di date."""
    if RANGE_SEPARATOR in raw:
        start_raw, _, end_raw = raw.partition(RANGE_SEPARATOR)
        return _expand_range(_parse_date(start_raw), _parse_date(end_raw))
    return [_parse_date(raw)]


def _parse_date(raw: str) -> date:
    """Parsa una singola data YYYY-MM-DD, o termina con errore chiaro."""
    try:
        return datetime.strptime(raw.strip(), DATE_FORMAT).date()
    except ValueError:
        raise SystemExit(
            f"Data non valida: {raw!r} (formato atteso: YYYY-MM-DD "
            f"oppure YYYY-MM-DD{RANGE_SEPARATOR}YYYY-MM-DD)"
        )


def _expand_range(start: date, end: date) -> List[date]:
    """Tutte le date dell'intervallo inclusivo [start, end]."""
    if end < start:
        raise SystemExit(
            f"Intervallo non valido: {start} è successivo a {end}"
        )
    total_days = (end - start).days + 1
    if total_days > MAX_RANGE_DAYS:
        raise SystemExit(
            f"Intervallo troppo ampio ({total_days} giorni): "
            f"il massimo consentito è {MAX_RANGE_DAYS}"
        )
    return [start + timedelta(days=offset) for offset in range(total_days)]


def main(argv: List[str]) -> int:
    """Esegue la raccolta e restituisce il codice di uscita."""
    setup_logging()
    days = parse_dates(argv)
    config = Config.load(CONFIG_FILE)
    succeeded = collect_dates(config, days)
    failed = len(days) - succeeded
    if failed:
        logger.error("Raccolta incompleta: %d/%d date fallite", failed, len(days))
        return 1
    logger.info("Raccolta completata per %d data/e", succeeded)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
