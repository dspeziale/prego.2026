"""Converte i testi grezzi dell'Ufficio delle letture in JSON.

Sorgente: data/biennale/raw/<Categoria>/... (TXT in cp1252, impaginati
in due modi: "compatti", con paragrafi su una sola riga lunghissima, e
"a capo", con righe spezzate a ~75 caratteri e righe vuote tra i
blocchi). Destinazione: data/biennale/raw/json/, in quattro cartelle:

    biennale/       giorni del ciclo stagionale (Ordinario, Quaresima,
                    Pasqua, Avvento, Ceneri, Triduo): stesso schema dei
                    file di data/biennale/, pronti da copiare.
                    Vi finiscono anche le ferie a data fissa del tempo
                    (17-24 dicembre, 29-31 dicembre, 2-12 gennaio), con il
                    campo "data" e codice per data (es. natale-2-gennaio-i)
                    che la webapp risolve in repository._find_biennale.
    proprio/        Santi e feste a data fissa: schema di data/proprio/.
    da_assegnare/   feste mobili (Trinità, Corpus Domini, Santa Famiglia,
                    II domenica dopo Natale) e file di prova.

Uso (dalla radice del progetto):
    python scripts/biennale_raw_to_json.py
    python scripts/biennale_raw_to_json.py --solo Ordinario/02_BIEN

Il file REPORT.md nella cartella di destinazione riassume conteggi,
avvisi per file (sottotitolo incollato al testo, fonte assente, file
danneggiati, duplicati) e giornate mancanti nella sorgente.
"""

import argparse
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "biennale" / "raw"
OUT_DIR = RAW_DIR / "json"

ENCODING = "cp1252"

MONTHS_IT = (
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
)

ROMAN = (
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
    "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX",
    "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI", "XXVII", "XXVIII",
    "XXIX", "XXX", "XXXI", "XXXII", "XXXIII", "XXXIV",
)

WEEKDAY_CODES = {
    "1DOM": "Domenica", "2LUN": "Lunedì", "3MAR": "Martedì",
    "4MER": "Mercoledì", "5GIO": "Giovedì", "6VEN": "Venerdì",
    "7SAB": "Sabato", "7.SAB": "Sabato",
    # la domenica che chiude la settimana (es. Pentecoste dopo PAS07)
    "8DOM": "Domenica+",
}

ORDINALS = ("Prima", "Seconda", "Terza", "Quarta", "Quinta")

_ACCENTS = str.maketrans("àèéìòù", "aeeiou")

# --------------------------------------------------------------------------
# Riconoscimento delle righe
# --------------------------------------------------------------------------

RE_MARKER = re.compile(
    r"^(?P<ord>Prima|Seconda|Terza|Quarta|Quinta)\s+Lettura"
    r"\s*(?:\((?P<tag>[^)]*)\))?\s*\.?\s*$",
    re.I,
)
RE_MARKER_SIMPLE = re.compile(r"^(?P<kind>Lettura|Vangelo)\s*(?:\((?P<tag>[^)]*)\))?\s*$")
RE_ALT = re.compile(
    r"^(?:[Oo]ppure|A scelta|(?:A scelta )?[Uu]na dell[ea](?: \w+)? seguenti)\s*:?\s*$"
)
_RE_FONTE_PREFIX = re.compile(
    r"^(?:Dal|Dalla|Dalle|Dai|Dallo|Dagli)\b\s*\S"
    r"|^Dall[’']\s*\S"
    r"|^Da\s+(?:un[’']|una?\b|alcun[ei]|[A-ZÀ-Ú«\"“])"
    r"|^Inizio (?:del|della|dell[’']|dei|degli|delle)\b"
    r"|^Incomincia (?:il|la|l[’'])\b"
    r"|^Conclusione (?:del|della|dell[’'])\b"
    r"|^Lettera (?:a|ai|agli|alla|alle)\b[^.]{0,60}\("
)
# parole che compaiono nelle righe di fonte (libro, autore, genere)
_RE_FONTE_WORDS = re.compile(
    r"libr[oi]|letter[ae]|vangel|trattat|discors|omeli|comment|oper[ae]|opuscol|"
    r"regola|atti\b|cantic|profet|apostol|vescov|papa|abat|sacerdot|martir|dottor|"
    r"diacon|monac|\bsan\b|sant[’'aoie]|beat[oa]|autor|sermon|esposizion|catechesi|"
    r"costituzion|enciclic|esortazion|istruzion|narrazion|epistol|autobiograf|storia|"
    r"meditazion|conferenz|spiegazion|dialog|apologi|confession|\binni\b|salm|"
    r"siracide|sapienza|proverbi|qo[èe]let|giobbe|tobia|giuditta|ester|maccabei|"
    r"apocalisse|genesi|esodo|levitico|numeri|deuteronomio|giosu|giudici|\brut\b|"
    r"samuele|\bre\b|cronache|esdra|neemia|baruc|lamentazioni|daniele|geremia|isaia|"
    r"ezechiele|osea|gioele|amos|abdia|giona|michea|naum|abacuc|sofonia|aggeo|"
    r"zaccaria|malachia|specchio|itinerari|princip|imitazion|vita\b|passion|"
    r"colloqui|scritt|pedagog|document|decret|\bnote\b|pensier|poem|preghier",
    re.I,
)


class _FonteMatcher:
    """Riga di fonte: prefisso «Dal…», parola tipica e forma breve o con
    riferimento tra parentesi (i paragrafi di testo che iniziano con
    «Dalla Siria a Roma…» non devono passare)."""

    def match(self, line: str) -> Optional[re.Match]:
        head = line[:160]
        m = _RE_FONTE_PREFIX.match(line)
        if not m:
            return None
        if not _RE_FONTE_WORDS.search(head):
            return None
        if "(" in head or len(line) <= 170 or re.search(r"[«\"“]", head[:80]):
            return m
        return None


