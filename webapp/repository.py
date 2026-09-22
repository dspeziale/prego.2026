"""Accesso in sola lettura ai dati raccolti da LiturgiaCollector.

Legge la cartella `output/` (una sottocartella per data, con
metadata.json e i file .txt) e la espone alle viste Flask con oggetti
di dominio semplici. Nessuna dipendenza dal package liturgia_collector.
"""

import json
import logging
import re
from datetime import date, timedelta

from biennale import BiennaleStore
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MONTHS_IT = (
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
)

WEEKDAYS_SHORT_IT = ("Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom")

# Ordine e titoli di visualizzazione dei documenti.
DOCUMENT_TITLES: Tuple[Tuple[str, str], ...] = (
    ("liturgia-del-giorno", "Messa del Giorno"),
    ("santo-del-giorno", "Santo del Giorno"),
    ("ufficio-delle-letture", "Ufficio delle Letture"),
    ("lodi-mattutine", "Lodi Mattutine"),
    ("ora-media", "Ora Media"),
    ("vespri", "Vespri"),
    ("primi-vespri", "Primi Vespri"),
    ("secondi-vespri", "Secondi Vespri"),
    ("compieta", "Compieta"),
    ("compieta-primi-vespri", "Compieta dopo i Primi Vespri"),
    ("compieta-secondi-vespri", "Compieta dopo i Secondi Vespri"),
)

# Colore liturgico -> classe badge (viola/rosa definite nel CSS custom).
COLOR_BADGES: Dict[str, str] = {
    "Verde": "success",
    "Rosso": "danger",
    "Viola": "viola",
    "Bianco": "secondary",
    "Rosa": "rosa",
}

# Colore liturgico -> tinta per elementi grafici (il bianco è reso oro).
COLOR_HEX: Dict[str, str] = {
    "Verde": "#2e7d32",
    "Rosso": "#d00000",
    "Viola": "#6a1b9a",
    "Bianco": "#c9a227",
    "Rosa": "#d81b60",
}

# Ore presenti in forma strutturata nel metadata.json:
# (chiave metadata, slug txt di fallback, titolo tab).
STRUCTURED_HOURS: Tuple[Tuple[str, str, str], ...] = (
    ("liturgia_del_giorno", "liturgia-del-giorno", "Messa del Giorno"),
    ("ufficio_delle_letture", "ufficio-delle-letture", "Ufficio delle Letture"),
    ("lodi_mattutine", "lodi-mattutine", "Lodi Mattutine"),
    ("ora_media", "ora-media", "Ora Media"),
    ("vespri", "vespri", "Vespri"),
    ("compieta", "compieta", "Compieta"),
    ("compieta_primi_vespri", "compieta-primi-vespri",
     "Compieta dopo i Primi Vespri"),
    ("compieta_secondi_vespri", "compieta-secondi-vespri",
     "Compieta dopo i Secondi Vespri"),
)

SECTION_LABELS: Dict[str, str] = {
    "introduzione": "Introduzione",
    "inno": "Inno",
    "antifone_e_salmi": "Antifone e Salmi",
    "lettura_breve": "Lettura Breve",
    "responsorio": "Responsorio",
    "versetto": "Versetto",
    "prima_lettura": "Prima Lettura",
    "responsorio_prima_lettura": "Responsorio",
    "seconda_lettura": "Seconda Lettura",
    "responsorio_seconda_lettura": "Responsorio",
    "te_deum": "Te Deum",
    "antifona_al_benedictus": "Antifona al Benedictus",
    "cantico_di_zaccaria": "Cantico di Zaccaria (Benedictus)",
    "antifona_al_magnificat": "Antifona al Magnificat",
    "cantico_della_beata_vergine": "Cantico della B.V. Maria (Magnificat)",
    "invocazioni": "Invocazioni",
    "intercessioni": "Intercessioni",
    "orazione": "Orazione",
    # Messa del giorno
    "antifona_d_ingresso": "Antifona d'ingresso",
    "colletta": "Colletta",
    "salmo_responsoriale": "Salmo Responsoriale",
    "sequenza": "Sequenza",
    "acclamazione_al_vangelo": "Acclamazione al Vangelo",
    "vangelo": "Vangelo",
    "sulle_offerte": "Sulle offerte",
    "antifona_alla_comunione": "Antifona alla comunione",
    "dopo_la_comunione": "Dopo la comunione",
    # Compieta
    "antifona_al_cantico": "Antifona al Cantico",
    "cantico_di_simeone": "Cantico di Simeone (Nunc dimittis)",
    "benedizione": "Benedizione",
    "antifona_alla_beata_vergine": "Antifona alla Beata Vergine",
}

