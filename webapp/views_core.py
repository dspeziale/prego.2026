"""Viste principali: oggi, giorno, calendario mensile, about, omelia."""

from datetime import date
from typing import Tuple

from flask import abort, redirect, render_template, request, url_for

from youtube import YouTubeError


def _month_nav(year: int, month: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """(anno, mese) precedente e successivo per la navigazione."""
    prev = (year - 1, 12) if month == 1 else (year, month - 1)
    nxt = (year + 1, 1) if month == 12 else (year, month + 1)
    return prev, nxt


def register(app, repository, youtube, santi_store=None) -> None:
    """Registra le route sull'app (endpoint invariati)."""

    @app.route("/santi/<iso>")
    def santi(iso: str):
        """Tutti i santi e beati venerati in quel giorno del calendario."""
        record = repository.day(iso, with_documents=False)
        if record is None:
            abort(404)
        elenco = santi_store.load(record.day) if santi_store is not None else None
        return render_template("santi.html", record=record, santi=elenco)

    @app.route("/")
    def index():
        """All'arrivo sul sito: la liturgia di oggi."""
        today_iso = date.today().isoformat()
        if repository.day(today_iso, with_documents=False) is not None:
            return redirect(url_for("day_view", iso=today_iso))
        return redirect(url_for("current_month"))

    @app.route("/giorno/<iso>")
    def day_view(iso: str):
        record = repository.day(iso)
        if record is None:
            abort(404)
        return render_template("day.html", record=record)

    @app.route("/mese/<int:year>/<int:month>")
    def month_view(year: int, month: int):
        if not 1 <= month <= 12:
            abort(404)
        prev_month, next_month = _month_nav(year, month)
        return render_template(
            "month.html",
            year=year,
            month=month,
            weeks=repository.month_grid(year, month),
            prev_month=prev_month,
            next_month=next_month,
        )

    @app.route("/mese/corrente")
    def current_month():
        today = date.today()
        return redirect(url_for("month_view", year=today.year, month=today.month))

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/impostazioni")
    def impostazioni():
        """Preferenze del lettore: vivono in localStorage del dispositivo,
        così valgono anche nelle pagine sincronizzate dall'app."""
        return render_template("impostazioni.html")

    @app.route("/api/giorni")
    def api_giorni():
        """Elenco delle giornate disponibili (per l'app Android)."""
        giorni = [day.isoformat() for day in repository.available_days()]
        return {"giorni": giorni, "totale": len(giorni)}

    @app.route("/omelia/<iso>")
    def omelia(iso: str):
        record = repository.day(iso, with_documents=False)
        if record is None:
            abort(404)
        default_query = (
            record.metadata.get("celebrazione")
            or record.metadata.get("santo_del_giorno")
            or iso
        )
        query = (request.args.get("q") or "").strip() or default_query
        videos, error, notice = [], None, None
        if not youtube.enabled:
            error = (
                "Chiave API YouTube non configurata: impostare "
                "'youtube_api_key' in config.json oppure la variabile "
                "d'ambiente YOUTUBE_API_KEY."
            )
        else:
            try:
                videos, exact = youtube.search(query)
                if videos and not exact:
                    notice = (
                        f"Nessun video trovato per «{query}»: "
                        "probabilmente l'omelia non è ancora stata "
                        "pubblicata. Ecco gli ultimi video del canale."
                    )
            except YouTubeError as exc:
                error = str(exc)
        return render_template(
            "omelia.html",
            record=record, query=query, videos=videos,
            error=error, notice=notice,
        )

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404