RE_FONTE = _FonteMatcher()
RE_RESP = re.compile(r"^Responsorio\b")
RE_RESP_LINE = re.compile(r"^(?:R\.|V\.|\*)")
RE_ORAZIONE = re.compile(r"^Orazione\b")
RE_VPAG = re.compile(r"^(?P<rif>[A-Za-z0-9][^()]{1,60}?)\s*\(v\.\s*pag\.")
# titolo e fonte sulla stessa riga: «Vangelo (A/B/C) Dal vangelo secondo Luca…»
RE_MARKER_GLUED = re.compile(
    r"^((?:Vangelo|Lettura|(?:Prima|Seconda|Terza|Quarta|Quinta)\s+Lettura)"
    r"\s*(?:\([^)]*\))?)\s+(?=\S)",
    re.I,
)
# incipit tipici del testo, per staccare un sottotitolo incollato
RE_OPENER = re.compile(
    r"(?<=[a-zà-ú!?»])\s+(?=(?:Fratelli|Carissimi|Carissimo|Figlioli|Figli miei|"
    r"In quei giorni|In quel tempo|In quel giorno|In principio|Dice il Signore|"
    r"Così dice il Signore|Così parla il Signore|Oracolo del Signore|Al tempo di|"
    r"Nell[’']anno|Vi esorto|Vi scongiuro|Vi supplico|Ricordatevi|Ascoltate|"
    r"Consolate, consolate|Un giorno|C[’']era una volta|Mi fu rivolta|Il Signore disse|"
    r"Il Signore parlò|Il Signore rispose|Dio disse|Dio parlò)\b(?:,|\s|:))"
)
RE_DOT_ONLY = re.compile(r"^[.\s]*$")
# parole strutturali con cui spesso inizia il testo dopo un sottotitolo
# incollato (articoli, congiunzioni temporali, pronomi, virgolette)
RE_STRUCT_START = re.compile(
    r"(?<=[a-zà-ú,!?»])\s+(?=(?:Quando|Dopo|Nel|Nell[’']\w|Nella|Nelle|Nei|Negli|Il|La|Le|Lo|"
    r"Gli|In|Al|All[’']\w|Alla|Alle|Un|Una|Un[’']\w|Se|Chi|Come|Così|Ecco|Io|Noi|Voi|Tu|Egli|"
    r"Essi|Parola|Allora|Mentre|Ora|Poi|Vi|Ti|Mi|Ci|Non|Fratelli|Carissimi|Figlioli|Dice|"
    r"Disse|Tutto|Tutti|Ogni|Questo|Questa|Questi|Queste|Quello|Quella|Beato|Beati|Guai|"
    r"Venite|Andate|Ascolta|Ascoltate|Sappiate|Ricordati|Riflettiamo|Consideriamo|Vediamo|"
    r"Perché|Poiché|Siccome|Infatti|Anche|Prendete|Vedete|Guardate|Ho|Hai|Abbiamo|Avete|Sono|"
    r"Siamo|Siete|Era|Erano|C[’']è|C[’']era|Vi è|Vi era|Vi sono|Vi erano|Or|Alcuni|Molti|Nessuno|"
    r"Niente|Nulla)\b|L[’'][A-Za-zÀ-ú]|«|“|\")"
)


def split_glued_subtitle(text: str) -> Optional[Tuple[str, str]]:
    """(sottotitolo, testo) se il sottotitolo incollato è separabile.

    Prima si cercano gli incipit tipici («Fratelli,», «In quei giorni»);
    poi la prima parola strutturale maiuscola preceduta da una parola
    senza punto/punto e virgola/due punti, con un prefisso di almeno tre
    parole e al massimo 140 caratteri.
    """
    opener = RE_OPENER.search(text, 12, 170)
    if opener and len(text[:opener.start()].split()) >= 3:
        return text[:opener.start()].strip(), text[opener.end():].strip()
    for match in RE_STRUCT_START.finditer(text, 12, 170):
        prefix = text[:match.start()]
        if len(prefix) > 140 or len(prefix.split()) < 3:
            if len(prefix) > 140:
                break
            continue
        inner = prefix.strip().rstrip(".!?").replace("SS.", "").replace("S.", "")
        if re.search(r"[.;:!?]", inner):
            continue
        return prefix.strip(), text[match.end():].strip()
    return None

# Marcatori che nei file compatti possono trovarsi a metà riga: si
# spezza la riga prima di ciascuno (e dopo i due punti di "Oppure:").
INLINE_SPLITS = (
    re.compile(r"(?<=\S)[ \t]*(?=(?:Oppure|oppure)\s*:)"),
    re.compile(r"(?<=(?:Oppure|oppure):)[ \t]*(?=\S)"),
    re.compile(r"(?<=\S)[ \t]+(?=(?:A scelta )?[Uu]na delle(?: tre| due)? seguenti\s*:)"),
    re.compile(r"(?<=seguenti:)[ \t]*(?=\S)"),
    re.compile(r"(?<=\S)[ \t]+(?=(?:Prima|Seconda|Terza|Quarta|Quinta)\s+Lettura\b)", re.I),
    re.compile(r"(?<=[.!?»])[ \t]*(?=(?:Prima|Seconda|Terza|Quarta|Quinta)\s+LETTURA\b)"),
    re.compile(r"(?<=[.!?»:;])[ \t]+(?=Vangelo\b\s*(?:\([^)]*\))?\s+Dal\s)"),
    re.compile(r"(?<=[.!?»])[ \t]+(?=Responsorio\b)"),
    re.compile(r"(?<=\S)[ \t]{2,}(?=Orazione\s+\S)"),
    re.compile(r"(?<=[.!?»])[ \t]*(?=Orazione\s+[A-ZÈÀ«])"),
    # sottotitolo incollato davanti alla fonte: «Egli è pastore… Dai «Discorsi»…»
    re.compile(r"(?<=[a-zà-ú,])[ \t]+(?=(?:Dal|Dalla|Dalle|Dai|Dallo|Dagli|Dall[’'])\s*[«\"“])"),
)


def normalize_text(raw: bytes) -> str:
    text = raw.decode(ENCODING)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x85", "…")
    text = text.replace("\xa0", " ")
    # virgolette rese come < > dall'OCR
    text = re.sub(r"<(?=\S)", "«", text)
    text = re.sub(r"(?<=\S)>", "»", text)
    text = text.replace("<", "«").replace(">", "»")
    return text


def is_wrapped(text: str) -> bool:
    longest = max((len(line) for line in text.splitlines()), default=0)
    return longest <= 300


