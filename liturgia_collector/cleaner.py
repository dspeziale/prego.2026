"""Estrazione e pulizia del testo liturgico dall'HTML CEI.

Strategia (selettori verificati sull'HTML reale, luglio 2026):

Messa del giorno
    contenitore  #cci_documenti_main_content
    sezioni      .cci-liturgia-giorno-dettagli-content
                 (h2 titolo, h3 sottotitolo, p versetto, div contenuto)

Liturgia delle Ore
    contenitore  article.seed-post  div.cci-liturgia-ore
    markup       lo_titolo, lo_sottotitolo, lo_versetto, lo_nota,
                 lo_rif, lo_normal (blocchi)
                 lo_antifona, lo_rosso (marcatori rossi inline: V. R. ant. †)

Tutto ciò che è navigazione, script, form, social, widget viene rimosso
alla radice: si estrae SOLO il contenitore del testo liturgico, quindi
header/footer/menu/cookie non entrano mai nell'output.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from .utils import normalize_text

logger = logging.getLogger(__name__)

Node = Union[Tag, NavigableString]


class ContentNotFoundError(Exception):
    """La pagina non contiene il contenitore del testo liturgico."""


class HtmlCleaner:
    """Trasforma l'HTML delle pagine CEI in testo puro e leggibile."""

    PARSER = "lxml"

    MASS_ROOT = "#cci_documenti_main_content"
    MASS_SECTION = ".cci-liturgia-giorno-dettagli-content"
    MASS_TITLE = ".cci-liturgia-giorno-section-title"
    MASS_SUBTITLE = ".cci-liturgia-giorno-section-subtitle"
    MASS_VERSE = ".cci-liturgia-giorno-section-versetto"
    MASS_CONTENT = ".cci-liturgia-giorno-section-content"
    MASS_CELEBRATION = "h3.cci_content_single_title"
    MASS_COLOR = ".cci-colore-liturgico span"

    HOURS_ROOT = "div.cci-liturgia-ore"
    HOURS_TITLE = "h1.cci_content_page_current_title"
    HOURS_DAY_LINE = ".cci-opere-giorni-liturgia"

    SAINT_ROOT = "#cci_documenti_main_content"
    SAINT_NAME = "h1.cci_content_single_title"
    SAINT_CAPTION = ".cci-santo-del-giorno-info .cci-santo-del-giorno-didascalia"
    SAINT_SOURCE = ".cci-santo-del-giorno-fonte-container"
    SAINT_OTHERS_TITLE = ".cci-santo-del-giorno-altri-santi"
    SAINT_PANEL = ".santo-del-giorno-accordion .panel"
    SAINT_PANEL_NAME = ".cci-santo-del-giorno-accordion-nome"
    SAINT_PANEL_BODY = ".panel-body"
    SAINT_IMAGE = ".santo-del-giorno-image img"

    # Immagini segnaposto del tema, da non considerare foto del santo.
    _PLACEHOLDER_IMAGE_MARKERS = ("logo_cci", "/themes/")

    DATE_LINE = ".cci-data-estesa-liturgia"

    # Tag eliminati integralmente ovunque.
    REMOVE_TAGS = (
        "script", "style", "noscript", "iframe", "svg", "img", "picture",
        "video", "audio", "canvas", "button", "form", "input", "select",
        "textarea", "label", "nav", "aside", "header", "footer",
        "template", "object", "embed", "figure",
    )

    # Elementi di servizio interni al contenuto (widget, ancore, target JS).
    REMOVE_SELECTORS = (
        ".cci-liturgia-giorno-font-increase",
        ".cci-multiple-liturgie",
        ".cci_breadcrumb",
        ".liturgia-navbar",
        ".cci-liturgia-ore-menu",
        ".cci-liturgia-ore-loader",
        ".verses",
        ".hide-if-no-js",
        ".screen-reader-text",
        ".visually-hidden",
        ".sharedaddy",
        ".social-share",
        ".share-container",
        ".cci_get_social_share",
        ".modal",
        ".widget",
    )

    # Marcatori rubricali rossi resi inline seguiti da uno spazio.
    INLINE_MARKER_CLASSES = frozenset(
        {"lo_antifona", "lo_rosso", "red-address-book",
         "cci-liturgia-giorno-testo-rosso"}
    )

    # Tag il cui contenuto scorre nel flusso del testo.
    INLINE_TAGS = frozenset(
        {"a", "span", "strong", "em", "b", "i", "u", "sup", "sub",
         "small", "cite", "abbr", "time", "q", "s"}
    )

    _RE_LECTIONARY_SUFFIX = re.compile(r"\s*\(ANNO\s+(PARI|DISPARI)\)\s*$", re.I)
    _RE_PSALTER = re.compile(r"\b([IVX]+)\s+SETTIMANA\s+DEL\s+SALTERIO\b", re.I)

    # Regole di suddivisione logica delle ore: (chiave, pattern, keep_full).
    # keep_full=True mantiene l'intera riga (il marcatore fa parte del
    # testo, es. '1 ant. ...'); False scarta il titolo e tiene il resto.
    # Il parser è monotono: una regola scatta solo se successiva alla
    # sezione corrente, così le righe 'V.' del responsorio non ricadono
    # nell'introduzione e l'antifona ripetuta resta nel cantico.
    LODI_SECTION_RULES = (
        ("introduzione", re.compile(r"^V\.\s"), True),
        # 'INNO' nei formulari del salterio, 'Inno' in quelli propri.
        ("inno", re.compile(r"^INNO\b|^Inno\b"), False),
        ("antifone_e_salmi", re.compile(r"^1\s?ant\.", re.I), True),
        ("lettura_breve", re.compile(r"^LETTURA BREVE\b"), False),
        ("responsorio", re.compile(r"^RESPONSORIO( BREVE)?\b"), False),
        # Il sito alterna 'Ant. al Ben.' e 'Ant al Ben.' (senza punto).
        ("antifona_al_benedictus",
         re.compile(r"^Ant\.?\s+al\s+Ben\.?", re.I), False),
        ("cantico_di_zaccaria", re.compile(r"^CANTICO DI ZACCARIA\b"), False),
        ("invocazioni", re.compile(r"^(INVOCAZIONI|INTERCESSIONI)\b"), False),
        ("orazione", re.compile(r"^ORAZIONE\b"), False),
    )

    UFFICIO_SECTION_RULES = (
        ("introduzione", re.compile(r"^V\.\s"), True),
        ("inno", re.compile(r"^INNO\b|^Inno\b"), False),
        ("antifone_e_salmi", re.compile(r"^1\s?ant\.", re.I), True),
        ("versetto", re.compile(r"^VERSETTO\b"), False),
        ("prima_lettura", re.compile(r"^PRIMA LETTURA\b"), False),
        ("responsorio_prima_lettura", re.compile(r"^RESPONSORIO\b"), False),
        ("seconda_lettura", re.compile(r"^SECONDA LETTURA\b"), False),
        ("responsorio_seconda_lettura", re.compile(r"^RESPONSORIO\b"), False),
        ("te_deum", re.compile(r"^(INNO\s+)?TE DEUM\b", re.I), False),
        ("orazione", re.compile(r"^ORAZIONE\b"), False),
    )

    # L'antifona può essere numerata ('1 ant.') o unica ('Ant.', nelle
    # feste); il lookahead esclude 'Ant. al Magn./Ben.'.
    _RE_ANTIPHON_START = re.compile(
        r"^(?:[1-3]\s?ant|Ant)\.?\s+(?!al\s)", re.I
    )

    VESPRI_SECTION_RULES = (
        ("introduzione", re.compile(r"^V\.\s"), True),
        ("inno", re.compile(r"^INNO\b|^Inno\b"), False),
        ("antifone_e_salmi", _RE_ANTIPHON_START, True),
        ("lettura_breve", re.compile(r"^LETTURA BREVE\b"), False),
        ("responsorio", re.compile(r"^RESPONSORIO( BREVE)?\b"), False),
        ("antifona_al_magnificat",
         re.compile(r"^Ant\.?\s+al\s+Magn\.?", re.I), False),
        ("cantico_della_beata_vergine",
         re.compile(r"^CANTICO DELLA BEATA VERGINE\b"), False),
        ("intercessioni", re.compile(r"^(INTERCESSIONI|INVOCAZIONI)\b"), False),
        ("orazione", re.compile(r"^ORAZIONE\b"), False),
    )

    ORA_MEDIA_SECTION_RULES = (
        ("introduzione", re.compile(r"^V\.\s"), True),
        ("inno", re.compile(r"^INNO\b|^Inno\b"), False),
        ("antifone_e_salmi", _RE_ANTIPHON_START, True),
        ("lettura_breve", re.compile(r"^LETTURA BREVE\b"), False),
        ("orazione", re.compile(r"^ORAZIONE\b"), False),
    )

    # La pagina domenicale della Compieta a volte incorpora contenuti
    # dei Vespri (Ant. al Magn., Magnificat, intercessioni): le regole
    # accettano entrambe le forme e la progressione monotona sceglie.
    COMPIETA_SECTION_RULES = (
        ("introduzione", re.compile(r"^V\.\s"), True),
        ("inno", re.compile(r"^INNO\b|^Inno\b"), False),
        ("antifone_e_salmi", _RE_ANTIPHON_START, True),
        ("lettura_breve", re.compile(r"^LETTURA BREVE\b"), False),
        ("responsorio", re.compile(r"^RESPONSORIO( BREVE)?\b"), False),
        # Scatta solo dopo il responsorio: altrimenti la ripetizione
        # dell'antifona (non numerata) del salmo la attiverebbe.
        ("antifona_al_cantico",
         re.compile(r"^Ant\.?\s+(al\s+Magn\.?\s*)?", re.I), False,
         "responsorio"),
        ("cantico_di_simeone", re.compile(r"^CANTICO DI SIMEONE\b"), False),
        ("cantico_della_beata_vergine",
         re.compile(r"^CANTICO DELLA BEATA VERGINE\b"), False),
        ("intercessioni", re.compile(r"^(INTERCESSIONI|INVOCAZIONI)\b"), False),
        ("orazione", re.compile(r"^ORAZIONE\b"), False),
        ("benedizione",
         re.compile(r"^Il Signore ci (conceda|benedica)\b"), True),
        # Richiede la benedizione già vista: gli incipit ('Ave', 'Salve')
        # ricorrono anche negli inni mariani a inizio ora.
        ("antifona_alla_beata_vergine",
         re.compile(r"^(Salve|Sotto la tua protezione|Ave|Regina"
                    r"|Alma|O santa Madre)"), True, "benedizione"),
    )

    # Messa del giorno: i titoli sono righe maiuscole esatte nel testo.
    MASS_SECTION_RULES = (
        ("antifona_d_ingresso", re.compile(r"^ANTIFONA$"), False),
        ("colletta", re.compile(r"^COLLETTA$"), False),
        ("prima_lettura", re.compile(r"^PRIMA LETTURA$"), False),
        ("salmo_responsoriale", re.compile(r"^SALMO RESPONSORIALE$"), False),
        ("seconda_lettura", re.compile(r"^SECONDA LETTURA$"), False),
        ("sequenza", re.compile(r"^SEQUENZA$"), False),
        ("acclamazione_al_vangelo",
         re.compile(r"^ACCLAMAZIONE AL VANGELO$"), False),
        ("vangelo", re.compile(r"^VANGELO$"), False),
        ("sulle_offerte", re.compile(r"^SULLE OFFERTE$"), False),
        ("antifona_alla_comunione",
         re.compile(r"^ANTIFONA ALLA COMUNIONE$"), False),
        ("dopo_la_comunione", re.compile(r"^DOPO LA COMUNIONE$"), False),
    )

    # Sezioni con titoli esatti e non ambigui: le transizioni possono
    # avvenire in qualsiasi ordine (assorbe i titoli fuori posto del
    # sito, es. Antifona alla comunione duplicata prima del Vangelo).
    NON_MONOTONIC_SLUGS = frozenset({"liturgia-del-giorno"})

    HOUR_SECTION_RULES = {
        "liturgia-del-giorno": MASS_SECTION_RULES,
        "lodi-mattutine": LODI_SECTION_RULES,
        "ufficio-delle-letture": UFFICIO_SECTION_RULES,
        "vespri": VESPRI_SECTION_RULES,
        "compieta": COMPIETA_SECTION_RULES,
        "compieta-dopo-i-primi-vespri": COMPIETA_SECTION_RULES,
        "compieta-dopo-i-secondi-vespri": COMPIETA_SECTION_RULES,
    }

    ORA_MEDIA_SLUG = "ora-media"
    _RE_ORA_MEDIA_HOUR = re.compile(r"^Ora\s+(terza|sesta|nona)\b", re.I)

    # ------------------------------------------------------------------
    # API pubblica
    # ------------------------------------------------------------------

    def clean_daily_mass(self, html: str) -> str:
        """Testo pulito della Messa del giorno."""
        root = self._liturgical_root(html, self.MASS_ROOT)
        parts = []
        date_line = self._text_of(root, self.DATE_LINE)
        if date_line:
            parts.append(date_line)
        celebration = self._text_of(root, self.MASS_CELEBRATION)
        if celebration:
            parts.append(celebration)
        sections = [
            text
            for section in root.select(self.MASS_SECTION)
            if (text := self._render_mass_section(section))
        ]
        if not sections:
            raise ContentNotFoundError("nessuna sezione liturgica trovata")
        return self._join_sections(parts + sections)

    def clean_hour(self, html: str) -> str:
        """Testo pulito di un'ora della Liturgia delle Ore."""
        soup = self._soup(html)
        root = soup.select_one(self.HOURS_ROOT)
        if root is None:
            raise ContentNotFoundError(
                f"contenitore {self.HOURS_ROOT!r} assente nella pagina"
            )
        parts = []
        for selector in (self.DATE_LINE, self.HOURS_TITLE, self.HOURS_DAY_LINE):
            value = self._text_of(soup, selector)
            if value:
                parts.append(value)
        body = normalize_text(self._render(root))
        if not body:
            raise ContentNotFoundError("testo dell'ora liturgica vuoto")
        parts.append(body)
        return self._join_sections(parts)

    def clean_saint_of_the_day(self, html: str) -> str:
        """Testo pulito del Santo del giorno (Martirologio + altri santi)."""
        soup = self._soup(html)
        root = soup.select_one(self.SAINT_ROOT)
        name = self._text_of(soup, self.SAINT_NAME)
        if root is None or not name:
            raise ContentNotFoundError("santo del giorno assente nella pagina")
        parts = [self._text_of(root, self.DATE_LINE)]
        main_entry = [name.upper()]
        caption = self._text_of(soup, self.SAINT_CAPTION)
        if caption:
            main_entry.append(caption)
        source = soup.select_one(self.SAINT_SOURCE)
        if source is not None:
            main_entry.append(normalize_text(self._render(source)))
        parts.append("\n".join(main_entry))
        others = self._render_other_saints(soup)
        if others:
            parts.append(self._text_of(soup, self.SAINT_OTHERS_TITLE).upper()
                         or "ALTRI SANTI")
            parts.extend(others)
        return self._join_sections(parts)

    def extract_saint_name(self, html: str) -> Optional[str]:
        """Nome del santo principale del giorno."""
        return self._text_of(self._soup(html), self.SAINT_NAME) or None

    def extract_saint_sections(self, html: str) -> Optional[Dict[str, Any]]:
        """Santo del giorno in forma strutturata per metadata.json.

        Restituisce {'nome', 'martirologio', 'altri_santi': [{'nome',
        'martirologio'}, ...]} oppure None se la pagina non ha contenuto.
        """
        soup = self._soup(html)
        name = self._text_of(soup, self.SAINT_NAME)
        if not name:
            return None
        source = soup.select_one(self.SAINT_SOURCE)
        martyrology = (
            normalize_text(self._render(source)) if source is not None else None
        )
        others = []
        for panel in soup.select(self.SAINT_PANEL):
            panel_name = self._text_of(panel, self.SAINT_PANEL_NAME)
            body = panel.select_one(self.SAINT_PANEL_BODY)
            text = normalize_text(self._render(body)) if body is not None else ""
            if panel_name:
                others.append({"nome": panel_name, "martirologio": text})
        return {
            "nome": name,
            "martirologio": martyrology,
            "altri_santi": others,
        }

    def extract_saint_image(self, html: str) -> Optional[str]:
        """URL dell'immagine del santo principale, se presente.

        Lavora sul DOM grezzo: la pipeline di pulizia elimina i tag <img>.
        """
        soup = BeautifulSoup(html, self.PARSER)
        image = soup.select_one(self.SAINT_IMAGE)
        src = (image.get("src") or "").strip() if image is not None else ""
        if not src:
            return None
        if any(marker in src for marker in self._PLACEHOLDER_IMAGE_MARKERS):
            return None
        return src

    def _render_other_saints(self, soup: BeautifulSoup) -> List[str]:
        """Voci 'Altri Santi': nome e testo del martirologio."""
        entries = []
        for panel in soup.select(self.SAINT_PANEL):
            name = self._text_of(panel, self.SAINT_PANEL_NAME)
            body = panel.select_one(self.SAINT_PANEL_BODY)
            text = normalize_text(self._render(body)) if body is not None else ""
            if name:
                entries.append(f"{name.upper()}\n{text}".strip())
        return entries

    _RE_PSALMODY_MARKER = re.compile(r"^([1-3])\s?ant\.", re.I)

    def split_hour_sections(self, text: str, hour_slug: str) -> Dict[str, Any]:
        """Suddivide il testo pulito di un'ora nelle sue sezioni logiche.

        Restituisce un dizionario chiave -> testo (es. 'inno',
        'lettura_breve', ...); 'antifone_e_salmi' è una lista di gruppi
        antifona + salmo/cantico (di norma tre). Per l'Ora media il
        risultato è annidato nei tre blocchi 'terza', 'sesta' e 'nona'.
        Le righe che precedono la prima sezione riconosciuta
        (intestazioni di pagina) vengono scartate. Vuoto se l'ora non ha
        regole di suddivisione.
        """
        if hour_slug == self.ORA_MEDIA_SLUG:
            return {
                name: self._split_sections(block, self.ORA_MEDIA_SECTION_RULES)
                for name, block in self._split_ora_media(text).items()
            }
        rules = self.HOUR_SECTION_RULES.get(hour_slug)
        if not rules:
            return {}
        monotonic = hour_slug not in self.NON_MONOTONIC_SLUGS
        return self._split_sections(text, rules, monotonic)

    def _split_sections(
        self,
        text: str,
        rules: Tuple[Tuple[Any, ...], ...],
        monotonic: bool = True,
    ) -> Dict[str, Union[str, List[str]]]:
        """Macchina a stati: righe -> sezioni ordinate."""
        sections: Dict[str, List[str]] = {}
        current_key: Optional[str] = None
        current_index = -1
        for line in text.splitlines():
            stripped = line.strip()
            transition = self._match_section(
                stripped, rules, current_index, sections, monotonic
            )
            if transition is not None:
                index, key, content = transition
                if not monotonic and index == 0 and sections.get(key):
                    # La prima sezione che si ripete segna l'inizio di un
                    # secondo formulario (memorie facoltative): ci si
                    # ferma al primo, quello principale del giorno.
                    break
                current_index, current_key = index, key
                sections.setdefault(current_key, [])
                if content:
                    sections[current_key].append(content)
            elif current_key is not None:
                sections[current_key].append(stripped)
        result: Dict[str, Union[str, List[str]]] = {}
        for key, lines in sections.items():
            joined = normalize_text("\n".join(lines))
            if not joined:
                continue
            if key == "antifone_e_salmi":
                result[key] = self._split_psalmody(joined)
            else:
                result[key] = joined
        return result

    def _split_ora_media(self, text: str) -> Dict[str, str]:
        """Separa l'Ora media nei blocchi Terza, Sesta e Nona.

        I blocchi sono delimitati dalle righe 'Ora terza' / 'Ora sesta' /
        'Ora nona'; ciò che precede il primo delimitatore è intestazione
        di pagina e viene scartato.
        """
        blocks: Dict[str, List[str]] = {}
        current: Optional[str] = None
        for line in text.splitlines():
            match = self._RE_ORA_MEDIA_HOUR.match(line.strip())
            if match:
                current = match.group(1).lower()
                blocks[current] = []
            elif current is not None:
                blocks[current].append(line)
        return {name: "\n".join(lines) for name, lines in blocks.items()}

    _RE_PSALM_TITLE = re.compile(r"^(SALMO|CANTICO)\b")

    # Fine antifona: riga che termina con . ? ! (ignorando eventuali
    # marcatori salmodici † * e virgolette di chiusura).
    _RE_ANTIPHON_END = re.compile(r"[.?!][»\"']?\s*[†*]?\s*$")
    # Fine sottotitolo: riga che termina con ').' (citazione biblica).
    _RE_SUBTITLE_END = re.compile(r"\)\s*\.\s*$")
    # Righe massime entro cui cercare la fine del sottotitolo.
    _SUBTITLE_SEARCH_LIMIT = 10

    def _split_psalmody(self, text: str) -> List[Dict[str, Optional[str]]]:
        """Divide la salmodia nei suoi gruppi antifona + salmo/cantico.

        Con antifone numerate un nuovo gruppo inizia quando cambia il
        NUMERO (l'antifona ripetuta a fine salmo resta nel suo gruppo).
        Con antifona unica (feste) si divide sui titoli SALMO/CANTICO.
        Ogni gruppo è poi strutturato in antifona/sottotitolo/salmo.
        """
        groups = self._split_by_antiphon_number(text)
        if len(groups) <= 1:
            groups = self._split_by_psalm_title(text)
        return [self._structure_psalmody_group(group) for group in groups]

    def _structure_psalmody_group(self, text: str) -> Dict[str, Optional[str]]:
        """Struttura un gruppo di salmodia in antifona/sottotitolo/salmo.

        L'antifona termina alla prima riga che finisce con . ? !
        (o comunque prima del titolo SALMO/CANTICO); da lì il
        sottotitolo prosegue fino alla riga che termina con ').'
        (citazione biblica inclusa); il resto è il salmo vero e proprio.
        """
        lines = text.splitlines()
        antiphon: List[str] = []
        index = 0
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped and self._RE_PSALM_TITLE.match(stripped) and antiphon:
                break  # titolo raggiunto: l'antifona finisce prima
            antiphon.append(line)
            if stripped and self._RE_ANTIPHON_END.search(stripped):
                index += 1
                break
        remaining = lines[index:]
        subtitle: List[str] = []
        body = remaining
        searched = 0
        for position, line in enumerate(remaining):
            if line.strip():
                searched += 1
            if self._RE_SUBTITLE_END.search(line.strip()):
                subtitle = remaining[:position + 1]
                body = remaining[position + 1:]
                break
            if searched >= self._SUBTITLE_SEARCH_LIMIT:
                break  # nessuna citazione entro il limite
        if not subtitle:
            # Senza citazione, il titolo SALMO/CANTICO fa da sottotitolo.
            for position, line in enumerate(remaining):
                if self._RE_PSALM_TITLE.match(line.strip()):
                    subtitle = remaining[:position + 1]
                    body = remaining[position + 1:]
                elif line.strip():
                    break
        return {
            "antifona": normalize_text("\n".join(antiphon)) or None,
            "sottotitolo": self._flatten_subtitle("\n".join(subtitle)),
            "salmo": normalize_text("\n".join(body)) or None,
        }

    @staticmethod
    def _flatten_subtitle(text: str) -> Optional[str]:
        """Compatta il sottotitolo: dopo il primo a capo, una sola riga.

        Il titolo (SALMO/CANTICO) resta sulla prima riga; la citazione
        che segue viene riportata su un'unica riga.
        """
        normalized = normalize_text(text)
        if not normalized:
            return None
        lines = [line for line in normalized.split("\n") if line.strip()]
        if len(lines) <= 1:
            return lines[0] if lines else None
        return lines[0] + "\n" + " ".join(lines[1:])

    def _split_by_antiphon_number(self, text: str) -> List[str]:
        """Gruppi delimitati dal cambio di numero dell'antifona.

        In un gruppo il marcatore compare al più due volte (apertura e
        ripetizione a fine salmo): un terzo marcatore apre un nuovo
        gruppo anche a numero invariato, per assorbire i refusi di
        numerazione del sito.
        """
        groups: List[List[str]] = []
        current_number: Optional[str] = None
        markers_in_group = 0
        for line in text.splitlines():
            match = self._RE_PSALMODY_MARKER.match(line)
            if match:
                if match.group(1) != current_number or markers_in_group >= 2:
                    current_number = match.group(1)
                    groups.append([])
                    markers_in_group = 0
                markers_in_group += 1
            if groups:
                groups[-1].append(line)
        return [normalize_text("\n".join(group)) for group in groups]

    def _split_by_psalm_title(self, text: str) -> List[str]:
        """Gruppi delimitati dai titoli SALMO/CANTICO (antifona unica)."""
        groups: List[List[str]] = [[]]
        seen_title = False
        for line in text.splitlines():
            if self._RE_PSALM_TITLE.match(line):
                if seen_title:
                    groups.append([])
                seen_title = True
            groups[-1].append(line)
        return [
            normalized
            for group in groups
            if (normalized := normalize_text("\n".join(group)))
        ]

    @staticmethod
    def _match_section(
        line: str,
        rules: Tuple[Tuple[Any, ...], ...],
        current_index: int,
        sections: Dict[str, List[str]],
        monotonic: bool = True,
    ) -> Optional[Tuple[int, str, str]]:
        """Prima regola ammissibile che combacia con la riga.

        Con `monotonic` la regola deve essere successiva alla sezione
        corrente. Una regola può avere un quarto elemento opzionale: la
        chiave di una sezione che deve già essere stata riconosciuta
        perché la regola possa scattare. Restituisce (indice, chiave,
        contenuto della riga) oppure None.
        """
        for index, rule in enumerate(rules):
            key, pattern, keep_full = rule[0], rule[1], rule[2]
            required = rule[3] if len(rule) > 3 else None
            if monotonic and index <= current_index:
                continue
            if not monotonic and index == current_index:
                continue
            if required is not None and required not in sections:
                continue
            match = pattern.match(line)
            if match:
                content = line if keep_full else line[match.end():].strip()
                return index, key, content
        return None

    def extract_day_header(self, html: str) -> Dict[str, Optional[str]]:
        """Metadati dalla pagina della Messa: celebrazione e colore."""
        soup = self._soup(html)
        celebration = self._text_of(soup, self.MASS_CELEBRATION)
        if celebration:
            celebration = self._RE_LECTIONARY_SUFFIX.sub("", celebration)
        color = self._text_of(soup, self.MASS_COLOR)
        return {
            "celebration": celebration or None,
            "color": color.capitalize() if color else None,
        }

    def extract_psalter_week(self, html: str) -> Optional[str]:
        """Settimana del salterio (es. 'II') dalla pagina delle Ore."""
        soup = self._soup(html)
        day_line = self._text_of(soup, self.HOURS_DAY_LINE)
        if day_line:
            match = self._RE_PSALTER.search(day_line)
            if match:
                return match.group(1).upper()
        return None

    # ------------------------------------------------------------------
    # Preparazione del DOM
    # ------------------------------------------------------------------

    def _soup(self, html: str) -> BeautifulSoup:
        """Parsa l'HTML ed elimina tag di servizio, commenti e link."""
        soup = BeautifulSoup(html, self.PARSER)
        for tag_name in self.REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        for selector in self.REMOVE_SELECTORS:
            for tag in soup.select(selector):
                tag.decompose()
        for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
            comment.extract()
        # I link diventano testo semplice: le citazioni bibliche
        # (es. 'Os 10,1-3' su BibbiaEdu) vengono così preservate.
        for anchor in soup.find_all("a"):
            anchor.unwrap()
        return soup

    def _liturgical_root(self, html: str, selector: str) -> Tag:
        """Contenitore radice del testo liturgico, o eccezione."""
        root = self._soup(html).select_one(selector)
        if root is None:
            raise ContentNotFoundError(
                f"contenitore {selector!r} assente nella pagina"
            )
        return root

    # ------------------------------------------------------------------
    # Rendering testo
    # ------------------------------------------------------------------

    def _render_mass_section(self, section: Tag) -> str:
        """Sezione della Messa: TITOLO, sottotitolo, versetto, contenuto."""
        lines = []
        title = self._text_of(section, self.MASS_TITLE)
        if title:
            lines.append(title.upper())
        for selector in (self.MASS_SUBTITLE, self.MASS_VERSE):
            value = self._text_of(section, selector)
            if value:
                lines.append(value)
        content = section.select_one(self.MASS_CONTENT)
        if content is not None:
            body = normalize_text(self._render(content))
            if body:
                lines.append(body)
        return "\n".join(lines).strip()

    def _render(self, node: Node) -> str:
        """Converte ricorsivamente un nodo DOM in testo.

        - <br> diventa a capo
        - i marcatori rubricali rossi restano inline ('R. ', '1 ant. ')
        - i tag inline scorrono nel testo
        - ogni altro elemento è un blocco separato da riga vuota
        """
        if isinstance(node, Comment):
            return ""
        if isinstance(node, NavigableString):
            # I newline del sorgente HTML sono solo whitespace:
            # gli a capo reali derivano da <br> e dai blocchi.
            return re.sub(r"[\r\n]+", " ", str(node))
        if node.name == "br":
            return "\n"
        inner = "".join(self._render(child) for child in node.children)
        classes = frozenset(node.get("class") or ())
        if classes & self.INLINE_MARKER_CLASSES:
            # Un <br> in testa al marcatore (es. 'R.') indica un a capo reale.
            prefix = "\n" if inner.startswith("\n") else ""
            marker = " ".join(inner.split())
            return f"{prefix}{marker} " if marker else ""
        if node.name in self.INLINE_TAGS:
            return inner
        return f"\n\n{inner.strip()}\n\n"

    def _text_of(self, scope: Union[BeautifulSoup, Tag], selector: str) -> str:
        """Testo normalizzato (una riga) del primo elemento selezionato."""
        element = scope.select_one(selector)
        if element is None:
            return ""
        return " ".join(self._render(element).split())

    @staticmethod
    def _join_sections(parts: List[str]) -> str:
        """Unisce le sezioni separandole con UNA sola riga vuota."""
        joined = "\n\n".join(part.strip() for part in parts if part.strip())
        return normalize_text(joined) + "\n"
