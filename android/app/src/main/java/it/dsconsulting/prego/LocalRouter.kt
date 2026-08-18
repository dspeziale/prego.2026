package it.dsconsulting.prego

import android.content.Context
import android.net.Uri
import android.webkit.WebResourceResponse
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.io.File
import java.io.FileInputStream
import java.security.MessageDigest
import java.time.LocalDate

/**
 * Router locale: serve alla WebView le pagine scaricate (filesDir),
 * gli asset del sito e le librerie CDN incorporate nell'APK.
 *
 * L'app naviga sull'host fittizio [LOCAL_HOST]; ogni richiesta viene
 * intercettata e risolta senza rete.
 */
class LocalRouter(private val context: Context) {

    companion object {
        const val LOCAL_HOST = "prego.local"
        const val BASE = "https://$LOCAL_HOST"

        private val CDN_HOSTS = setOf("cdn.jsdelivr.net", "fonts.gstatic.com")
        private val ANALYTICS_HOSTS = setOf(
            "www.googletagmanager.com", "www.google-analytics.com",
            "region1.google-analytics.com",
        )
        private val RE_MESE = Regex("^/mese/(\\d{4})/(\\d{1,2})$")
        private val RE_ISLAND = Regex("\"availableDays\":\\s*\\[[^\\]]*\\]")

        // Le pagine del sito incorporano l'immagine del santo del giorno
        // ospitata su chiesacattolica.it. Viene scaricata durante la
        // sincronizzazione e servita da qui: aprire una giornata non deve
        // mai uscire in rete. Il filtro è ristretto ai tag <img> perché
        // gli <script src> dei CDN hanno già la loro intercettazione.
        val RE_REMOTE_IMG = Regex(
            "(<img\\b[^>]*?\\bsrc=\")(https?://[^\"]+)\"",
            RegexOption.IGNORE_CASE,
        )
        private const val IMG_DIR = "santi"

        /** Percorso locale che sostituisce un'immagine remota. */
        fun localImagePath(url: String): String {
            val digest = MessageDigest.getInstance("SHA-1")
                .digest(url.toByteArray(Charsets.UTF_8))
                .joinToString("") { "%02x".format(it.toInt() and 0xff) }
            val name = url.substringBefore('?').substringAfterLast('/')
            val extension = name.substringAfterLast('.', "")
                .lowercase().filter { it.isLetterOrDigit() }.take(4)
            return "/static/$IMG_DIR/$digest.${extension.ifEmpty { "jpg" }}"
        }
        // Senza questo header la WebView blocca i font cross-origin
        // (icone FontAwesome e PT Sans Narrow): CORS vale anche per
        // le risposte intercettate.
        private val CORS = mapOf("Access-Control-Allow-Origin" to "*")
        private val MIME = mapOf(
            "html" to "text/html", "css" to "text/css",
            "js" to "application/javascript", "json" to "application/json",
            "png" to "image/png", "jpg" to "image/jpeg", "jpeg" to "image/jpeg",
            "gif" to "image/gif", "svg" to "image/svg+xml",
            "ico" to "image/x-icon", "woff2" to "font/woff2",
            "woff" to "font/woff", "ttf" to "font/ttf",
        )
    }

    private val pagesDir = File(context.filesDir, "pages")
    private val staticDir = File(context.filesDir, "static")

    /** Giornate disponibili offline (dall'ultima sincronizzazione). */
    fun availableDays(): List<String> {
        val file = File(pagesDir, "giorni.json")
        if (!file.isFile) return emptyList()
        return try {
            val giorni = JSONObject(file.readText(Charsets.UTF_8))
                .getJSONArray("giorni")
            List(giorni.length()) { giorni.getString(it) }
        } catch (_: Exception) {
            emptyList()
        }
    }

    /** Risposta locale per la richiesta, o null (rete) per gli altri host. */
    fun intercept(url: Uri): WebResourceResponse? = when (url.host) {
        LOCAL_HOST -> local(url.path ?: "/")
        in CDN_HOSTS -> asset("cdn/${url.host}${url.path}") ?: notFound()
        "fonts.googleapis.com" ->
            asset("cdn/fonts.googleapis.com/pt-sans-narrow.css") ?: notFound()
        in ANALYTICS_HOSTS -> empty("application/javascript")
        else -> null
    }