def logical_lines(text: str) -> List[str]:
    """Righe logiche: un paragrafo per riga, marcatori separati."""
    lines = text.split("\n")
    if is_wrapped(text):
        blank_ratio = 1 - sum(1 for l in lines if l.strip()) / max(1, len(lines))
        if blank_ratio > 0.2:
            blocks = _join_blocks(lines)
        else:
            blocks = _join_by_punctuation(lines)
    else:
        blocks = [l.strip() for l in lines]
    out: List[str] = []
    for block in blocks:
        if not block.strip():
            out.append("")
            continue
        # gli spezzoni si individuano PRIMA di compattare gli spazi: gli
        # spazi multipli davanti a «Orazione» sono un indizio
        for piece in _split_inline(block):
            piece = re.sub(r"[ \t]+", " ", piece).strip()
            if not piece:
                continue
            glued = RE_MARKER_GLUED.match(piece)
            if glued and (RE_FONTE.match(piece[glued.end():]) or RE_ALT.match(piece[glued.end():])):
                out.append(glued.group(1).strip())
                out.append(piece[glued.end():].strip())
            else:
                out.append(piece)
    return out


def _join_blocks(lines: List[str]) -> List[str]:
    """Layout 'a capo' con righe vuote: le righe di un blocco vanno unite."""
    blocks: List[str] = []
    current: List[str] = []
    for line in lines:
        if line.strip():
            current.append(line.strip())
        elif current:
            blocks.append(_join_wrapped(current))
            current = []
            blocks.append("")
    if current:
        blocks.append(_join_wrapped(current))
    return blocks


def _join_wrapped(pieces: List[str]) -> str:
    """Unisce righe spezzate; i versetti del responsorio restano separati."""
    out: List[str] = []
    for piece in pieces:
        if out and not RE_RESP_LINE.match(piece) and not RE_RESP.match(piece) \
                and not RE_MARKER.match(piece) and not RE_ORAZIONE.match(piece):
            out[-1] = out[-1] + " " + piece
        else:
            out.append(piece)
    return "\n".join(out)


def _join_by_punctuation(lines: List[str]) -> List[str]:
    """Layout 'a capo' senza righe vuote: si unisce fino a un segno forte."""
    blocks: List[str] = []
    current = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if RE_MARKER.match(line) or RE_RESP.match(line) or RE_FONTE.match(line) \
                or RE_RESP_LINE.match(line) or RE_ORAZIONE.match(line):
            if current:
                blocks.append(current)
            current = line
            if RE_MARKER.match(line) or RE_RESP.match(line):
                blocks.append(current)
                current = ""
            continue
        current = (current + " " + line).strip() if current else line
        if re.search(r"[.!?»]$", line):
            blocks.append(current)
            current = ""
    if current:
        blocks.append(current)
    return blocks


def _split_inline(block: str) -> List[str]:
    pieces = [block]
    for pattern in INLINE_SPLITS:
        nxt: List[str] = []
        for piece in pieces:
            nxt.extend(pattern.split(piece))
        pieces = nxt
    # dentro un blocco 'a capo' i versetti sono già separati da \n
    result: List[str] = []
    for piece in pieces:
        result.extend(piece.split("\n"))
    return result


# --------------------------------------------------------------------------
# Parser del contenuto (intestazione + letture + orazione)
# --------------------------------------------------------------------------

class Reading:
    def __init__(self, titolo: str, tag: str = "") -> None:
        self.titolo = titolo
        self.tag = tag
        self.fonte = ""
        self.riferimento = ""
        self.sottotitolo = ""
        self.testo: List[str] = []
        self.responsorio: List[str] = []
        self.alternative = False
        self.reference_only = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "titolo": self.titolo,
            "riferimento": self.riferimento,
            "sottotitolo": self.sottotitolo,
            "fonte": self.fonte,
            "testo": "\n".join(self.testo).strip(),
            "responsorio": "\n".join(self.responsorio).strip(),
        }

    @property
    def started(self) -> bool:
        return bool(self.fonte or self.testo or self.sottotitolo or self.reference_only)


class Parsed:
    def __init__(self) -> None:
        self.header: List[str] = []
        self.readings: List[Reading] = []
        self.orazione: List[str] = []
        self.warnings: List[str] = []


def parse_fonte(line: str, reading: Reading, warnings: List[str]) -> None:
    """Fonte, riferimento (tra parentesi) e sottotitolo dalla riga."""
    match = re.match(r"^(?P<fonte>.*?)\s*\((?P<rif>[^()]*)\)\s*(?P<rest>.*)$", line)
    if not match:
        reading.fonte = line.strip().rstrip(".").strip()
        return
    fonte = match.group("fonte").strip()
    # fonte ripetuta due volte sulla stessa riga
    half = len(fonte) // 2
    if len(fonte) > 20 and fonte[:half].strip() == fonte[half:].strip():
        fonte = fonte[:half].strip()
    reading.fonte = fonte.rstrip(".").strip()
    reading.riferimento = re.sub(r"\s+", " ", match.group("rif")).strip()
    rest = match.group("rest").strip()
    rest = re.sub(r"^\.\s*", "", rest)
    rest = re.sub(r"\s*\.\s*$", "", rest).strip()
    if not rest:
        return
    if len(rest) <= 170:
        reading.sottotitolo = rest
        return
    # sottotitolo incollato all'inizio del testo: si prova a staccarlo
    split = split_glued_subtitle(rest)
    if split:
        reading.sottotitolo, first = split
        reading.testo.append(first)
        warnings.append(f"{reading.titolo}: sottotitolo separato euristicamente «{reading.sottotitolo[:50]}»")
    else:
        reading.testo.append(rest)
        warnings.append(f"{reading.titolo}: sottotitolo incollato al testo (fonte «{reading.fonte[:40]}»)")


def next_ordinal(titolo: str) -> str:
    base = titolo.split(" ")[0]
    if base in ORDINALS:
        idx = ORDINALS.index(base)
        if idx + 1 < len(ORDINALS):
            return f"{ORDINALS[idx + 1]} Lettura"
    return "Lettura"


