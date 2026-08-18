package it.dsconsulting.prego

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.time.LocalDate
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger

/**
 * Sincronizzazione: scarica dal sito tutte le pagine (giornate, mesi,
 * about) e gli asset in filesDir, così l'app funziona senza rete.
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

        val giorniText = fetch("$REMOTE/api/giorni").toString(Charsets.UTF_8)
        val giorniArray = JSONObject(giorniText).getJSONArray("giorni")
        val giorni = List(giorniArray.length()) { giorniArray.getString(it) }
        if (giorni.isEmpty()) {
            listener.onDone(false, "Nessuna giornata disponibile sul sito.")
            return
        }

        val recentFrom = LocalDate.now().minusDays(RECENT_DAYS).toString()
        val tasks = mutableListOf<Pair<String, File>>()
        tasks += "/static/css/prego.css" to File(staticDir, "css/prego.css")
        tasks += "/static/js/prego.js" to File(staticDir, "js/prego.js")
        tasks += "/static/icon-192.png" to File(staticDir, "icon-192.png")
        tasks += "/about" to File(pagesDir, "about.html")
        giorni.map { it.substring(0, 7) }.distinct().forEach { yearMonth ->
            val (year, month) = yearMonth.split("-")
            tasks += "/mese/$year/${month.toInt()}" to
                File(pagesDir, "mese/$yearMonth.html")
        }
        giorni.forEach { iso ->
            val dest = File(pagesDir, "giorno/$iso.html")
            if (force || !dest.isFile || iso >= recentFrom) {
                tasks += "/giorno/$iso" to dest
            }
        }

        val total = tasks.size
        val done = AtomicInteger(0)
        val errors = ConcurrentLinkedQueue<String>()
        val executor = Executors.newFixedThreadPool(THREADS)
        val latch = CountDownLatch(total)
        listener.onProgress(0, total)
        tasks.forEach { (path, dest) ->
            executor.execute {
                try {
                    save(path, dest)
                } catch (exc: Exception) {
                    errors += "$path: ${exc.message}"
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
        val message = if (errors.isEmpty()) {
            "Scaricate $total risorse."
        } else {
            "Completata con ${errors.size} errori su $total."
        }
        listener.onDone(true, message)
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

    private fun save(path: String, dest: File) {
        dest.parentFile?.mkdirs()
        val data = fetch(REMOTE + path)
        val tmp = File(dest.parentFile, dest.name + ".tmp")
        tmp.writeBytes(data)
        if (!tmp.renameTo(dest)) {
            tmp.copyTo(dest, overwrite = true)
            tmp.delete()
        }
    }
}
