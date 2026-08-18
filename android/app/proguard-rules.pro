# Interfaccia JavaScript esposta alla WebView: non va offuscata.
-keepclassmembers class it.dsconsulting.prego.MainActivity$PregoBridge {
    @android.webkit.JavascriptInterface <methods>;
}