def parse_document(lines: List[str]) -> Parsed:
    doc = Parsed()
    current: Optional[Reading] = None
    pending_titolo: Optional[Tuple[str, str]] = None  # (titolo, tag)
    alt_flag = False
    in_resp = False
    in_orazione = False
    seen_body = False
    prev = None

    def new_reading(titolo: str, tag: str, alternative: bool) -> Reading:
        reading = Reading(titolo, tag)
        reading.alternative = alternative
        doc.readings.append(reading)
        return reading

    for line in lines:
        if line == prev and line:
            continue  # righe duplicate consecutive (titoli ripetuti)
        prev = line
        if not line:
            # nel layout 'a capo' le righe vuote separano anche i
            # versetti del responsorio: non chiudono nulla
            continue
        if RE_DOT_ONLY.match(line):
            continue

        if in_orazione:
            if RE_MARKER.match(line) or RE_MARKER_SIMPLE.match(line) or RE_FONTE.match(line):
                in_orazione = False
            else:
                doc.orazione.append(line)
                continue

        marker = RE_MARKER.match(line)
        simple = RE_MARKER_SIMPLE.match(line) if not marker else None
        if marker or simple:
            seen_body = True
            if marker:
                titolo = f"{marker.group('ord').capitalize()} Lettura"
                tag = (marker.group("tag") or "").strip()
            else:
                titolo = simple.group("kind")
                tag = (simple.group("tag") or "").strip()
            pending_titolo = (titolo, tag)
            in_resp = False
            current = None
            continue

        if RE_ALT.match(line):
            seen_body = True
            # «Una delle seguenti» apre un gruppo: la prima voce non è
            # un'alternativa, le successive («Oppure») sì
            alt_flag = line.lower().startswith("oppure")
            in_resp = False
            continue

        if RE_ORAZIONE.match(line):
            in_orazione = True
            in_resp = False
            doc.orazione.append(re.sub(r"^Orazione\s*", "", line).strip())
            continue

        vpag = RE_VPAG.match(line)
        if vpag and (pending_titolo or current is not None or doc.readings):
            seen_body = True
            if pending_titolo:
                titolo, tag = pending_titolo
            else:
                last = current if current is not None else doc.readings[-1]
                titolo, tag = last.titolo, last.tag
            reading = new_reading(titolo, tag, alternative=current is not None and not pending_titolo)
            reading.riferimento = vpag.group("rif").strip()
            reading.sottotitolo = "Testo non riportato nella fonte (rimando a pagina)"
            reading.reference_only = True
            reading.alternative = True
            doc.warnings.append(f"{titolo}: solo riferimento «{reading.riferimento}» (v. pag.)")
            current = None
            continue

        if RE_FONTE.match(line):
            seen_body = True
            if pending_titolo:
                titolo, tag = pending_titolo
                pending_titolo = None
                current = new_reading(titolo, tag, alternative=alt_flag)
            elif current is not None and current.sottotitolo and not current.fonte \
                    and not current.testo and not current.responsorio:
                # il sottotitolo precedeva la fonte: stessa lettura
                pass
            elif current is not None and current.started and current.responsorio:
                # nuova fonte dopo un responsorio completo, senza titolo:
                # è la lettura successiva (o un'alternativa se preceduta
                # da "Oppure")
                if alt_flag:
                    current = new_reading(current.titolo, current.tag, alternative=True)
                else:
                    current = new_reading(next_ordinal(current.titolo), "", alternative=False)
            elif current is not None and current.started:
                current = new_reading(current.titolo, current.tag, alternative=True)
                if not alt_flag:
                    doc.warnings.append(f"{current.titolo}: fonte «{line[:40]}» senza titolo né 'oppure' (trattata come alternativa)")
            elif current is None:
                titolo = "Prima Lettura" if not doc.readings else next_ordinal(doc.readings[-1].titolo)
                current = new_reading(titolo, "", alternative=False)
            alt_flag = False
            in_resp = False
            parse_fonte(line, current, doc.warnings)
            continue

        if RE_RESP.match(line):
            if current is None:
                # responsorio senza lettura: lo si attacca all'ultima
                if doc.readings:
                    current = doc.readings[-1]
                else:
                    doc.header.append(line)
                    continue
            if current.responsorio and alt_flag:
                current.responsorio.append("oppure:")
            alt_flag = False
            in_resp = True
            current.responsorio.append(line)
            continue

        if current is not None and current.started and RE_RESP_LINE.match(line):
            # versetto R./V./* : appartiene al responsorio anche quando
            # manca la riga «Responsorio (...)»
            if not current.responsorio:
                current.responsorio.append("Responsorio")
            in_resp = True
            current.responsorio.append(line)
            continue

        if current is not None and current.started:
            if in_resp and not RE_RESP_LINE.match(line):
                # testo non-versetto dopo il responsorio: lo si accoda
                # comunque al responsorio (es. seconda riga di 'R.')
                current.responsorio.append(line)
                continue
            if not current.testo and len(line) <= 120 \
                    and not re.search(r"[.!?»;:]$", line) and not RE_RESP_LINE.match(line):
                # sottotitolo (eventualmente spezzato su più righe)
                current.sottotitolo = f"{current.sottotitolo} {line}".strip()
                continue
            if not current.testo and not current.sottotitolo and len(line) > 170 \
                    and current.fonte and not RE_RESP_LINE.match(line):
                # primo paragrafo con il sottotitolo incollato davanti
                split = split_glued_subtitle(line)
                if split:
                    current.sottotitolo, line = split
                    doc.warnings.append(f"{current.titolo}: sottotitolo separato euristicamente «{current.sottotitolo[:50]}»")
            current.testo.append(line)
            continue

        if not seen_body:
            doc.header.append(line)
            continue

        # testo dopo un titolo ma senza riga di fonte: la lettura parte
        # comunque (riga breve = sottotitolo, riga lunga = testo), così
        # nulla va perduto; la fonte assente viene segnalata alla fine.
        if pending_titolo:
            titolo, tag = pending_titolo
            pending_titolo = None
            current = new_reading(titolo, tag, alternative=alt_flag)
            alt_flag = False
            if len(line) <= 120 and not re.search(r"[.!?»;:]$", line):
                current.sottotitolo = line
            else:
                current.testo.append(line)
            continue
        doc.warnings.append(f"riga ignorata: «{line[:60]}»")

    # fonte o responsorio assenti (di norma troncature della sorgente)
    for reading in doc.readings:
        if not reading.fonte and not reading.reference_only:
            doc.warnings.append(f"{reading.titolo}: fonte assente")
        if reading.testo and not reading.responsorio and reading.titolo != "Vangelo":
            doc.warnings.append(f"{reading.titolo}: responsorio assente (sorgente troncata?)")
    # fonti in due righe (layout a capo): la seconda contiene il riferimento
    return doc


