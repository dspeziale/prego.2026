# LiturgiaCollector

Applicazione Python object-oriented che scarica quotidianamente i testi
liturgici dal sito della **Conferenza Episcopale Italiana**
(chiesacattolica.it) e li salva in **TXT estremamente puliti**, pronti per
una pipeline AI (embedding, indicizzazione vettoriale, RAG).

Nessun browser automation: le pagine CEI sono renderizzate lato server,
quindi bastano `requests` + `beautifulsoup4` + `lxml`.

## Cosa raccoglie

Per ogni data (default: oggi):

| Documento | File |
|---|---|
| Messa del giorno | `liturgia-del-giorno.txt` |
| Santo del giorno (Martirologio + altri santi) | `santo-del-giorno.txt` |
| Ufficio delle letture | `ufficio-delle-letture.txt` |
| Lodi mattutine | `lodi-mattutine.txt` |
| Ora media | `ora-media.txt` |
| Vespri | `vespri.txt` |
| Compieta | `compieta.txt` |
| **Solo sabato**: Primi vespri, Compieta dopo i primi vespri | `primi-vespri.txt`, `compieta-primi-vespri.txt` |
| **Solo domenica**: Secondi vespri, Compieta dopo i secondi vespri | `secondi-vespri.txt`, `compieta-secondi-vespri.txt` |
| Metadati liturgici | `json/<data>.json` |

Struttura di output: i TXT in una cartella per data, i metadati JSON
tutti insieme nella cartella `json/` alla radice del progetto
(configurabile con `json_output`):

```
data/output/
    2026-07-08/
        liturgia-del-giorno.txt
        santo-del-giorno.txt
        ufficio-delle-letture.txt
        lodi-mattutine.txt
        ora-media.txt
        vespri.txt
        compieta.txt
data/json/
    2026-07-08.json
    2026-07-09.json
```

`metadata.json` combina il calcolo algoritmico del calendario liturgico
(anno A/B/C, ciclo feriale I/II, tempo, settimana — verificabile su
gcatholic.org) con i dati autorevoli estratti dalla pagina CEI
(celebrazione, grado, colore, settimana del salterio):

```json
{
    "data": "2026-07-08",
    "giorno_settimana": "Mercoledì",
    "anno_liturgico": "A",
    "ciclo_biennale": "II",
    "tempo_liturgico": "Tempo Ordinario",
    "settimana_del_tempo": "XIV",
    "celebrazione": "MERCOLEDÌ DELLA XIV SETTIMANA DEL TEMPO ORDINARIO",
    "grado": "Feria",
    "colore": "Verde",
    "settimana_del_salterio": "II",
    "santo_del_giorno": "Santi Aquila e Prisca o Priscilla, coniugi",
    "immagine_santo": "https://www.chiesacattolica.it/wp-content/uploads/sites/31/2023/06/5e70e45c-....jpeg"
}
```

`immagine_santo` è `null` quando il sito non pubblica una foto per il
santo del giorno (le immagini segnaposto del tema vengono ignorate).
Il campo `santo` contiene la forma strutturata:

```json
"santo": {
    "nome": "Santi Aquila e Prisca o Priscilla, coniugi",
    "martirologio": "Commemorazione dei santi Aquila e Prisca ...",
    "altri_santi": [
        { "nome": "Santa Gliceria, martire", "martirologio": "..." }
    ]
}
```

`settimana_del_tempo` è in numeri romani ("XIV"); "0" indica i giorni
tra le Ceneri e la I domenica di Quaresima, `null` i tempi senza
numerazione (Natale, Triduo).

`metadata.json` contiene inoltre la Messa del giorno, l'Ufficio delle
letture, le Lodi mattutine, l'Ora media, i Vespri e la Compieta (incluse
le compiete vigiliari) suddivisi nelle loro sezioni logiche:

