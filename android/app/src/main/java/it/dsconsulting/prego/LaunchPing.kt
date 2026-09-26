package it.dsconsulting.prego

import android.content.Context
import android.os.Build
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import java.util.UUID

/**
 * Ping di avvio verso il sito: quante installazioni usano l'app, e di chi.
 *
 * A ogni apertura manda `POST /api/ping` con un identificativo casuale
 * dell'installazione (generato la prima volta e tenuto nelle
 * preferenze), versione dell'app, versione di Android, modello, lingua
 * e il nome dell'utente: quello inserito in Impostazioni oppure, in sua
 * assenza, il nome del profilo o del telefono. L'email parte solo se
 * l'utente l'ha inserita in Impostazioni (Android non la rende leggibile
 * alle app). In risposta il sito indica la versione pubblicata: se è più
 * nuova, [onUpdate] riceve versione e URL.
 *
 * Tutto avviene in un thread in sottofondo, con timeout brevi; qualsiasi
 * errore viene ignorato in silenzio: il ping non deve mai disturbare.
 */
object LaunchPing {

    private const val PREFS = "prego"
    private const val KEY_ID = "installazione"
    private const val KEY_LAUNCHES = "avvii"
    const val KEY_NOME = "utente_nome"
    const val KEY_EMAIL = "utente_email"

    /**
     * @param deviceName nome ricavato dal telefono e sua origine
     *   ("profilo" o "dispositivo"), usato se l'utente non ne ha inserito uno
     * @param countLaunch false per un nuovo invio dopo aver salvato i dati
     *   in Impostazioni (non è un avvio)
     */
    fun send(
        context: Context,
        deviceName: Pair<String, String>,
        countLaunch: Boolean = true,
        onUpdate: (versione: String, url: String) -> Unit = { _, _ -> },
    ) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val id = prefs.getString(KEY_ID, null) ?: UUID.randomUUID().toString().also {
            prefs.edit().putString(KEY_ID, it).apply()
        }
        val launches = prefs.getInt(KEY_LAUNCHES, 0) + if (countLaunch) 1 else 0
        if (countLaunch) prefs.edit().putInt(KEY_LAUNCHES, launches).apply()

        val userName = prefs.getString(KEY_NOME, "")?.trim().orEmpty()
        val email = prefs.getString(KEY_EMAIL, "")?.trim().orEmpty()
        val (nome, fonte) =
            if (userName.isNotEmpty()) userName to "utente" else deviceName

        val body = JSONObject()
            .put("id", id)
            .put("versione", BuildConfig.VERSION_NAME)
            .put("versionCode", BuildConfig.VERSION_CODE)
            .put("android", Build.VERSION.RELEASE ?: "")
            .put("sdk", Build.VERSION.SDK_INT)
            .put("modello", "${Build.MANUFACTURER} ${Build.MODEL}".trim())
            .put("lingua", Locale.getDefault().toLanguageTag())
            .put("avvii", launches)
            .put("nome", nome)
            .put("nome_fonte", fonte)
            .put("email", email)
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