def merge_split_fonte(lines: List[str]) -> List[str]:
    """Unisce 'Dalla lettera ... di san Paolo,' + 'apostolo (2,16—3,4)'."""
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if RE_FONTE.match(line) and "(" not in line:
            j = i + 1
            while j < len(lines) and not lines[j]:
                j += 1
            if j < len(lines) and re.match(r"^[^()]{0,70}\([^()]*\)\s*\.?\s*$", lines[j]) \
                    and not RE_RESP.match(lines[j]):
                out.append(f"{line} {lines[j]}")
                i = j + 1
                continue
        if RE_FONTE.match(line) and line.count("(") > line.count(")"):
            # parentesi del riferimento spezzata su più righe
            merged = line
            j = i + 1
            steps = 0
            while j < len(lines) and steps < 4 and merged.count("(") > merged.count(")"):
                if lines[j]:
                    merged = f"{merged} {lines[j]}"
                    steps += 1
                j += 1
            if merged.count("(") == merged.count(")"):
                out.append(merged)
                i = j
                continue
        out.append(line)
        i += 1
    return out


# --------------------------------------------------------------------------
# Mappatura cartelle -> chiavi liturgiche
# --------------------------------------------------------------------------

def slug(value: str) -> str:
    value = re.sub(r"^Tempo (di )?", "", value or "", flags=re.I)
    value = value.strip().lower().translate(_ACCENTS)
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def biennale_code(entry: Dict[str, Any]) -> str:
    parts = [slug(entry.get(k) or "") for k in (
        "tempo_liturgico", "settimana_del_tempo", "giorno_settimana",
        "anno_liturgico", "ciclo_biennale")]
    return "-".join(p for p in parts if p)


def cycle_from_folder(parts: Tuple[str, ...]) -> Optional[str]:
    for part in parts:
        low = part.lower()
        if low in ("bien_dispari", "dispari"):
            return "I"
        if low in ("bien_pari", "pari"):
            return "II"
    return None


def weekday_from_name(stem: str) -> Optional[str]:
    return WEEKDAY_CODES.get(stem.upper())


class Target:
    """Dove va un file grezzo e con quali chiavi."""

    def __init__(self, kind: str, **keys: Any) -> None:
        self.kind = kind   # biennale | biennale_data | proprio | da_assegnare | skip
        self.keys = keys


def classify(rel: Path) -> Target:
    parts = rel.parts
    cat = parts[0]
    stem = rel.stem
    cycle = cycle_from_folder(parts)

    if cat == "Ordinario":
        week = int(parts[1].split("_")[0])
        day = weekday_from_name(stem)
        if day == "Domenica+":
            # domenica che chiude la settimana: nel materiale c'è solo il
            # caso di Pentecoste (pari) archiviato sotto Ordinario/06
            return Target("biennale", tempo="Tempo di Pasqua", settimana="VIII",
                          giorno="Domenica", ciclo=cycle,
                          nota="Pentecoste (ciclo pari) archiviata in Ordinario/06_BIEN/8DOM")
        return Target("biennale", tempo="Tempo Ordinario", settimana=ROMAN[week - 1],
                      giorno=day, ciclo=cycle)
    if cat == "Quaresima":
        week = int(parts[1][3:])
        day = weekday_from_name(stem)
        if week == 6 and day in ("Giovedì", "Venerdì", "Sabato"):
            return Target("biennale", tempo="Triduo Pasquale", settimana=None,
                          giorno=day, ciclo=cycle)
        return Target("biennale", tempo="Quaresima", settimana=ROMAN[week - 1],
                      giorno=day, ciclo=cycle)
    if cat == "Ceneri":
        return Target("biennale", tempo="Quaresima", settimana="0",
                      giorno=weekday_from_name(stem), ciclo=cycle)
    if cat == "Pasqua":
        week = int(parts[1][3:])
        day = weekday_from_name(stem)
        if stem.lower() == "7.sab":
            return Target("skip", motivo="duplicato di 7SAB.txt")
        if day == "Domenica+":
            return Target("biennale", tempo="Tempo di Pasqua", settimana=ROMAN[week],
                          giorno="Domenica", ciclo=cycle)
        return Target("biennale", tempo="Tempo di Pasqua", settimana=ROMAN[week - 1],
                      giorno=day, ciclo=cycle)
    if cat == "Avvento":
        if parts[1] == "1724dic":
            day = int(stem.split("_")[0])
            return Target("biennale_data", tempo="Avvento", giorno_mese=day, mese=12, ciclo=cycle)
        week = int(parts[1][3:])
        return Target("biennale", tempo="Avvento", settimana=ROMAN[week - 1],
                      giorno=weekday_from_name(stem), ciclo=cycle)
    if cat == "Natale":
        day, month = int(stem[:2]), int(stem[2:])
        return Target("biennale_data", tempo="Tempo di Natale", giorno_mese=day, mese=month, ciclo=cycle)
    if cat in ("Santi", "Feste"):
        if stem == "test":
            return Target("da_assegnare", motivo="file di prova")
        if re.fullmatch(r"\d{4}", stem):
            month, day = int(stem[:2]), int(stem[2:])
            if cat == "Santi" and (month, day) in ((1, 2), (1, 3), (1, 4), (1, 5)):
                return Target("skip", motivo="ferie 2-5 gennaio: già in Natale/ (entrambi i cicli)")
            return Target("proprio", giorno_mese=day, mese=month, categoria=cat)
        return Target("da_assegnare", motivo="festa mobile")
    return Target("skip", motivo="categoria sconosciuta")


# --------------------------------------------------------------------------
# Costruzione dei JSON
# --------------------------------------------------------------------------

