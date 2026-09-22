# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Cos'è

**Prego** raccoglie i testi liturgici quotidiani dal sito della Conferenza
Episcopale Italiana (chiesacattolica.it) e li serve attraverso una webapp
Flask e un'app Android offline. Due componenti distinti con un contratto
di dati in mezzo, non un'unica applicazione:

1. **Collector** (`main.py` + `liturgia_collector/`) — ETL da riga di
   comando: scarica, pulisce e scrive i dati in `data/`.
2. **Webapp** (`webapp/`) — interfaccia Flask che legge `data/` in sola
   lettura. Nessun database: la sorgente di verità sono i file JSON/TXT.
3. **App Android** (`android/`) — WebView Kotlin che sincronizza le pagine
   già composte dalla webapp su `prego.vercel.app` e le serve offline.

## Comandi

```bash
# Dipendenze
pip install -r requirements.txt

# Raccolta (idempotente): oggi, una data, un intervallo inclusivo, misto
python main.py
python main.py 2026-07-08
python main.py 2026-07-01..2026-07-31
python main.py 2026-07-08 2026-08-01..2026-08-05

# Webapp locale -> http://localhost:5300
python webapp/app.py

# Test (smoke test senza framework, senza rete): tutti i controlli
python tests/run_tests.py

# Gestione utenti abilitati alle modifiche
python webapp/users.py list
python webapp/users.py add <utente> <password>
python webapp/users.py remove <utente>

# Conversione dei testi grezzi del Biennale (data/biennale/raw/) in JSON
# -> data/biennale/raw/json/{biennale,proprio,da_assegnare,duplicati}
#    + REPORT.md con avvisi e giornate mancanti
python scripts/biennale_raw_to_json.py --pulisci

# Build APK Android (serve JDK 17)
cd android && ./gradlew assembleDebug   # gradlew.bat su Windows

# Deploy in produzione (dalla radice del progetto)
vercel deploy --prod --yes --scope danieles-projects-f241dba0
```

`tests/run_tests.py` è un unico script: non usa pytest e non accetta il
nome di un singolo test da riga di comando. Per isolarne uno, chiama la
funzione `test_*` corrispondente da un piccolo script Python temporaneo,
oppure commenta le altre nella lista `main()`.

## Architettura

### Flusso dei dati

Collector → `data/json/<data>.json` (metadati + tutte le ore in forma
strutturata) e `data/output/<data>/*.txt` (testi puliti) → Webapp legge
entrambi → Android sincronizza l'HTML già renderizzato dalla webapp.

Il `metadata.json` è la sorgente primaria per la vista giornaliera: le ore
sono suddivise in sezioni logiche (antifone, letture, responsori, salmodia
in tre gruppi, cantici, orazioni). I TXT sono un **fallback** usato solo
dove il metadata non ha la forma strutturata. Vedi
`repository.py:_build_tabs`.

### Package del collector (`liturgia_collector/`)

Pipeline a contratti chiari: `scraper` (fetch HTML, retry+backoff) →
`cleaner` (estrazione + pulizia, macchina a stati per le sezioni delle
ore) → `calendar` (calcolo algoritmico anno A/B/C, ciclo I/II, tempo,
settimana) → `writer` (TXT + JSON) → `collector` (orchestrazione per data,
il fallimento di una data non blocca le altre). `models.py` definisce
`LiturgicalDocument` e `DateInfo`.

> **Gotcha di packaging**: i moduli vivono in `liturgia_collector/` e non
> nella root perché un `calendar.py` a livello root oscurerebbe il modulo
> standard `calendar` (usato da `requests` via `email.utils`), rompendo
> l'app. Non spostare i moduli nella root.

### Webapp (`webapp/`)

Application factory in `app.py`: qui vivono solo configurazione e wiring;
le route stanno nei moduli `views_*.py`, ciascuno con una funzione
`register(app, ...)`. `repository.py` è il livello di lettura dei dati e
costruisce gli oggetti di dominio (`DayRecord`, `HourTab`, `HourSection`)
per i template.

**La webapp non è un package**: `api/index.py` aggiunge `webapp/` a
`sys.path`, quindi i moduli si importano piatti (`import views_admin`,
`from repository import ...`), non con percorsi relativi. Mantieni questo
stile quando aggiungi moduli.

Gli store (`ProprioStore`, `BiennaleStore`, `DownloadStore`, `UserStore`)
sono persistenza su file JSON, un file per voce. Il Biennale è associato a
una giornata tramite una **cascata di corrispondenze** da specifica a
generica (anno esatto → A/B/C → senza anno → senza ciclo) in
`repository.py:_find_biennale`.

### Modalità sola lettura

Su Vercel il filesystem è read-only. La costante `READ_ONLY` in `app.py` si
attiva con la variabile d'ambiente `VERCEL` (in locale si simula con
`LC_READ_ONLY=1`). In quella modalità la Raccolta è nascosta, i salvataggi
di Proprio/Biennale sono bloccati con avviso, e il registro dei download
non si scrive ma finisce nel log della funzione col prefisso `DOWNLOAD`.
Ogni nuova operazione che scrive su disco deve rispettare `READ_ONLY`.

### Flusso di aggiornamento in produzione

I dati si raccolgono **solo in locale** (Vercel è read-only), poi si
pubblicano con il deploy: i nuovi JSON in `data/json` partono col deploy e
il sito li mostra subito. L'app Android non scarica nulla da sola: si
aggiorna solo quando l'utente tocca il pulsante ⟳. Il flusso tipico a fine
mese è: Raccolta → deploy → apri l'app → ⟳.

## Note per l'esercizio

- `webapp/app.py` usa una **secret key fissa nel codice** e il repository
  GitHub è pubblico: chi legge il repo può forgiare una sessione admin.
  Va spostata su variabile d'ambiente (`SECRET_KEY`) prima dell'esercizio.
- Le form POST non hanno protezione CSRF.
- `data/downloads.jsonl` è stato di runtime, non versionato (`.gitignore`).
- La pagina Omelia richiede `YOUTUBE_API_KEY` (env) o `youtube_api_key`
  in `config.json`; senza chiave mostra un avviso e il resto funziona.
- `config.json` `version`, `versionName` in `android/app/build.gradle.kts`
  e il footer della webapp vanno tenuti allineati (oggi 2.08).
