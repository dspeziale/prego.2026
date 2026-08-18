"""Esecuzione della raccolta dal sito CEI via interfaccia web."""

from flask import flash, jsonify, redirect, render_template, request, url_for


def register(app, collector_runner, login_required, reject_if_read_only) -> None:
    """Registra le route sull'app (endpoint invariati)."""

    @app.route("/raccolta")
    @login_required
    def raccolta():
        return render_template(
            "raccolta.html", status=collector_runner.status()
        )

    @app.route("/raccolta/avvia", methods=["POST"])
    @login_required
    def raccolta_avvia():
        if reject_if_read_only():
            return redirect(url_for("raccolta"))
        mode = request.form.get("modo", "oggi")
        args: list = []
        if mode == "data":
            value = (request.form.get("data") or "").strip()
            if not value:
                flash("Indicare la data da raccogliere.", "danger")
                return redirect(url_for("raccolta"))
            args = [value]
        elif mode == "intervallo":
            start = (request.form.get("dal") or "").strip()
            end = (request.form.get("al") or "").strip()
            if not start or not end:
                flash("Indicare inizio e fine dell'intervallo.", "danger")
                return redirect(url_for("raccolta"))
            args = [f"{start}..{end}"]
        if collector_runner.start(args):
            flash("Raccolta avviata.", "success")
        else:
            flash("Una raccolta è già in corso: attendere.", "danger")
        return redirect(url_for("raccolta"))

    @app.route("/raccolta/stato")
    def raccolta_stato():
        return jsonify(collector_runner.status())