def clean_titolo(reading: Reading, drop_cycle_tag: bool) -> str:
    titolo = reading.titolo
    tag = reading.tag
    if tag and not drop_cycle_tag:
        titolo = f"{titolo} ({tag})"
    if reading.alternative:
        titolo = f"{titolo} (oppure)"
    return titolo


def readings_to_list(doc: Parsed, drop_cycle_tag: bool) -> List[Dict[str, Any]]:
    letture = []
    for reading in doc.readings:
        item = reading.to_dict()
        item["titolo"] = clean_titolo(reading, drop_cycle_tag)
        if item["riferimento"] or item["testo"] or item["fonte"]:
            letture.append(item)
    return letture


def header_santo(header: List[str]) -> Tuple[str, Optional[str], List[str]]:
    """Nome del santo (o della festa), grado, note dall'intestazione."""
    ranks = ("Solennità", "Festa", "Memoria", "Memoria facoltativa", "Commemorazione")
    rank_re = re.compile(r"\s+(Solennità|Festa|Memoria facoltativa|Memoria|Commemorazione)\s*$")
    lines: List[str] = []
    for raw in header:
        line = re.sub(r"^\d{1,2}\s+[A-Za-zÀ-ú]+\s*", "", raw).strip()   # via la data
        if not line:
            continue
        # intestazione compattata su una riga: «SAN LUCA Evangelista Festa»
        m = rank_re.search(line)
        if m and line[:m.start()].strip():
            line, tail = line[:m.start()].strip(), m.group(1)
            for piece in _split_upper_run(line):
                lines.append(piece)
            lines.append(tail)
            continue
        lines.extend(_split_upper_run(line))
    tipo = None
    upper_parts: List[str] = []     # righe in MAIUSCOLO: il nome
    qualifier_parts: List[str] = [] # righe brevi subito dopo: la qualifica
    notes: List[str] = []
    name_done = False
    for line in lines:
        if line in ranks:
            tipo = line
            name_done = True
            continue
        continuation = re.match(r"^[eE]\s+[A-ZÀ-Ú]{3,}", line)  # «e CIPRIANO, vescovo»
        is_note = len(line) > 70 or line.endswith(":") or (line[:1].islower() and not continuation) \
            or re.match(r"^(Dopo|Quando|Il seguente|La prima|Nell[’']ottava|Domenica dopo)", line)
        if is_note:
            notes.append(line)
            continue
        if _is_upper(line) and not name_done and not qualifier_parts:
            upper_parts.append(line)
        elif upper_parts and not name_done:
            qualifier_parts.append(line)
        else:
            notes.append(line)
    if upper_parts:
        main = _title_case(" ".join(upper_parts))
        rest = [q[0].lower() + q[1:] if q[:1].isupper() and not _is_upper(q) else _title_case(q).lower()
                for q in qualifier_parts if q]
        santo = ", ".join([main] + rest)
    else:
        santo = ", ".join(qualifier_parts)
    if not tipo and "Commemorazione" in santo:
        tipo = "Commemorazione"
    return santo, tipo, notes


def _split_upper_run(line: str) -> List[str]:
    """«SAN LUCA Evangelista» -> ['SAN LUCA', 'Evangelista'].

    Separa la sequenza iniziale di parole maiuscole dalla qualifica in
    minuscolo che la segue sulla stessa riga (solo se la riga inizia
    con almeno due parole maiuscole).
    """
    m = re.match(r"^((?:[A-ZÀ-Ú][A-ZÀ-Ú’'.\-]*[,]?\s+){2,}[A-ZÀ-Ú][A-ZÀ-Ú’'.\-]*[,]?)\s+([A-Z][a-zà-ú].*)$", line)
    if m:
        return [m.group(1).strip(), m.group(2).strip()]
    return [line]


def _is_upper(line: str) -> bool:
    """Riga «di nome»: in maiuscolo nel complesso, oppure che inizia con
    una parola maiuscola di almeno tre lettere («SANTI CORNELIO, papa»)."""
    letters = [c for c in line if c.isalpha()]
    if not letters:
        return False
    if sum(1 for c in letters if c.isupper()) >= 0.6 * len(letters):
        return True
    return bool(re.match(r"^(?:[eE]\s+)?[A-ZÀ-Ú][A-ZÀ-Ú’']{2,}", line))


_LOWER_WORDS = {"di", "e", "della", "del", "dei", "delle", "degli", "da", "a", "ed",
                "il", "la", "lo", "i", "le", "gli", "in", "su", "per", "con", "nostro",
                "dell", "dall", "dopo", "tra", "fra"}


def _title_case(value: str) -> str:
    """Solo le parole tutte MAIUSCOLE vengono ricomposte; le altre
    (già in minuscolo o Capitalizzate nella sorgente) restano come sono."""
    words = []
    for index, word in enumerate(value.split()):
        low = word.lower()
        if low in ("ss.", "ss.ma"):
            words.append("SS." if low == "ss." else "SS.ma")
            continue
        if index and low in _LOWER_WORDS:
            words.append(low)
            continue
        if word != word.upper():
            words.append(word)
            continue
        # apostrofi: SANT’AGNESE -> Sant’Agnese, D’ASSISI -> d’Assisi
        parts = re.split(r"([’'])", word)
        parts = [p.capitalize() if p not in ("’", "'") else p for p in parts]
        fixed = "".join(parts)
        if index and re.match(r"^D[’']", fixed):
            fixed = "d" + fixed[1:]
        words.append(fixed)
    return " ".join(words)


def build_biennale(target: Target, doc: Parsed, source: Path) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "tempo_liturgico": target.keys["tempo"],
        "settimana_del_tempo": target.keys.get("settimana"),
        "giorno_settimana": target.keys.get("giorno"),
        "anno_liturgico": None,
        "ciclo_biennale": target.keys.get("ciclo"),
        "letture": readings_to_list(doc, drop_cycle_tag=True),
    }
    if doc.orazione:
        entry["orazione"] = " ".join(doc.orazione).strip()
    entry["codice"] = biennale_code(entry)
    entry["fonte_raw"] = str(source.relative_to(RAW_DIR)).replace("\\", "/")
    return entry


