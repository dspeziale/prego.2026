"""Raccoglie da santodelgiorno.it l'elenco dei santi di ogni giorno dell'anno.

Per ogni data del calendario (366 giorni, 29 febbraio incluso) scarica
https://www.santodelgiorno.it/GG/mese/ ed estrae il santo principale e
l'elenco «Altri santi e venerazioni». Il risultato va in
data/santi/GG-MM.json: i santi sono legati al giorno del mese, non
all'anno, quindi il file vale per sempre e la raccolta si fa una volta.

Uso (dalla radice del progetto):
    python scripts/collect_santi.py                 # tutto l'anno
    python scripts/collect_santi.py 22-09 01-01     # solo alcune date
    python scripts/collect_santi.py --solo-mancanti # completa i buchi

Le date già presenti vengono riscritte solo se la pagina ha contenuto:
una risposta vuota o un errore non cancellano mai un file esistente.
"""

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "santi"

BASE_URL = "https://www.santodelgiorno.it"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
PAUSE_SECONDS = 0.4
TIMEOUT = 20
RETRY = 3

MONTHS_IT = (
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
)
DAYS_IN_MONTH = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

logger = logging.getLogger("collect_santi")


def clean(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    # «Sant' Ignazio» -> «Sant'Ignazio»
    text = re.sub(r"(Sant|Dell|Nell|D|L)[’']\s+(?=[A-ZÀ-Ú])", r"\1'", text)
    return text.strip(" -")


def absolute(href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    if href.startswith("http"):
        return href
    return BASE_URL + href


def parse_page(html: str) -> Dict[str, Any]:
    """Santo principale e altri santi dalla pagina del giorno."""
    soup = BeautifulSoup(html, "lxml")
    result: Dict[str, Any] = {"principali": [], "altri": []}

    # --- santi principali: «Il GG mese si venera:» ------------------------
    for box in soup.select("div.SantoDiOggi"):
        name = box.select_one(".NomeSantoDiOggi")
        kind = box.select_one(".TipologiaSantoDiOggi")
        if not name:
            continue
        link = None
        for a in box.select("a[href]"):
            if "Continua" in a.get_text() or a.get_text(strip=True) == clean(name.get_text()):
                link = a["href"]
                break
        # descrizione: tutto il testo del riquadro tolti nome, qualifica e
        # il rimando «>>> Continua»
        full = clean(box.get_text(" ", strip=True))
        for part in (name.get_text(" ", strip=True), kind.get_text(" ", strip=True) if kind else ""):
            part = clean(part)
            if part and full.startswith(part):
                full = full[len(part):].strip()
        description = re.split(r">>>|Continua", full)[0].strip(" -")
        result["principali"].append({
            "nome": clean(name.get_text(" ", strip=True)),
            "qualifica": clean(kind.get_text(" ", strip=True)) if kind else "",
            "descrizione": description,
            "url": absolute(link),
        })

    # --- altri santi e venerazioni ----------------------------------------
    title = soup.find("span", class_="Titolo", string=re.compile(r"Altri santi e venerazioni"))
    container: Optional[Tag] = None
    if title is not None:
        node = title
        while node is not None and node.parent is not None and node.parent.get("id") != "CenterDiv":
            node = node.parent
        container = node if isinstance(node, Tag) else None
    if container is not None:
        for item in container.select("div.ElencoSanto"):
            link = item.select_one("a[href]")
            kind = item.select_one("i")
            if not link:
                continue
            result["altri"].append({
                "nome": clean(link.get_text(" ", strip=True)),
                "qualifica": clean(kind.get_text(" ", strip=True)) if kind else "",
                "url": absolute(link.get("href")),
            })
        for item in container.select("span.AltriSanti"):
            kind = item.select_one("i")
            name_text = item.get_text("\n", strip=True).split("\n")[0]
            result["altri"].append({
                "nome": clean(name_text),
                "qualifica": clean(kind.get_text(" ", strip=True)) if kind else "",
                "url": None,
            })
    # senza duplicati, nell'ordine della pagina
    seen = set()
    unique: List[Dict[str, Any]] = []
    for saint in result["altri"]:
        key = saint["nome"].lower()
        if re.fullmatch(r"\d{1,2} [a-zà-ú]+", key):
            continue  # voce di calendario («29 febbraio»), non un santo
        if saint["nome"] and key not in seen:
            seen.add(key)
            unique.append(saint)
    result["altri"] = unique
    return result


def fetch(session: requests.Session, day: int, month: int) -> Optional[str]:
    url = f"{BASE_URL}/{day:02d}/{MONTHS_IT[month - 1]}/"
    for attempt in range(1, RETRY + 1):
        try:
            response = session.get(url, timeout=TIMEOUT)
            if response.status_code == 404:
                logger.warning("%s: 404", url)
                return None
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            logger.warning("%s: tentativo %d/%d fallito (%s)", url, attempt, RETRY, exc)
            time.sleep(attempt * 1.5)
    return None


def collect(day: int, month: int, session: requests.Session, force: bool) -> bool:
    code = f"{day:02d}-{month:02d}"
    path = OUT_DIR / f"{code}.json"
    if path.exists() and not force:
        return True
    html = fetch(session, day, month)
    if html is None:
        return False
    parsed = parse_page(html)
    if not parsed["principali"] and not parsed["altri"]:
        logger.warning("%s: pagina senza santi, file non scritto", code)
        return False
    entry = {
        "data": code,
        "giorno": day,
        "mese": MONTHS_IT[month - 1].capitalize(),
        "mese_numero": month,
        "data_estesa": f"{day} {MONTHS_IT[month - 1]}",
        "principali": parsed["principali"],
        "altri": parsed["altri"],
        "fonte": f"{BASE_URL}/{day:02d}/{MONTHS_IT[month - 1]}/",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=4) + "\n",
                    encoding="utf-8", newline="\n")
    logger.info("%s: %d principali, %d altri", code,
                len(entry["principali"]), len(entry["altri"]))
    return True


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("date", nargs="*", help="date GG-MM (default: tutto l'anno)")
    parser.add_argument("--solo-mancanti", action="store_true",
                        help="non riscrive i file già presenti")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

    if args.date:
        wanted = []
        for raw in args.date:
            match = re.fullmatch(r"(\d{1,2})-(\d{1,2})", raw)
            if not match:
                raise SystemExit(f"Data non valida: {raw!r} (atteso GG-MM)")
            wanted.append((int(match.group(1)), int(match.group(2))))
    else:
        wanted = [(d, m) for m in range(1, 13) for d in range(1, DAYS_IN_MONTH[m - 1] + 1)]

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "it-IT,it;q=0.9"})
    failed = []
    for day, month in wanted:
        ok = collect(day, month, session, force=not args.solo_mancanti)
        if not ok:
            failed.append(f"{day:02d}-{month:02d}")
        time.sleep(PAUSE_SECONDS)
    print(f"\nRaccolti {len(wanted) - len(failed)}/{len(wanted)} giorni in {OUT_DIR}")
    if failed:
        print("Falliti:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
