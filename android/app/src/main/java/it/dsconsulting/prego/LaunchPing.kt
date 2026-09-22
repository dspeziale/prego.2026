package it.dsconsulting.prego

import android.content.Context
import android.os.Build
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import java.util.UUID

/**
 * Ping di avvio verso il sito: quante installazioni usano l'app.
 *
 * A ogni apertura manda `POST /api/ping` con un identificativo casuale
 * dell'installazione (generato la prima volta e tenuto nelle
 * preferenze: nessun dato personale), versione dell'app, versione di
 * Android, modello e lingua. In risposta il sito indica la versione
 * pubblicata: se è più nuova, [onUpdate] riceve versione e URL.
 *
 * Tutto avviene in un thread in sottofondo, con timeout brevi; qualsiasi
 * errore viene ignorato in silenzio: il ping non deve mai disturbare.
 */
object LaunchPing {

    private const val PREFS = "prego"
    private const val KEY_ID = "installazione"
    private const val KEY_LAUNCHES = "avvii"

    fun send(context: Context, onUpdate: (versione: String, url: String) -> Unit) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val id = prefs.getString(KEY_ID, null) ?: UUID.randomUUID().toString().also {
            prefs.edit().putString(KEY_ID, it).apply()
        }
        val launches = prefs.getInt(KEY_LAUNCHES, 0) + 1
        prefs.edit().putInt(KEY_LAUNCHES, launches).apply()

        val body = JSONObject()
            .put("id", id)
            .put("versione", BuildConfig.VERSION_NAME)
            .put("versionCode", BuildConfig.VERSION_CODE)
            .put("android", Build.VERSION.RELEASE ?: "")
            .put("sdk", Build.VERSION.SDK_INT)
            .put("modello", "${Build.MANUFACTURER} ${Build.MODEL}".trim())
            .put("lingua", Locale.getDefault().toLanguageTag())
            .put("avvii", launches)
            .toString()

        Thread({
            try {
                val connection =
                    URL("${SyncManager.REMOTE}/api/ping").openConnection() as HttpURLConnection
                connection.connectTimeout = 5_000
                connection.readTimeout = 8_000
                connection.requestMethod = "POST"
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                connection.setRequestProperty(
                    "User-Agent", "PregoAndroid/${BuildConfig.VERSION_NAME}"
                )
                connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
                if (connection.responseCode == 200) {
                    val answer = JSONObject(
                        connection.inputStream.use { it.readBytes() }.toString(Charsets.UTF_8)
                    )
                    val published = answer.optInt("versionCode", 0)
                    if (published > BuildConfig.VERSION_CODE) {
                        onUpdate(answer.optString("versione"), answer.optString("url"))
                    }
                }
                connection.disconnect()
            } catch (_: Exception) {
                // offline o sito irraggiungibile: nessun disturbo all'utente
            }
        }, "prego-ping").start()
    }
}