def build_biennale_data(target: Target, doc: Parsed, source: Path) -> Dict[str, Any]:
    day, month = target.keys["giorno_mese"], target.keys["mese"]
    entry: Dict[str, Any] = {
        "tempo_liturgico": target.keys["tempo"],
        "settimana_del_tempo": None,
        "giorno_settimana": None,
        "anno_liturgico": None,
        "ciclo_biennale": target.keys.get("ciclo"),
        "data": f"{day:02d}-{month:02d}",
        "data_estesa": f"{day} {MONTHS_IT[month - 1]}",
        "letture": readings_to_list(doc, drop_cycle_tag=True),
    }
    if doc.orazione:
        entry["orazione"] = " ".join(doc.orazione).strip()
    entry["codice"] = "-".join(p for p in (
        slug(entry["tempo_liturgico"]), str(day), slug(MONTHS_IT[month - 1]),
        slug(entry["ciclo_biennale"] or "")) if p)
    entry["fonte_raw"] = str(source.relative_to(RAW_DIR)).replace("\\", "/")
    return entry


def build_proprio(target: Target, doc: Parsed, source: Path) -> Dict[str, Any]:
    day, month = target.keys["giorno_mese"], target.keys["mese"]
    santo, tipo, notes = header_santo(doc.header)
    entry: Dict[str, Any] = {
        "data": f"{day:02d}-{month:02d}",
        "giorno": day,
        "mese": MONTHS_IT[month - 1],
        "mese_numero": month,
        "data_estesa": f"{day} {MONTHS_IT[month - 1]}",
        "santo": santo,
        "tipo": tipo,
        "letture": readings_to_list(doc, drop_cycle_tag=False),
        "orazione": " ".join(doc.orazione).strip(),
    }
    if notes:
        entry["note"] = notes
    entry["fonte_raw"] = str(source.relative_to(RAW_DIR)).replace("\\", "/")
    return entry


def build_da_assegnare(target: Target, doc: Parsed, source: Path) -> Dict[str, Any]:
    santo, tipo, notes = header_santo(doc.header)
    entry: Dict[str, Any] = {
        "celebrazione": santo,
        "tipo": tipo,
        "motivo": target.keys.get("motivo"),
        "letture": readings_to_list(doc, drop_cycle_tag=False),
        "orazione": " ".join(doc.orazione).strip(),
    }
    if notes:
        entry["note"] = notes
    entry["fonte_raw"] = str(source.relative_to(RAW_DIR)).replace("\\", "/")
    return entry


# --------------------------------------------------------------------------
# Esecuzione
# --------------------------------------------------------------------------

def write_json(path: Path, entry: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=4) + "\n",
                    encoding="utf-8", newline="\n")