```json
"liturgia_del_giorno": {
    "antifona_d_ingresso": "...", "colletta": "...",
    "prima_lettura": "...", "salmo_responsoriale": "...",
    "seconda_lettura": "... (domeniche e solennità)",
    "acclamazione_al_vangelo": "...", "vangelo": "...",
    "sulle_offerte": "...", "antifona_alla_comunione": "...",
    "dopo_la_comunione": "..."
},
"compieta": {
    "introduzione": "...", "inno": "...",
    "antifone_e_salmi": ["..."],
    "lettura_breve": "...", "responsorio": "...",
    "antifona_al_cantico": "...",
    "cantico_di_simeone": "...",
    "orazione": "...", "benedizione": "...",
    "antifona_alla_beata_vergine": "..."
}
```

Il sabato la pagina CEI della Compieta contiene solo l'invitatorio e la
domenica una forma ibrida con elementi dei Vespri (Magnificat,
intercessioni): il parser riflette fedelmente ciò che il sito pubblica.

```json
"lodi_mattutine": {
    "introduzione": "V. O Dio, vieni a salvarmi ...",
    "inno": "...",
    "antifone_e_salmi": ["1 ant. ... SALMO ...", "2 ant. ... CANTICO ...", "3 ant. ... SALMO ..."],
    "lettura_breve": "Rm 8, 35. 37 ...",
    "responsorio": "R. ...",
    "antifona_al_benedictus": "...",
    "cantico_di_zaccaria": "Lc 1, 68-79 ...",
    "invocazioni": "...",
    "orazione": "..."
},
"ufficio_delle_letture": {
    "introduzione": "...", "inno": "...",
    "antifone_e_salmi": ["1 ant. ...", "2 ant. ...", "3 ant. ..."],
    "prima_lettura": "...", "responsorio_prima_lettura": "...",
    "seconda_lettura": "...", "responsorio_seconda_lettura": "...",
    "te_deum": "... (domeniche, feste e solennità)",
    "orazione": "..."
},
"ora_media": {
    "terza": { "introduzione": "...", "inno": "...",
               "antifone_e_salmi": ["...", "...", "..."],
               "lettura_breve": "...", "orazione": "..." },
    "sesta": { "...": "..." },
    "nona":  { "...": "..." }
},
"vespri": {
    "introduzione": "...", "inno": "...",
    "antifone_e_salmi": ["1 ant. ...", "2 ant. ...", "3 ant. ..."],
    "lettura_breve": "...", "responsorio": "...",
    "antifona_al_magnificat": "...",
    "cantico_della_beata_vergine": "...",
    "intercessioni": "...", "orazione": "..."
}
```

Il sabato (e nelle vigilie delle solennità) la pagina CEI dei Vespri
contiene solo l'invitatorio: in quei giorni `vespri` ha la sola
salmodia dell'invitatorio, mentre i vespri veri sono nei primi vespri.

Il parser delle sezioni (`HtmlCleaner.split_hour_sections`) è una
macchina a stati a progressione monotona sui titoli del testo pulito:
gestisce le varianti tipografiche del sito ('INNO'/'Inno',
'Ant. al Ben.'/'Ant al Ben.', 'INNO Te Deum') e disambigua i due
RESPONSORIO dell'Ufficio in base alla lettura corrente.
`antifone_e_salmi` è sempre una lista di tre gruppi (antifona +
salmo/cantico): un nuovo gruppo inizia quando cambia il numero
dell'antifona, così la ripetizione dell'antifona a fine salmo resta
nel proprio gruppo.

## Uso

```bash
pip install -r requirements.txt

python main.py                              # liturgia di oggi
python main.py 2026-07-08                   # data specifica
python main.py 2026-07-11 2026-07-12        # più date singole
python main.py 2026-07-01..2026-07-31       # intervallo inclusivo
python main.py 2026-07-08 2026-08-01..2026-08-05   # misto
```

Configurazione in `config.json`:

