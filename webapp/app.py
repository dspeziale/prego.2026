"""Prego (LiturgiaViewer): interfaccia web per i dati di LiturgiaCollector.

Avvio:
    python webapp/app.py        # http://localhost:5300

Application factory: qui vivono solo configurazione e wiring; le route
sono nei moduli views_*.py (core, auth, proprio, biennale, raccolta).
"""

import json
import logging
import os
from datetime import date
from functools import wraps
from pathlib import Path
from typing import Optional, Tuple

from flask import Flask, flash, redirect, request, session, url_for

import views_admin
import views_auth
import views_biennale
import views_core
import views_proprio
import views_raccolta
from biennale import BiennaleStore
from downloads import DownloadStore
from proprio import ProprioStore
from repository import MONTHS_IT, WEEKDAYS_SHORT_IT, LiturgiaRepository
from runner import CollectorRunner
from santi import SantiStore
from users import UserStore
from youtube import YouTubeClient

PORT = 5300
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Su Vercel (e simili) il filesystem è in sola lettura: niente
# raccolte né salvataggi di Proprio/Biennale.
READ_ONLY = bool(os.environ.get("VERCEL") or os.environ.get("LC_READ_ONLY"))

logger = logging.getLogger(__name__)


def _config_values() -> dict:
    """Contenuto di config.json (vuoto se assente o illeggibile)."""
    config_path = PROJECT_ROOT / "config.json"
    if config_path.is_file():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("config.json non leggibile (%s): uso i default", exc)
    return {}


def _data_dirs() -> Tuple[Path, Path]:
    """Cartelle dei TXT e dei metadati JSON dalla config.json."""
    values = _config_values()
    output = (PROJECT_ROOT / values.get("output", "data/output")).resolve()
    json_dir = (PROJECT_ROOT / values.get("json_output", "data/json")).resolve()
    return output, json_dir


def create_app(output_dir: Optional[Path] = None,
               json_dir: Optional[Path] = None) -> Flask:
    """Application factory."""
    app = Flask(__name__, static_folder=str(PROJECT_ROOT / "static"))
    app.secret_key = "liturgia-collector"  # solo per sessione e flash

    values = _config_values()
    default_output, default_json = _data_dirs()
    proprio_store = ProprioStore(
        PROJECT_ROOT / values.get("proprio_output", "data/proprio")
    )
    biennale_store = BiennaleStore(
        PROJECT_ROOT / values.get("biennale_output", "data/biennale")
    )
    collector_runner = CollectorRunner(PROJECT_ROOT)
    user_store = UserStore(PROJECT_ROOT / "users.json")
    youtube = YouTubeClient(
        os.environ.get("YOUTUBE_API_KEY")
        or values.get("youtube_api_key", "")
    )
    download_store = DownloadStore(
        PROJECT_ROOT / values.get("downloads_log", "data/downloads.jsonl"),
        read_only=READ_ONLY,
    )
    # La cartella android/ è esclusa dal deploy, quindi l'APK pubblicato
    # è quello in data/app/; il secondo percorso vale in locale, dove si
    # può servire direttamente l'ultimo APK costruito.
    apk_paths = (
        PROJECT_ROOT / values.get("apk", "data/app/Prego.apk"),
        PROJECT_ROOT / "android" / "Prego-debug.apk",
    )
    repository = LiturgiaRepository(
        output_dir or default_output,
        json_dir or default_json,
        proprio_store=proprio_store,
        biennale_store=biennale_store,
    )

    def login_required(view):
        """Consente la vista solo agli utenti abilitati alle modifiche."""
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user"):
                flash("Accesso richiesto per questa operazione.", "danger")
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def reject_if_read_only() -> bool:
        """True (con avviso) quando il deploy è in sola lettura."""
        if READ_ONLY:
            flash("Deploy in sola lettura: operazione non disponibile.",
                  "danger")
            return True
        return False

    @app.context_processor
    def inject_globals():
        """Dati disponibili in tutti i template (sidebar, nomi mesi)."""
        return {
            "months_it": MONTHS_IT,
            "weekdays_short": WEEKDAYS_SHORT_IT,
            "sidebar_months": repository.available_months(),
            "available_days_iso": [
                day.isoformat() for day in repository.available_days()
            ],
            "today": date.today(),
            "read_only": READ_ONLY,
            # l'app Android sincronizza le pagine con User-Agent
            # "PregoAndroid/<versione>": lì le voci Scarica l'app e Accedi
            # non hanno senso e vengono nascoste
            "in_app": request.user_agent.string.startswith("PregoAndroid"),
            "current_user": session.get("user"),
            "app_version": values.get("version", "1.0"),
        }

    santi_store = SantiStore(PROJECT_ROOT / values.get("santi_output", "data/santi"))
    views_core.register(app, repository, youtube, santi_store)
    views_auth.register(app, user_store)
    views_proprio.register(app, proprio_store, login_required,
                           reject_if_read_only)
    views_biennale.register(app, biennale_store, login_required,
                            reject_if_read_only)
    views_raccolta.register(app, collector_runner, login_required,
                            reject_if_read_only)
    views_admin.register(app, download_store, apk_paths, repository,
                         proprio_store, biennale_store, user_store,
                         login_required, values.get("version", "1.0"))
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app().run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