# Gradi con cui il Proprio del santo entra nella scheda Giorno. Nei
# primi due sostituisce le letture feriali del Biennale; nelle memorie
# le affianca.
PROPRIO_REPLACES_BIENNALE = ("Solennità", "Festa", "Commemorazione")
PROPRIO_GRADES = PROPRIO_REPLACES_BIENNALE + ("Memoria", "Memoria facoltativa")

# Parole che non identificano un santo nel confronto fra il nome del
# Proprio e la celebrazione del giorno.
_NAME_STOPWORDS = frozenset({
    "san", "santa", "santi", "sante", "sant", "santo", "santissima",
    "santissimo", "ss", "beata", "beato", "beati", "vergine", "vergini",
    "martire", "martiri", "vescovo", "vescovi", "papa", "sacerdote",
    "sacerdoti", "dottore", "della", "delle", "del", "dei", "degli", "di",
    "e", "ed", "il", "la", "lo", "le", "gli", "chiesa", "apostolo",
    "apostoli", "evangelista", "religiosa", "religioso", "abate",
    "diacono", "compagni", "memoria", "facoltativa", "festa", "solennita",
    "commemorazione", "messa", "giorno", "vespertina", "vigilia", "anno",
    "nella", "nel", "primo", "protomartire", "patrono", "patrona",
    "italia", "europa", "d", "de",
})

_ACCENTS_TRANSLATION = str.maketrans("àáâèéêìíîòóôùúû", "aaaeeeiiiooouuu")


def _name_tokens(text: str) -> set:
    """Parole significative di un nome, minuscole e senza accenti."""
    text = (text or "").lower().translate(_ACCENTS_TRANSLATION)
    return {
        tok for tok in re.findall(r"[a-z]+", text)
        if tok not in _NAME_STOPWORDS and len(tok) > 1
    }


ORA_MEDIA_LABELS: Dict[str, str] = {
    "terza": "Terza",
    "sesta": "Sesta",
    "nona": "Nona",
}

# Etichette brevi delle schede per la visualizzazione su smartphone.
SHORT_TITLES: Dict[str, str] = {
    "liturgia-del-giorno": "Messa",
    "santo-del-giorno": "Santo",
    "ufficio-delle-letture": "Ufficio",
    "lodi-mattutine": "Lodi",
    "ora-media": "Media",
    "vespri": "Vespri",
    "compieta": "Compieta",
    "primi-vespri": "I Vespri",
    "secondi-vespri": "II Vespri",
    "compieta-primi-vespri": "Compieta I",
    "compieta-secondi-vespri": "Compieta II",
}


class DocumentRecord:
    """Un file TXT liturgico caricato da disco."""

    def __init__(self, slug: str, title: str, text: str) -> None:
        self.slug = slug
        self.title = title
        self.text = text


class HourSection:
    """Una sezione logica di un'ora (testo semplice o gruppi di salmodia)."""

    def __init__(self, key: str, value: Any, label: Optional[str] = None) -> None:
        self.key = key
        self.label = label or SECTION_LABELS.get(
            key, key.replace("_", " ").title()
        )
        self.groups: Optional[List[str]] = value if isinstance(value, list) else None
        self.text: Optional[str] = value if isinstance(value, str) else None


