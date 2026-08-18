"""Amministrazione e distribuzione dell'app Android.

Tre route: la pagina pubblica da cui scaricare l'app, il download vero e
proprio (che viene annotato nel registro) e il cruscotto riservato agli
utenti abilitati.
"""

from datetime import date

from flask import abort, render_template, request, send_file

from downloads import DownloadStore

APK_MIME = "application/vnd.android.package-archive"
DOWNLOAD_NAME = "Prego.apk"


def client_ip(req) -> str:
    """IP del chiamante, tenendo conto del proxy davanti all'app.

    Su Vercel la richiesta arriva dal proxy, quindi remote_addr è
    l'indirizzo interno: quello vero è il primo di X-Forwarded-For.
    """
    forwarded = req.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return req.remote_addr or ""


def register(app, download_store, apk_paths, repository, proprio_store,
             biennale_store, user_store, login_required, version) -> None:
    """Registra le route sull'app."""

    def apk_file():
        """Primo APK disponibile tra i percorsi noti, o None."""
        for path in apk_paths:
            if path.is_file():
                return path
        return None

    def apk_info():
        """Nome, dimensione e data dell'APK pubblicato."""
        path = apk_file()
        if path is None:
            return None
        stat = path.stat()
        return {
            "nome": path.name,
            "mb": round(stat.st_size / (1024 * 1024), 1),
            "aggiornato": date.fromtimestamp(stat.st_mtime),
        }

    @app.route("/app")
    def app_page():
        """Pagina pubblica di presentazione e download dell'app."""
        return render_template("app.html", apk=apk_info())

    @app.route("/app/scarica")
    def app_download():
        """Consegna l'APK e annota chi lo ha scaricato."""
        path = apk_file()
        if path is None:
            abort(404)
        download_store.record(
            client_ip(request),
            request.headers.get("User-Agent", ""),
            path.name,
        )
        return send_file(
            path, as_attachment=True,
            download_name=DOWNLOAD_NAME, mimetype=APK_MIME,
        )

    @app.route("/admin")
    @login_required
    def admin():
        """Cruscotto: download dell'app e stato dell'archivio."""
        entries = download_store.entries()
        giorni = repository.available_days()
        archivio = {
            "giornate": len(giorni),
            "mesi": len(repository.available_months()),
            "prima": giorni[0] if giorni else None,
            "ultima": giorni[-1] if giorni else None,
            "proprio": len(proprio_store.list_entries()),
            "biennale": len(biennale_store.list_entries()),
        }
        return render_template(
            "admin.html",
            downloads=entries,
            riepilogo=DownloadStore.summary(entries),
            registrazione_attiva=download_store.writable,
            archivio=archivio,
            utenti=user_store.usernames(),
            apk=apk_info(),
            versione=version,
        )
