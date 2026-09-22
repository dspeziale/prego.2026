package it.dsconsulting.prego

import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.os.Build
import android.os.Bundle
import android.os.UserManager
import android.provider.Settings
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity

/**
 * Prego per Android: il sito, reso disponibile offline.
 *
 * La WebView naviga sull'host locale [LocalRouter.LOCAL_HOST]; le pagine
 * arrivano dalla memoria dell'app (sincronizzate da prego.vercel.app) e
 * le librerie CSS/JS dagli asset dell'APK.
 *
 * Nulla viene scaricato di propria iniziativa: la sincronizzazione parte
 * solo quando la chiede l'utente (pulsante di sincronizzazione o
 * pulsante delle pagine start/manca). Le altre uscite in rete sono la
 * pagina Omelia (ricerca YouTube) e i link esterni, conseguenza di un
 * tocco dell'utente, e il ping anonimo di avvio ([LaunchPing]: poche
 * decine di byte, serve a contare le installazioni e a sapere se c'è
 * una versione nuova).
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var syncBar: LinearLayout
    private lateinit var syncProgress: ProgressBar
    private lateinit var syncLabel: TextView
    private lateinit var router: LocalRouter
    private lateinit var syncManager: SyncManager

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        router = LocalRouter(this)
        syncManager = SyncManager(this)
        webView = findViewById(R.id.webView)

        // ping anonimo di avvio (statistiche d'uso) e, se il sito ha una
        // versione più nuova, proposta di aggiornamento
        if (savedInstanceState == null && isOnline()) {
            LaunchPing.send(this) { versione, url ->
                runOnUiThread { offerUpdate(versione, url) }
            }
        }
        syncBar = findViewById(R.id.syncBar)
        syncProgress = findViewById(R.id.syncProgress)
        syncLabel = findViewById(R.id.syncLabel)

        with(webView.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true // localStorage: tema scuro e carattere
            allowFileAccess = false
            allowContentAccess = false
        }
        webView.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(
                view: WebView?, request: WebResourceRequest
            ): WebResourceResponse? =
                router.intercept(request.url)
                    ?: super.shouldInterceptRequest(view, request)

            override fun onPageFinished(view: WebView, url: String) {
                super.onPageFinished(view, url)
                injectUserName(view, url)
            }

            override fun shouldOverrideUrlLoading(
                view: WebView, request: WebResourceRequest
            ): Boolean {
                val url = request.url
                val path = url.path ?: "/"
                // download dell'APK (aggiornamento dell'app): sempre nel
                // browser del telefono, che scarica e avvia l'installazione
                if (path.startsWith("/app/") &&
                    (url.host == LocalRouter.LOCAL_HOST || url.host == SyncManager.REMOTE_HOST)
                ) {
                    runCatching {
                        startActivity(
                            Intent(Intent.ACTION_VIEW, android.net.Uri.parse(SyncManager.REMOTE + path))
                        )
                    }
                    return true
                }
                return when (url.host) {
                    LocalRouter.LOCAL_HOST -> when {
                        // l'omelia (ricerca YouTube) esiste solo online
                        path.startsWith("/omelia/") -> {
                            if (isOnline()) {
                                view.loadUrl(SyncManager.REMOTE + path)
                            } else {
                                toast("L'omelia è disponibile solo online.")
                            }
                            true
                        }
                        else -> false
                    }
                    SyncManager.REMOTE_HOST ->
                        // dal sito remoto si torna alle pagine locali
                        if (path.startsWith("/omelia")) {
                            false
                        } else {
                            view.loadUrl(LocalRouter.BASE + path)
                            true
                        }
                    else -> {
                        // link esterni (YouTube, chiesacattolica.it...)
                        runCatching {
                            startActivity(Intent(Intent.ACTION_VIEW, url))
                        }
                        true
                    }
                }
            }
        }
        webView.addJavascriptInterface(PregoBridge(), "PregoApp")

        findViewById<ImageButton>(R.id.syncButton).setOnClickListener {
            askSync()
        }
        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    if (webView.canGoBack()) webView.goBack() else finish()
                }
            }
        )

        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState)
        } else {
            webView.loadUrl(LocalRouter.BASE + "/")
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        webView.saveState(outState)
    }

    private fun isOnline(): Boolean {
        val manager =
            getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        return manager.activeNetwork != null
    }

    /** Unico ingresso alla rete per i dati: sempre su richiesta esplicita. */
    private fun askSync() {
        if (syncManager.running) return
        AlertDialog.Builder(this)
            .setTitle(R.string.sync_button)
            .setItems(
                arrayOf("Scarica solo le novità", "Riscarica tutto")
            ) { _, which -> startSync(force = which == 1) }
            .show()
    }

    private fun startSync(force: Boolean) {
        if (syncManager.running) return
        if (!isOnline()) {
            toast(getString(R.string.sync_offline))
            return
        }
        syncBar.visibility = View.VISIBLE
        syncProgress.progress = 0
        syncLabel.text = getString(R.string.sync_running)
        syncManager.start(force, object : SyncManager.Listener {
            override fun onProgress(done: Int, total: Int) = runOnUiThread {
                syncProgress.max = total
                syncProgress.progress = done
                syncLabel.text = "$done/$total"
            }

            override fun onDone(success: Boolean, message: String) =
                runOnUiThread {
                    syncBar.visibility = View.GONE
                    val prefix = getString(
                        if (success) R.string.sync_done else R.string.sync_error
                    )
                    toast("$prefix — $message")
                    if (success) {
                        getSharedPreferences("prego", MODE_PRIVATE).edit()
                            .putLong(
                                "ultima_sincronizzazione",
                                System.currentTimeMillis()
                            )
                            .apply()
                        webView.reload()
                    }
                }
        })
    }

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }

    /** Il sito pubblica una versione più nuova: si propone il download. */
    private fun offerUpdate(versione: String, url: String) {
        if (isFinishing || url.isBlank()) return
        AlertDialog.Builder(this)
            .setTitle("Aggiornamento disponibile")
            .setMessage(
                "È uscita la versione $versione di Prego " +
                    "(installata: ${BuildConfig.VERSION_NAME}). " +
                    "Scaricarla ora? Si installa sopra, i dati restano."
            )
            .setPositiveButton("Scarica") { _, _ ->
                runCatching {
                    startActivity(Intent(Intent.ACTION_VIEW, android.net.Uri.parse(url)))
                }
            }
            .setNegativeButton("Più tardi", null)
            .show()
    }

    /**
     * Nome dell'utente Android: profilo utente se leggibile, altrimenti
     * il nome del dispositivo impostato dall'utente, altrimenti il
     * modello del telefono.
     */
    private fun deviceUserName(): String {
        if (Build.VERSION.SDK_INT >= 34) {
            runCatching {
                val manager =
                    getSystemService(Context.USER_SERVICE) as UserManager
                val name = manager.userName?.trim().orEmpty()
                if (name.isNotEmpty()) return name
            }
        }
        runCatching {
            val device = Settings.Global.getString(
                contentResolver, Settings.Global.DEVICE_NAME
            )?.trim().orEmpty()
            if (device.isNotEmpty()) return device
        }
        return Build.MODEL
    }

    /** Mostra il nome dell'utente in cima al menu laterale. */
    private fun injectUserName(view: WebView, url: String) {
        if (android.net.Uri.parse(url).host != LocalRouter.LOCAL_HOST) return
        val name = org.json.JSONObject.quote(deviceUserName())
        view.evaluateJavascript(
            """
            (function () {
                var menu = document.querySelector(".nav-sidebar");
                if (!menu || document.getElementById("prego-utente")) return;
                var li = document.createElement("li");
                li.className = "nav-item";
                li.id = "prego-utente";
                li.innerHTML = '<a class="nav-link" style="cursor:default">'
                    + '<i class="nav-icon fas fa-user"></i>'
                    + '<p style="font-weight:bold"></p></a>';
                li.querySelector("p").textContent = $name;
                menu.insertBefore(li, menu.firstChild);
            })();
            """.trimIndent(),
            null
        )
    }

    /** Funzioni richiamabili dalle pagine locali (start/manca). */
    inner class PregoBridge {
        @JavascriptInterface
        fun sync() {
            runOnUiThread { startSync(force = false) }
        }

        @JavascriptInterface
        fun syncTutto() {
            runOnUiThread { startSync(force = true) }
        }
    }
}