class HourTab:
    """Una scheda della vista giornaliera.

    kind: 'text' (TXT integrale), 'structured' (sezioni dal metadata),
    'ora_media' (tre blocchi strutturati Terza/Sesta/Nona).
    """

    def __init__(self, slug: str, title: str, kind: str) -> None:
        self.slug = slug
        self.title = title
        self.short_title = SHORT_TITLES.get(slug, title)
        self.kind = kind
        self.text: Optional[str] = None
        self.sections: List[HourSection] = []
        self.sub_hours: List[Tuple[str, List[HourSection]]] = []
        self.santo: Optional[Dict[str, Any]] = None

    @staticmethod
    def from_text(document: "DocumentRecord") -> "HourTab":
        tab = HourTab(document.slug, document.title, "text")
        tab.text = document.text
        return tab

    @staticmethod
    def from_sections(slug: str, title: str, data: Dict[str, Any]) -> "HourTab":
        tab = HourTab(slug, title, "structured")
        tab.sections = [HourSection(key, value) for key, value in data.items()]
        return tab

    @staticmethod
    def from_santo(slug: str, title: str, data: Dict[str, Any]) -> "HourTab":
        tab = HourTab(slug, title, "santo")
        tab.santo = data
        return tab

    @staticmethod
    def from_ora_media(slug: str, title: str, data: Dict[str, Any]) -> "HourTab":
        tab = HourTab(slug, title, "ora_media")
        tab.sub_hours = [
            (ORA_MEDIA_LABELS.get(name, name.title()),
             [HourSection(key, value) for key, value in block.items()])
            for name, block in data.items()
        ]
        return tab


class DayRecord:
    """Una giornata raccolta: metadati + documenti."""

    def __init__(
        self,
        day: date,
        metadata: Dict[str, Any],
        documents: List[DocumentRecord],
    ) -> None:
        self.day = day
        self.metadata = metadata
        self.documents = documents
        self.tabs: List[HourTab] = []
        self.proprio: Optional[Dict[str, Any]] = None
        self.giorno_sections: List[HourSection] = []

    @property
    def iso(self) -> str:
        return self.day.isoformat()

    @property
    def celebration(self) -> str:
        return self.metadata.get("celebrazione") or "—"

    @property
    def color(self) -> Optional[str]:
        return self.metadata.get("colore")

    @property
    def color_badge(self) -> str:
        return COLOR_BADGES.get(self.color or "", "dark")

    @property
    def color_hex(self) -> str:
        """Tinta del colore liturgico del giorno."""
        return COLOR_HEX.get(self.color or "", "#8e1600")

    # Campi mostrati (solo valore, senza etichetta) nel riquadro del
    # giorno della vista mensile.
    SUMMARY_KEYS = (
        "anno_liturgico",
        "ciclo_biennale",
        "tempo_liturgico",
        "settimana_del_tempo",
        "grado",
        "colore",
        "settimana_del_salterio",
    )

    @property
    def header_parts(self) -> List[str]:
        """Badge testuali dell'intestazione mobile.

        Es.: ['XIV Ordinario', 'II Salterio'] — anno e ciclo sono resi
        a parte come badge colorati.
        """
        meta = self.metadata
        parts = []
        season = re.sub(r"^Tempo (di )?", "", meta.get("tempo_liturgico") or "")
        week = meta.get("settimana_del_tempo")
        if season and week is not None:
            parts.append(f"{week} {season}")
        elif season:
            parts.append(season)
        if meta.get("settimana_del_salterio"):
            parts.append(f"{meta['settimana_del_salterio']} Salterio")
        return parts

    @property
    def summary_values(self) -> List[str]:
        """Valori sintetici della giornata, nell'ordine di SUMMARY_KEYS.

        Il tempo liturgico è abbreviato togliendo 'Tempo (di)':
        'Tempo Ordinario' -> 'Ordinario', 'Tempo di Pasqua' -> 'Pasqua'.
        """
        values = []
        for key in self.SUMMARY_KEYS:
            value = self.metadata.get(key)
            if value is None:
                continue
            if key == "tempo_liturgico":
                value = re.sub(r"^Tempo (di )?", "", str(value))
            values.append(str(value))
        return values