    private fun local(path: String): WebResourceResponse {
        RE_MESE.matchEntire(path)?.let { match ->
            val (year, month) = match.destructured
            return page("mese/$year-${month.padStart(2, '0')}.html")
        }
        return when {
            path == "/" -> home()
            path.startsWith("/giorno/") ->
                page("giorno/${path.removePrefix("/giorno/")}.html")
            path == "/mese/corrente" -> currentMonth()
            path == "/about" -> page("about.html")
            path.startsWith("/static/") -> static(path.removePrefix("/static/"))
            path.startsWith("/app/") ->
                asset("www/${path.removePrefix("/app/")}") ?: notFound()
            path == "/favicon.ico" -> static("icon-192.png")
            else -> fallbackPage()
        }
    }

    /** Home: la giornata di oggi, o la più vicina disponibile. */
    private fun home(): WebResourceResponse {
        val days = availableDays()
        if (days.isEmpty()) return assetHtml("www/start.html")
        val today = LocalDate.now().toString()
        val target = when {
            today in days -> today
            else -> days.lastOrNull { it < today } ?: days.first()
        }
        return page("giorno/$target.html")
    }

    private fun currentMonth(): WebResourceResponse {
        val now = LocalDate.now()
        val current = File(
            pagesDir, "mese/%04d-%02d.html".format(now.year, now.monthValue)
        )
        if (current.isFile) return html(current)
        availableDays().lastOrNull()?.let { last ->
            val fallback = File(pagesDir, "mese/${last.substring(0, 7)}.html")
            if (fallback.isFile) return html(fallback)
        }
        return fallbackPage()
    }

    private fun page(relative: String): WebResourceResponse {
        val file = File(pagesDir, relative)
        return if (file.isFile) html(file) else fallbackPage()
    }

    private fun fallbackPage(): WebResourceResponse =
        if (availableDays().isEmpty()) assetHtml("www/start.html")
        else assetHtml("www/manca.html")

    /**
     * Pagina HTML scaricata; l'elenco availableDays incorporato nella
     * pagina viene sostituito con quello locale aggiornato, così il
     * selettore della data conosce anche le giornate sincronizzate dopo,
     * e le immagini remote vengono puntate alla copia locale.
     */
    private fun html(file: File): WebResourceResponse {
        var text = file.readText(Charsets.UTF_8)
        val days = availableDays()
        if (days.isNotEmpty()) {
            val island = "\"availableDays\": " + JSONArray(days)
            text = RE_ISLAND.replace(text) { island }
        }
        // Sempre, anche per le pagine sincronizzate prima che l'app
        // salvasse le immagini: se la copia locale manca la richiesta
        // resta interna e risponde vuota, senza toccare la rete.
        text = RE_REMOTE_IMG.replace(text) { match ->
            match.groupValues[1] + localImagePath(match.groupValues[2]) + "\""
        }
        return bytes("text/html", text.toByteArray(Charsets.UTF_8))
    }

    private fun static(relative: String): WebResourceResponse {
        val file = File(staticDir, relative)
        if (file.isFile) {
            val mime = mime(relative)
            return WebResourceResponse(
                mime, encoding(mime), 200, "OK", CORS, FileInputStream(file)
            )
        }
        return asset("static/$relative") ?: notFound()
    }

    private fun asset(path: String): WebResourceResponse? = try {
        val mime = mime(path)
        WebResourceResponse(
            mime, encoding(mime), 200, "OK", CORS, context.assets.open(path)
        )
    } catch (_: Exception) {
        null
    }

    private fun assetHtml(path: String): WebResourceResponse =
        asset(path) ?: bytes(
            "text/html",
            "<h1>Prego</h1><p>Risorsa non trovata.</p>".toByteArray()
        )

    private fun notFound(): WebResourceResponse = empty("text/plain")

    private fun empty(mime: String): WebResourceResponse =
        bytes(mime, ByteArray(0))

    private fun bytes(mime: String, data: ByteArray): WebResourceResponse =
        WebResourceResponse(
            mime, encoding(mime), 200, "OK", CORS, ByteArrayInputStream(data)
        )

    private fun mime(path: String): String {
        val extension = path.substringBefore('?')
            .substringAfterLast('.', "").lowercase()
        return MIME[extension] ?: "application/octet-stream"
    }

    private fun encoding(mime: String): String? =
        if (mime.startsWith("text/") || mime == "application/javascript"
            || mime == "application/json") "utf-8" else null
}
