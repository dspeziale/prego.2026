# Prego — app Android

Il sito **Prego** ([prego.vercel.app](https://prego.vercel.app)) come
applicazione Android nativa, con tutti i dati scaricati localmente sullo
smartphone: una volta sincronizzata, **funziona completamente senza rete**.

## Come funziona

- L'app è una WebView Kotlin che naviga sull'host locale fittizio
  `prego.local`: ogni richiesta viene intercettata e servita dalla
  memoria del telefono, mai dalla rete.
- La **sincronizzazione** (`SyncManager`) scarica da `prego.vercel.app`:
  - l'elenco delle giornate disponibili (`/api/giorni`);
  - la pagina completa di ogni giornata (`/giorno/<data>`), con dentro
    Messa, Ufficio, Lodi, Ora media, Vespri, Compieta, scheda Giorno,
    Proprio e Biennale già composti dal server;
  - i calendari mensili, la pagina About e gli asset css/js del sito;
  - le immagini del santo del giorno, che il sito ospita su
    chiesacattolica.it: vengono salvate sul telefono e servite da lì,
    così aprire una giornata non contatta mai un server esterno.
- Le **librerie esterne** (AdminLTE, Bootstrap, jQuery, FontAwesome,
  Awesome Notifications, font PT Sans Narrow) sono incorporate nell'APK
  in `app/src/main/assets/cdn/` e servite al posto dei CDN
  (`LocalRouter`), quindi la grafica è identica al sito anche offline.
- All'avvio l'app apre la giornata di oggi (o la più vicina
  disponibile) e **non scarica nulla**: nessuna sincronizzazione
  automatica, nessuna richiesta in sottofondo. Si accede alla rete solo
  quando lo chiede l'utente.
- Il pulsante ⟳ in basso a sinistra permette di scaricare le novità o di
  riscaricare tutto (utile se sul sito sono stati modificati Proprio o
  Biennale di giornate già scaricate). Le giornate degli ultimi 7 giorni
  vengono comunque sempre riaggiornate.
- Tema chiaro/scuro e dimensione del carattere funzionano come sul sito
  e vengono ricordati (localStorage della WebView).

Solo la pagina **Omelia** (ricerca su YouTube) richiede la rete, e vi si
arriva toccando il collegamento: offline avvisa che è disponibile solo
online. Le funzioni di
modifica (login, Proprio, Biennale, Raccolta) restano sul sito.

## Requisiti e build

- **Android Studio** (Koala o successivo) con SDK 34 — è la via
  consigliata: aprire la cartella `android/` come progetto, attendere il
  sync di Gradle e usare *Build ▸ Build App Bundle(s) / APK(s) ▸ Build APK(s)*.
- In alternativa da riga di comando (serve un JDK 17):

  ```
  cd android
  ./gradlew assembleDebug        # gradlew.bat su Windows
  ```

  L'APK esce in `app/build/outputs/apk/debug/app-debug.apk`.

- Requisito sul telefono: Android 8.0 (API 26) o successivo.

Per pubblicare una release firmata: *Build ▸ Generate Signed App Bundle/APK*
in Android Studio (creare un keystore la prima volta).

## Occupazione e dati

Le pagine scaricate pesano indicativamente 50–100 MB per un anno intero
di giornate; gli asset incorporati nell'APK circa 3 MB. I dati stanno in
`filesDir` dell'app (rimossi disinstallando l'app o con "Cancella dati").

## Struttura

```
android/
├── app/src/main/
│   ├── java/it/dsconsulting/prego/
│   │   ├── MainActivity.kt    # WebView, navigazione, pulsante sync
│   │   ├── LocalRouter.kt     # serve pagine e asset offline
│   │   └── SyncManager.kt     # scarica i dati dal sito
│   ├── assets/
│   │   ├── cdn/               # librerie CDN incorporate
│   │   ├── static/            # css/js/icona del sito (fallback)
│   │   └── www/               # pagine locali (avvio, pagina mancante)
│   └── res/                   # layout, temi, icone
└── ...file gradle
```

Il sito espone per l'app l'endpoint `GET /api/giorni`
(`{"giorni": ["2026-01-01", ...], "totale": N}`).

© 2024-26 DS Consulting