```json
{
    "output": "output",
    "json_output": "json",
    "timeout": 20,
    "retry": 3,
    "user_agent": "Mozilla/5.0 ..."
}
```

## Architettura

```
main.py                      entry point CLI del collector
config.json                  configurazione (percorsi, timeout, API key)
users.json                   utenti abilitati alle modifiche (hash)
vercel.json / api/index.py   deploy su Vercel
liturgia_collector/          package del collector (ETL)
    config.py  models.py  utils.py  calendar.py
    scraper.py  cleaner.py  writer.py  collector.py
webapp/                      interfaccia web Flask
    app.py                   application factory e wiring
    views_core.py            oggi, giorno, mese, about, omelia
    views_auth.py            login/logout
    views_proprio.py         gestione Proprio
    views_biennale.py        gestione Biennale
    views_raccolta.py        raccolta via web
    repository.py            lettura dati per le viste
    proprio.py  biennale.py  runner.py  users.py  youtube.py
    templates/               pagine Jinja (AdminLTE)
static/                      icona, css/prego.css, js/prego.js
data/                        dati (non toccare a mano)
    output/                  TXT per giornata (escluso dal deploy)
    json/                    metadati per giornata (YYYY-MM-DD.json)
    proprio/                 Proprio dei santi (GG-MM.json)
    biennale/                lezionario biennale (slug.json)
tests/run_tests.py           smoke test eseguibili
```

> **Nota sul packaging**: i moduli vivono nel package `liturgia_collector/`
> e non nella root del progetto perché un `calendar.py` a livello root
> oscurerebbe il modulo standard `calendar` (usato internamente da
> `requests` via `email.utils`), rompendo l'applicazione.

### Selettori (verificati sull'HTML reale, luglio 2026)

* **Messa**: contenitore `#cci_documenti_main_content`, sezioni
  `.cci-liturgia-giorno-dettagli-content` (titolo `h2`, sottotitolo `h3`,
  versetto, contenuto). Celebrazione in `h3.cci_content_single_title`,
  colore in `.cci-colore-liturgico span`.
* **Liturgia delle Ore**: contenitore `div.cci-liturgia-ore` con markup
  semantico `lo_titolo`, `lo_versetto`, `lo_antifona` (V. / R. / ant.),
  `lo_rosso` († / —), `lo_rif`, `lo_sottotitolo`, `lo_nota`, `lo_normal`.
* **Santo del giorno**: nome in `h1.cci_content_single_title`, testo del
  Martirologio in `.cci-santo-del-giorno-fonte-container`, altri santi
  nei pannelli `.santo-del-giorno-accordion .panel` (nome + `.panel-body`).

La strategia di pulizia è *estrattiva*: si preleva SOLO il contenitore del
testo liturgico, quindi header, footer, menu, cookie banner, ricerche e
navigazione non entrano mai nell'output. All'interno del contenitore si
eliminano script, style, iframe, svg, form, widget, link (mantenendo il
testo delle citazioni bibliche), condivisioni social; si normalizzano
entità HTML, spazi multipli e righe vuote. Le rubriche, i marcatori rossi
(V., R., ant.), gli asterischi e le croci salmodiche, le citazioni
bibliche e i titoli sono preservati. Le sezioni sono separate da UNA sola
riga vuota.

## Interfaccia web (LiturgiaViewer)

Dashboard AdminLTE per consultare i dati raccolti:

```bash
python webapp/app.py        # http://localhost:5300
```

* **Dashboard** — statistiche dell'archivio (giornate, documenti, mesi)
  e ultime giornate raccolte.
* **Vista mensile** — calendario navigabile con celebrazione e colore
  liturgico di ogni giorno; i giorni non ancora raccolti sono in grigio.