class LiturgiaRepository:
    """Repository in sola lettura su output/ (TXT) e json/ (metadati)."""

    def __init__(
        self,
        output_dir: Path,
        json_dir: Path,
        proprio_store: Optional[Any] = None,
        biennale_store: Optional[Any] = None,
    ) -> None:
        self._output_dir = output_dir
        self._json_dir = json_dir
        self._proprio_store = proprio_store
        self._biennale_store = biennale_store

    # ------------------------------------------------------------------
    # Elenco giorni e mesi
    # ------------------------------------------------------------------

    def available_days(self) -> List[date]:
        """Date raccolte, in ordine crescente.

        Unione delle cartelle TXT e dei metadati JSON: così l'app
        funziona anche nei deploy senza la cartella output/.
        """
        days = set()
        if self._output_dir.is_dir():
            for entry in self._output_dir.iterdir():
                if entry.is_dir():
                    try:
                        days.add(date.fromisoformat(entry.name))
                    except ValueError:
                        logger.warning(
                            "Cartella ignorata (nome non-data): %s", entry
                        )
        if self._json_dir.is_dir():
            for entry in self._json_dir.glob("*.json"):
                try:
                    days.add(date.fromisoformat(entry.stem))
                except ValueError:
                    logger.warning("JSON ignorato (nome non-data): %s", entry)
        return sorted(days)

    def available_months(self) -> List[Tuple[int, int]]:
        """Coppie (anno, mese) con almeno una giornata raccolta."""
        return sorted({(d.year, d.month) for d in self.available_days()})

    # ------------------------------------------------------------------
    # Dettaglio giornata
    # ------------------------------------------------------------------

    def day(self, iso: str, with_documents: bool = True) -> Optional[DayRecord]:
        """Carica una giornata; None se non raccolta."""
        try:
            day = date.fromisoformat(iso)
        except ValueError:
            return None
        day_dir = self._output_dir / iso
        if not day_dir.is_dir() and not (self._json_dir / f"{iso}.json").is_file():
            return None
        metadata = self._read_metadata(iso)
        documents = self._read_documents(day_dir) if with_documents else []
        record = DayRecord(day, metadata, documents)
        if with_documents:
            record.tabs = self._build_tabs(metadata, documents)
            if self._proprio_store is not None:
                record.proprio = self._proprio_store.load(
                    f"{day.day:02d}-{day.month:02d}"
                )
            record.giorno_sections = self._giorno_sections(
                record.tabs, record.proprio, metadata
            )
        return record

    def _giorno_sections(
        self,
        tabs: List[HourTab],
        proprio: Optional[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> List[HourSection]:
        """Sezioni della scheda 'Giorno'.

        Lodi, con il Vangelo della Messa e i testi del Proprio inseriti
        prima dell'Antifona al Benedictus, nello stesso layout.
        """
        lodi = next(
            (tab for tab in tabs
             if tab.slug == "lodi-mattutine" and tab.kind == "structured"),
            None,
        )
        sections = list(lodi.sections) if lodi else []
        extra: List[HourSection] = []
        # Il Proprio del santo entra solo se quel santo è davvero celebrato
        # (grado e nome nella celebrazione del giorno). Nelle solennità e
        # nelle feste sostituisce le letture feriali del Biennale; nelle
        # memorie le affianca (prima lettura feriale, seconda del santo).
        proprio_in_uso = bool(proprio) and self.proprio_applies(proprio, metadata)
        grado = (metadata.get("grado") or "").strip()
        if not (proprio_in_uso and grado in PROPRIO_REPLACES_BIENNALE):
            biennale = self._find_biennale(metadata)
            if biennale:
                extra.extend(self._biennale_sections(biennale))
        if proprio_in_uso:
            extra.extend(self._proprio_sections(proprio))
        if not extra:
            # Senza Biennale né Proprio: le letture dell'Ufficio.
            extra.extend(self._office_reading_sections(metadata))
        # Il Vangelo della Messa è sempre l'ultimo inserto prima
        # dell'Antifona al Benedictus.
        mass = metadata.get("liturgia_del_giorno") or {}
        if mass.get("vangelo"):
            extra.append(HourSection(
                "vangelo_messa", mass["vangelo"], label="Vangelo della Messa",
            ))
        if not extra:
            return sections
        insert_at = next(
            (i for i, section in enumerate(sections)
             if section.key == "antifona_al_benedictus"),
            len(sections),
        )
        return sections[:insert_at] + extra + sections[insert_at:]

    @staticmethod
    def _reading_sections(
        readings: List[Dict[str, Any]], key_prefix: str
    ) -> List[HourSection]:
        """Letture (riferimento, fonte, sottotitolo, testo, responsorio)."""
        sections = []
        for reading in readings:
            fonte = (reading.get("fonte") or "").strip()
            riferimento = (reading.get("riferimento") or "").strip()
            if fonte and riferimento and "(" not in riferimento:
                # «Dalla lettera agli Efesini di san Paolo, apostolo (4,1-16)»
                lines = [f"{fonte} ({riferimento})"]
            else:
                lines = [value for value in (riferimento, fonte) if value]
            if reading.get("sottotitolo"):
                lines.append(reading["sottotitolo"])
            if reading.get("testo"):
                lines.append("")
                lines.append(reading["testo"])
            sections.append(HourSection(
                f"{key_prefix}_lettura", "\n".join(lines),
                label=reading.get("titolo", "Lettura"),
            ))
            if reading.get("responsorio"):
                sections.append(HourSection(
                    f"{key_prefix}_responsorio", reading["responsorio"],
                    label="Responsorio",
                ))
        return sections

    @staticmethod
    def proprio_applies(entry: Dict[str, Any], metadata: Dict[str, Any]) -> bool:
        """True se il santo del Proprio è celebrato in quella giornata.

        Il file del Proprio esiste per la data (es. 22-11, santa Cecilia)
        anche quando la giornata è occupata da una celebrazione superiore
        (Cristo Re): si controlla che il grado sia di festa e che il nome
        del santo compaia nella celebrazione del giorno. Senza
        celebrazione nei metadati si ripiega sul santo del giorno.
        """
        grado = (metadata.get("grado") or "").strip()
        if grado not in PROPRIO_GRADES:
            return False
        wanted = _name_tokens(entry.get("santo") or "")
        if not wanted:
            return False
        celebration = metadata.get("celebrazione") or metadata.get("santo_del_giorno") or ""
        found = _name_tokens(celebration)
        common = wanted & found
        # basta la metà delle parole significative (almeno una): copre
        # «Santi Cornelio e Cipriano» vs «SANTI CORNELIO, PAPA, E CIPRIANO»
        return len(common) * 2 >= len(wanted)

    def _proprio_sections(self, entry: Dict[str, Any]) -> List[HourSection]:
        """Sezioni del Proprio nel layout delle ore."""
        header = entry.get("santo", "")
        if entry.get("tipo"):
            header += f" — {entry['tipo']}"
        sections = [HourSection("proprio", header, label="Dal Proprio")]
        sections.extend(
            self._reading_sections(entry.get("letture") or [], "proprio")
        )
        if entry.get("orazione"):
            sections.append(HourSection(
                "proprio_orazione", entry["orazione"], label="Orazione",
            ))
        return sections

    def _find_biennale(
        self, metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Cerca nel Biennale la voce che combacia con la giornata.

        Prova lo slug completo (tempo-settimana-giorno-anno-ciclo) e poi
        varianti via via più generiche (anno A/B/C, senza anno, senza
        ciclo).
        """
        if self._biennale_store is None:
            return None
        # Prima le ferie a data fissa (17-24 dicembre e Tempo di Natale):
        # le loro letture sono proprie del giorno del mese, non della
        # settimana. Con il ciclo dell'anno, poi senza.
        try:
            day = date.fromisoformat(metadata.get("data") or "")
        except ValueError:
            day = None
        if day is not None and metadata.get("tempo_liturgico"):
            for cycle in (metadata.get("ciclo_biennale") or "", ""):
                code = BiennaleStore.date_code(
                    metadata["tempo_liturgico"], day.day, day.month, cycle
                )
                entry = self._biennale_store.load(code)
                if entry:
                    return entry
        base = {
            "tempo_liturgico": metadata.get("tempo_liturgico") or "",
            "settimana_del_tempo": metadata.get("settimana_del_tempo") or "",
            "giorno_settimana": metadata.get("giorno_settimana") or "",
        }
        year = metadata.get("anno_liturgico") or ""
        cycle = metadata.get("ciclo_biennale") or ""
        candidates = [
            {**base, "anno_liturgico": year, "ciclo_biennale": cycle},
            {**base, "anno_liturgico": "A/B/C", "ciclo_biennale": cycle},
            {**base, "anno_liturgico": "", "ciclo_biennale": cycle},
            {**base, "anno_liturgico": year, "ciclo_biennale": ""},
            {**base, "anno_liturgico": "A/B/C", "ciclo_biennale": ""},
            {**base, "anno_liturgico": "", "ciclo_biennale": ""},
        ]
        tried = set()
        for candidate in candidates:
            code = BiennaleStore.code(candidate)
            if not code or code in tried:
                continue
            tried.add(code)
            entry = self._biennale_store.load(code)
            if entry:
                return entry
        return None

    @staticmethod
    def _office_reading_sections(
        metadata: Dict[str, Any]
    ) -> List[HourSection]:
        """Letture dell'Ufficio delle Letture, con i responsori."""
        office = metadata.get("ufficio_delle_letture") or {}
        keys = ("prima_lettura", "responsorio_prima_lettura",
                "seconda_lettura", "responsorio_seconda_lettura")
        sections = [
            HourSection(key, office[key]) for key in keys if office.get(key)
        ]
        if sections:
            sections.insert(0, HourSection(
                "ufficio_letture", "", label="Dall'Ufficio delle Letture",
            ))
        return sections

    def _biennale_sections(self, entry: Dict[str, Any]) -> List[HourSection]:
        """Sezioni del Biennale nel layout delle ore."""
        header = " · ".join(part for part in (
            entry.get("data_estesa"),
            entry.get("settimana_del_tempo"),
            re.sub(r"^Tempo (di )?", "", entry.get("tempo_liturgico") or ""),
            entry.get("giorno_settimana"),
            f"Anno {entry['anno_liturgico']}" if entry.get("anno_liturgico") else None,
            f"Ciclo {entry['ciclo_biennale']}" if entry.get("ciclo_biennale") else None,
        ) if part)
        sections = [HourSection("biennale", header, label="Dal Biennale")]
        sections.extend(
            self._reading_sections(entry.get("letture") or [], "biennale")
        )
        return sections

    def _build_tabs(
        self,
        metadata: Dict[str, Any],
        documents: List[DocumentRecord],
    ) -> List[HourTab]:
        """Schede della vista giornaliera, guidate dal metadata.json.

        Le ore strutturate vengono rese per sezioni logiche; per le
        altre (Messa, Santo, Compieta, ore vigiliari) e come fallback
        quando il metadata non ha la forma strutturata si usa il TXT.
        """
        by_slug = {document.slug: document for document in documents}
        structured = {txt_slug: (meta_key, title)
                      for meta_key, txt_slug, title in STRUCTURED_HOURS}
        tabs: List[HourTab] = []
        for slug, _title in DOCUMENT_TITLES:
            if slug == "santo-del-giorno":
                santo = metadata.get("santo")
                if isinstance(santo, dict) and santo.get("nome"):
                    tabs.append(HourTab.from_santo(
                        slug, "Santo del Giorno", santo))
                    continue
            if slug in structured:
                meta_key, title = structured[slug]
                data = metadata.get(meta_key)
                if isinstance(data, dict) and data:
                    if meta_key == "ora_media":
                        tabs.append(HourTab.from_ora_media(slug, title, data))
                    else:
                        tabs.append(HourTab.from_sections(slug, title, data))
                    continue
            if slug in by_slug:
                tabs.append(HourTab.from_text(by_slug[slug]))
        return tabs

    def _read_metadata(self, iso: str) -> Dict[str, Any]:
        path = self._json_dir / f"{iso}.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Metadata non leggibile per %s: %s", iso, exc)
            return {}

    def _read_documents(self, day_dir: Path) -> List[DocumentRecord]:
        documents = []
        if not day_dir.is_dir():
            return documents
        for slug, title in DOCUMENT_TITLES:
            path = day_dir / f"{slug}.txt"
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                documents.append(DocumentRecord(slug, title, text))
        return documents

    # ------------------------------------------------------------------
    # Vista mensile
    # ------------------------------------------------------------------

    def month_grid(self, year: int, month: int) -> List[List[Optional[DayRecord]]]:
        """Griglia calendario del mese: settimane Lun-Dom.

        Ogni cella è un DayRecord (con `documents` vuoto ma con un
        attributo extra `collected`), oppure None per i giorni fuori mese.
        """
        first = date(year, month, 1)
        next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        cells: List[Optional[DayRecord]] = [None] * first.weekday()
        current = first
        while current < next_month:
            record = self.day(current.isoformat(), with_documents=False)
            if record is None:
                record = DayRecord(current, {}, [])
                record.collected = False
            else:
                record.collected = True
            cells.append(record)
            current += timedelta(days=1)
        while len(cells) % 7:
            cells.append(None)
        return [cells[i:i + 7] for i in range(0, len(cells), 7)]

