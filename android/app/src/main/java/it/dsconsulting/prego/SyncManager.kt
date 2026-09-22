package it.dsconsulting.prego

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.time.LocalDate
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger

/**
 * Sincronizzazione: scarica dal sito tutte le pagine (giornate, mesi,
 * about), gli asset e le immagini del santo del giorno in filesDir,
 * così l'app funziona senza rete.
 *
 * Parte solo su richiesta esplicita dell'utente: è l'unico momento in
 * cui l'app accede alla rete per i dati.
 *
 * Scarica solo le giornate mancanti; con force = true riscarica tutto
 * (utile quando cambiano Proprio/Biennale su giornate già scaricate).
 * Le giornate recenti vengono comunque sempre aggiornate.
 */
class SyncManager(private val context: Context) {

    interface Listener {
        fun onProgress(done: Int, total: Int)
        fun onDone(success: Boolean, message: String)
    }

    companion object {
        const val REMOTE_HOST = "prego.vercel.app"
        const val REMOTE = "https://$REMOTE_HOST"
        private const val THREADS = 4
        private const val RECENT_DAYS = 7L
    }

    @Volatile
    var running = false
        private set

    private val imagesSeen = ConcurrentHashMap.newKeySet<String>()
    private val savedImages = AtomicInteger(0)
    private val imageErrors = AtomicInteger(0)

    fun start(force: Boolean, listener: Listener) {
        if (running) return
        running = true
        Thread({
            try {
                run(force, listener)
            } catch (exc: Exception) {
                listener.onDone(false, exc.message ?: "errore imprevisto")
            } finally {
                running = false
            }
        }, "prego-sync").start()
    }

    private fun run(force: Boolean, listener: Listener) {
        val pagesDir = File(context.filesDir, "pages")
        val staticDir = File(context.filesDir, "static")
        imagesSeen.clear()
        savedImages.set(0)
        imageErrors.set(0)

        val giorniText = fetch("$REMOTE/api/giorni").toString(Charsets.UTF_8)
        val giorniArray = JSONObject(giorniText).getJSONArray("giorni")
        val giorni = List(giorniArray.length()) { giorniArray.getString(it) }
        if (giorni.isEmpty()) {
            listener.onDone(false, "Nessuna giornata disponibile sul sito.")
            return
        }

        val recentFrom = LocalDate.now().minusDays(RECENT_DAYS).toString()
        val jobs = mutableListOf<Pair<String, () -> Unit>>()
        fun page(path: String, dest: File) {
            jobs += path to { save(path, dest) }
        }
        page("/static/css/prego.css", File(staticDir, "css/prego.css"))
        page("/static/js/prego.js", File(staticDir, "js/prego.js"))
        page("/static/icon-192.png", File(staticDir, "icon-192.png"))
        page("/about", File(pagesDir, "about.html"))
        giorni.map { it.substring(0, 7) }.distinct().forEach { yearMonth ->
            val (year, month) = yearMonth.split("-")
            page(
                "/mese/$year/${month.toInt()}",
                File(pagesDir, "mese/$yearMonth.html"),
            )
        }
        // Santi del giorno: una pagina per giornata, legata al giorno del
        // mese e quindi stabile. Si scarica solo se manca (o con "tutto").
        giorni.forEach { iso ->
            val dest = File(pagesDir, "santi/$iso.html")
            if (force || !dest.isFile) page("/santi/$iso", dest)
        }
        giorni.forEach { iso ->
            val dest = File(pagesDir, "giorno/$iso.html")
            if (force || !dest.isFile || iso >= recentFrom) {
                jobs += "/giorno/$iso" to {
                    save("/giorno/$iso", dest)
                    saveImages(dest, force)
                }
            } else {
                // Giornata già sul telefono: la pagina non viene
                // riscaricata, si recuperano solo le immagini mancanti
                // (nessuna richiesta se ci sono già tutte).
                jobs += "immagini $iso" to { saveImages(dest, false) }
            }
        }

        val total = jobs.size
        val done = AtomicInteger(0)
        val errors = ConcurrentLinkedQueue<String>()
        val executor = Executors.newFixedThreadPool(THREADS)
        val latch = CountDownLatch(total)
        listener.onProgress(0, total)
        jobs.forEach { (label, job) ->
            executor.execute {
                try {
                    job()
                } catch (exc: Exception) {
                    errors += "$label: ${exc.message}"
                } finally {
                    listener.onProgress(done.incrementAndGet(), total)
                    latch.countDown()
                }
            }
        }
        latch.await()
        executor.shutdown()

        if (errors.size > total / 10) {
            listener.onDone(
                false, "Troppi errori (${errors.size}): ${errors.first()}"
            )
            return
        }
        // L'elenco delle giornate va scritto per ultimo: da qui in poi
        // il router considera disponibili le nuove pagine.
        File(pagesDir, "giorni.json").apply { parentFile?.mkdirs() }
            .writeText(giorniText, Charsets.UTF_8)
        val message = StringBuilder("Scaricate $total risorse")
        if (savedImages.get() > 0) {
            message.append(" e ${savedImages.get()} immagini")
        }
        if (errors.isNotEmpty()) message.append(", ${errors.size} errori")
        if (imageErrors.get() > 0) {
            message.append(", ${imageErrors.get()} immagini non scaricate")
        }
        listener.onDone(true, message.append(".").toString())
    }

    /**
     * Salva le immagini remote citate nella pagina: il santo del giorno
     * è ospitato su chiesacattolica.it e senza questa copia la WebView
     * lo scaricherebbe da internet a ogni apertura della giornata.
     *
     * Sono accessorie, quindi un errore qui non fa fallire la
     * sincronizzazione: al massimo l'immagine resta vuota.
     */
    private fun saveImages(page: File, force: Boolean) {
        if (!page.isFile) return
        val html = page.readText(Charsets.UTF_8)
        LocalRouter.RE_REMOTE_IMG.findAll(html).forEach { match ->
            val url = match.groupValues[2]
            val dest = File(
                context.filesDir,
                LocalRouter.localImagePath(url).removePrefix("/"),
            )
            if (dest.isFile && !force) return@forEach
            if (!imagesSeen.add(url)) return@forEach
            try {
                save(url, dest, absolute = true)
                savedImages.incrementAndGet()
            } catch (exc: Exception) {
                imageErrors.incrementAndGet()
            }
        }
    }

    private fun fetch(url: String): ByteArray {
        val connection = URL(url).openConnection() as HttpURLConnection
        connection.connectTimeout = 20_000
        connection.readTimeout = 60_000
        connection.setRequestProperty("User-Agent", "PregoAndroid/${BuildConfig.VERSION_NAME}")
        try {
            if (connection.responseCode != 200) {
                throw IllegalStateException(
                    "HTTP ${connection.responseCode} su $url"
                )
            }
            return connection.inputStream.use { it.readBytes() }
        } finally {
            connection.disconnect()
        }
    }

    /** Salva una risorsa; con absolute = true il path è un URL intero. */
    private fun save(path: String, dest: File, absolute: Boolean = false) {
        dest.parentFile?.mkdirs()
        val data = fetch(if (absolute) path else REMOTE + path)
        val tmp = File(dest.parentFile, dest.name + ".tmp")
        tmp.writeBytes(data)
        if (!tmp.renameTo(dest)) {
            tmp.copyTo(dest, overwrite = true)
            tmp.delete()
        }
    }
}