def expected_days() -> List[Tuple[str, str, str, str]]:
    """Giornate attese nel ciclo stagionale, per il conteggio dei buchi."""
    out: List[Tuple[str, str, str, str]] = []
    days = ("Domenica", "Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato")
    for cycle in ("I", "II"):
        for week in range(1, 35):
            for day in days:
                if week == 1 and day == "Domenica":
                    continue  # Battesimo del Signore
                out.append(("Tempo Ordinario", ROMAN[week - 1], day, cycle))
        for week in range(1, 7):
            for day in days:
                if week == 6 and day in ("Giovedì", "Venerdì", "Sabato"):
                    out.append(("Triduo Pasquale", "", day, cycle))
                else:
                    out.append(("Quaresima", ROMAN[week - 1], day, cycle))
        for day in ("Mercoledì", "Giovedì", "Venerdì", "Sabato"):
            out.append(("Quaresima", "0", day, cycle))
        for week in range(1, 8):
            for day in days:
                out.append(("Tempo di Pasqua", ROMAN[week - 1], day, cycle))
        out.append(("Tempo di Pasqua", "VIII", "Domenica", cycle))
        for week in range(1, 4):
            for day in days:
                out.append(("Avvento", ROMAN[week - 1], day, cycle))
    return out


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--solo", help="converte solo i file il cui percorso contiene questo testo")
    parser.add_argument("--pulisci", action="store_true", help="svuota prima la cartella json/")
    args = parser.parse_args(argv)

    if args.pulisci and OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in RAW_DIR.rglob("*.txt") if OUT_DIR not in p.parents)
    if args.solo:
        files = [p for p in files if args.solo.replace("\\", "/") in str(p).replace("\\", "/")]

    counts: Counter = Counter()
    warnings: Dict[str, List[str]] = {}
    skipped: List[Tuple[str, str]] = []
    produced: Dict[str, List[str]] = defaultdict(list)
    codes_seen: Dict[str, str] = {}
    biennale_keys = set()

    for path in files:
        rel = path.relative_to(RAW_DIR)
        rel_str = str(rel).replace("\\", "/")
        target = classify(rel)
        if target.kind == "skip":
            skipped.append((rel_str, target.keys.get("motivo", "")))
            counts["saltati"] += 1
            continue
        text = normalize_text(path.read_bytes())
        lines = merge_split_fonte(logical_lines(text))
        doc = parse_document(lines)
        if target.kind in ("biennale", "biennale_data"):
            # tag (D)/(P)/(I)/(II) incoerenti con la cartella
            for reading in doc.readings:
                tag = reading.tag.upper()
                cyc = target.keys.get("ciclo")
                if (tag == "D" and cyc == "II") or (tag == "P" and cyc == "I") \
                        or (tag == "I" and cyc == "II") or (tag == "II" and cyc == "I"):
                    doc.warnings.append(f"{reading.titolo}: tag ({reading.tag}) incoerente con la cartella (ciclo {cyc})")
        if target.keys.get("nota"):
            doc.warnings.append(target.keys["nota"])
        if not doc.readings:
            doc.warnings.append("nessuna lettura riconosciuta")

        if target.kind == "biennale":
            entry = build_biennale(target, doc, path)
            out = OUT_DIR / "biennale" / f"{entry['codice']}.json"
            key = entry["codice"]
            biennale_keys.add((entry["tempo_liturgico"], entry["settimana_del_tempo"] or "",
                               entry["giorno_settimana"], entry["ciclo_biennale"]))
        elif target.kind == "biennale_data":
            entry = build_biennale_data(target, doc, path)
            # stessa cartella del ciclo stagionale: la webapp le trova per
            # data (BiennaleStore.date_code / repository._find_biennale)
            out = OUT_DIR / "biennale" / f"{entry['codice']}.json"
            key = "data:" + entry["codice"]
        elif target.kind == "proprio":
            entry = build_proprio(target, doc, path)
            key = "proprio:" + entry["data"]
            if key in codes_seen:
                # stessa data in Santi/ e Feste/: vince quella con più letture
                prev_path = OUT_DIR / "proprio" / f"{entry['data']}.json"
                prev_entry = json.loads(prev_path.read_text(encoding="utf-8"))
                if len(entry["letture"]) <= len(prev_entry["letture"]):
                    out = OUT_DIR / "duplicati" / f"{entry['data']}__{rel.parts[0]}.json"
                    doc.warnings.append(f"stessa data di {codes_seen[key]}: conservata come duplicato")
                    write_json(out, entry)
                    warnings[rel_str] = doc.warnings
                    counts["duplicati"] += 1
                    continue
                dup_out = OUT_DIR / "duplicati" / f"{entry['data']}__{Path(codes_seen[key]).parts[0]}.json"
                write_json(dup_out, prev_entry)
                doc.warnings.append(f"sostituisce {codes_seen[key]} (meno letture), spostato in duplicati/")
                counts["duplicati"] += 1
            out = OUT_DIR / "proprio" / f"{entry['data']}.json"
        else:
            entry = build_da_assegnare(target, doc, path)
            out = OUT_DIR / "da_assegnare" / f"{slug(rel.stem)}.json"
            key = "da_assegnare:" + rel.stem

        if key in codes_seen and target.kind != "proprio":
            doc.warnings.append(f"codice {key} già prodotto da {codes_seen[key]}: sovrascritto")
        codes_seen[key] = rel_str
        write_json(out, entry)
        produced[target.kind].append(str(out.relative_to(OUT_DIR)).replace("\\", "/"))
        counts[target.kind] += 1
        counts["letture"] += len(entry["letture"])
        if doc.warnings:
            warnings[rel_str] = doc.warnings

    # giornate mancanti nel ciclo stagionale
    missing = [k for k in expected_days() if k not in biennale_keys]

    report = [
        "# Conversione dei testi grezzi del Biennale",
        "",
        f"File grezzi esaminati: {len(files)}",
        "",
        "| Destinazione | File prodotti |",
        "|---|---|",
        f"| biennale/ (ciclo stagionale, schema di data/biennale) | {counts['biennale']} |",
        f"| biennale/ con codice per data (17-24 dic, 29-31 dic, 2-12 gen; campo `data`) | {counts['biennale_data']} |",
        f"| proprio/ (santi e feste a data fissa, schema di data/proprio) | {counts['proprio']} |",
        f"| da_assegnare/ (feste mobili e file di prova) | {counts['da_assegnare']} |",
        f"| duplicati/ (stessa data in Santi/ e Feste/) | {counts['duplicati']} |",
        f"| saltati (duplicati esatti o già coperti) | {counts['saltati']} |",
        "",
        f"Letture totali estratte: {counts['letture']}",
        "",
        "## Regole di mappatura",
        "",
        "- `bien_dispari` / `dispari` → ciclo **I**; `bien_pari` / `pari` → ciclo **II**.",
        "- `Ordinario/NN_BIEN` → Tempo Ordinario, settimana NN in numeri romani; `1DOM`…`7SAB` → giorno.",
        "- `Quaresima/QUA0N` → Quaresima N; `QUA06` giovedì/venerdì/sabato → **Triduo Pasquale** (settimana vuota).",
        "- `Ceneri/` → Quaresima, settimana **0** (come nei metadati CEI).",
        "- `Pasqua/PAS0N` → Tempo di Pasqua N; `8DOM` → domenica della settimana successiva (Pentecoste = VIII).",
        "- `Avvento/AVV0N` → Avvento N; `Avvento/1724dic` e `Natale/` → voci a **data fissa** (cartella biennale_data/).",
        "- `Santi/` e `Feste/` con nome `MMGG` → Proprio (`GG-MM.json`); nomi non numerici → da_assegnare/.",
        "- Il tag `(D)`, `(P)`, `(I)`, `(II)`, `(I/II)` nei titoli è tolto nelle voci stagionali (il ciclo è dato dalla cartella).",
        "- Le letture alternative (`Oppure:`, `Una delle seguenti:`) sono voci separate con suffisso **(oppure)** nel titolo.",
        "- `riferimento` = contenuto tra parentesi della riga della fonte (es. `14,1-24`, `Lib. 1,2.5.7-9`).",
        "- `<` e `>` dell'OCR sono resi come « e »; i paragrafi sono separati da `\\n`.",
        "- L'`Orazione` finale, quando presente, è conservata nel campo `orazione`.",
        "- Ogni JSON riporta in `fonte_raw` il file grezzo di origine.",
        "",
        "## Giornate assenti nella sorgente (ciclo stagionale)",
        "",
        f"Mancano {len(missing)} combinazioni tempo/settimana/giorno/ciclo:",
        "",
    ]
    for tempo, week, day, cycle in missing:
        report.append(f"- {tempo} {week} {day} — ciclo {cycle}")
    report += ["", "## File saltati", ""]
    for rel_str, motivo in skipped:
        report.append(f"- `{rel_str}` — {motivo}")
    report += ["", f"## Avvisi per file ({len(warnings)} file)", ""]
    for rel_str in sorted(warnings):
        report.append(f"### {rel_str}")
        for w in warnings[rel_str]:
            report.append(f"- {w}")
        report.append("")
    (OUT_DIR / "REPORT.md").write_text("\n".join(report), encoding="utf-8", newline="\n")

    print(f"file esaminati: {len(files)}")
    for k in ("biennale", "biennale_data", "proprio", "da_assegnare", "duplicati", "saltati"):
        print(f"  {k:15s} {counts[k]}")
    print(f"  letture totali  {counts['letture']}")
    print(f"  file con avvisi {len(warnings)}")
    print(f"  giornate mancanti nel ciclo stagionale: {len(missing)}")
    print(f"report: {OUT_DIR / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