* **Vista giornaliera** — metadati, santo del giorno con immagine e i
  testi in schede. Messa del giorno, Ufficio delle letture, Lodi, Ora
  media, Vespri e Compieta (incluse le vigiliari) sono resi dal
  `metadata.json` per sezioni logiche (antifone, letture, responsori,
  salmodia nei tre gruppi, cantici evangelici, orazioni), con l'Ora
  media suddivisa in Terza/Sesta/Nona; il Santo del giorno è reso dal
  campo `santo` (nome, immagine, martirologio, altri santi), con
  fallback automatico al TXT ovunque il metadata non sia strutturato.
  Il tema usa il rosso liturgico come colore d'accento.

L'app (`webapp/app.py` + `webapp/repository.py`) legge direttamente la
cartella `output/` indicata in `config.json`: non serve alcun database e
le nuove raccolte compaiono al semplice refresh. AdminLTE, Bootstrap e
Font Awesome sono caricati da CDN.

## Proprio biennale (inserimento manuale)

Dall'interfaccia web (sidebar → **Proprio biennale**) si caricano le
letture proprie dei santi del ciclo biennale: data (giorno e mese),
nome del santo, tipo (Solennità/Festa/Memoria/...), fino a quattro
letture — ciascuna con riferimento, sottotitolo, fonte ("Dal ..."),
testo completo e responsorio — e l'orazione. Ogni ricorrenza è salvata
in `data/proprio/<giorno>-<mese>.json` (es. `data/proprio/21-01.json`):

```json
{
    "data": "21-01",
    "data_estesa": "21 Gennaio",
    "santo": "Sant'Agnese, vergine e martire",
    "tipo": "Memoria",
    "letture": [
        { "titolo": "Prima Lettura", "riferimento": "Cfr. 2 Cor 10, 17-18",
          "sottotitolo": "...", "fonte": "Dal «Trattato sulle vergini» ...",
          "testo": "...", "responsorio": "R. ..." }
    ],
    "orazione": "..."
}
```

L'elenco consente modifica (form precompilata) ed eliminazione.

## Deploy su Vercel

Il viewer è pronto per Vercel: `api/index.py` espone l'app Flask,
`vercel.json` instrada tutte le richieste e `.vercelignore` esclude la
cartella `data/output/` dal deploy (l'app funziona dai soli `json/`, più
`proprio/` e `biennale/`). Deploy:

```bash
npm i -g vercel
vercel          # dalla cartella LiturgiaCollector
```

Su Vercel il filesystem è in sola lettura: la voce Raccolta è nascosta
e i salvataggi di Proprio/Biennale sono bloccati con un avviso (la
modalità si attiva da sola con la variabile d'ambiente `VERCEL`; in
locale si può simulare con `LC_READ_ONLY=1`). Per aggiornare i dati
pubblicati: raccogliere in locale e rifare il deploy.

## Robustezza

* Retry automatico con backoff progressivo (`retry`,
  `retry_backoff_seconds`), timeout e User-Agent configurabili.
* Il fallimento di un singolo documento non blocca gli altri; il
  fallimento di una data non blocca le successive.
* Le ore vigiliari assenti in giorni particolari producono un WARNING,
  non un errore.
* Logging dettagliato INFO / WARNING / ERROR.

## Estensioni future

Il design è già predisposto per:

* **PDF / EPUB / Markdown** — nuova sottoclasse di `BaseWriter`.
* **SQLite / PostgreSQL / Elasticsearch** — writer verso database che
  serializzano `LiturgicalDocument` + `DateInfo.to_dict()`.
* **Embedding / RAG / LLM / traduzioni** — i TXT sono già chunk-friendly
  (sezioni separate da riga vuota) e `metadata.json` fornisce i metadati
  di filtro (tempo, anno, celebrazione).
* **Scheduler cron** — `main.py` è idempotente: `python main.py` in un
  cron job quotidiano è sufficiente.
* **OCR / altre fonti** — nuove implementazioni di scraper accanto a
  `LiturgicalScraper`, stesso contratto (`fetch_* -> html`).
# prego
