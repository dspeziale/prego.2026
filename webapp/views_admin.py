"""Amministrazione e distribuzione dell'app Android.

Tre route: la pagina pubblica da cui scaricare l'app, il download vero e
proprio (che viene annotato nel registro) e il cruscotto riservato agli
utenti abilitati.
"""

import logging
from datetime import date

from flask import abort, render_template, request, send_file, url_for

from downloads import DownloadStore
from pings import PingError, clean_ping

logger = logging.getLogger(__name__)

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
             biennale_store, user_store, login_required, version,
             version_code: int = 0, apk_fallback_url: str = "",
             ping_store=None) -> None:
    """Registra le route sull'app."""

    @app.route("/api/ping", methods=["POST"])
    def api_ping():
        """Avvio dell'app Android: registra il ping e risponde con la
        versione pubblicata, così l'app può proporre l'aggiornamento."""
        ping = clean_ping(request.get_json(silent=True))
        if ping is None:
            abort(400)
        if ping_store is not None:
            try:
                ping_store.record(ping)
            except PingError as exc:
                # il ping non deve mai fallire per l'app: si annota e basta
                logger.warning("Ping non registrato: %s", exc)
        return {
            "versione": version,
            "versionCode": version_code,
            "url": url_for("app_download", _external=True),
        }

    @app.route("/admin/utenti")
    @login_required
    def admin_utenti():
        """Quante installazioni usano l'app, dai ping di avvio."""
        attivo = ping_store is not None and ping_store.enabled
        stats, errore = None, None
        if attivo:
            try:
                stats = ping_store.stats()
            except PingError as exc:
                errore = str(exc)
        return render_template("admin_utenti.html", attivo=attivo,
                               stats=stats, errore=errore)

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
        # nome con la versione (Prego-2.11.apk): due download successivi
        # non si confondono nella cartella del telefono, e niente cache
        response = send_file(
            path, as_attachment=True,
            download_name=f"Prego-{version}.apk", mimetype=APK_MIME,
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.route("/api/version")
    def api_version():
        """Versione dell'app pubblicata (per il controllo aggiornamenti)."""
        return {
            "versione": version,
            "versionCode": version_code,
            "url": url_for("app_download", _external=True),
            "url_alternativo": apk_fallback_url,
        }

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
