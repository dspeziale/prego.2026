"""Gestione del Proprio (letture proprie dei santi)."""

from flask import abort, flash, redirect, render_template, request, url_for

from proprio import RANKS, READING_LABELS, ProprioStore


def register(app, proprio_store, login_required, reject_if_read_only) -> None:
    """Registra le route sull'app (endpoint invariati)."""

    @app.route("/proprio")
    def proprio_list():
        return render_template(
            "proprio_list.html", entries=proprio_store.list_entries()
        )

    @app.route("/proprio/nuovo")
    @login_required
    def proprio_new():
        return render_template(
            "proprio_form.html",
            entry=None, ranks=RANKS, reading_labels=READING_LABELS,
        )

    @app.route("/proprio/<code>/modifica")
    @login_required
    def proprio_edit(code: str):
        entry = proprio_store.load(code)
        if entry is None:
            abort(404)
        return render_template(
            "proprio_form.html",
            entry=entry, ranks=RANKS, reading_labels=READING_LABELS,
        )

    @app.route("/proprio/salva", methods=["POST"])
    @login_required
    def proprio_save():
        if reject_if_read_only():
            return redirect(url_for("proprio_list"))
        try:
            entry = ProprioStore.from_form(request.form)
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("proprio_new"))
        proprio_store.save(entry)
        flash(f"Salvato {entry['data_estesa']} — {entry['santo']}", "success")
        return redirect(url_for("proprio_list"))

    @app.route("/proprio/<code>/elimina", methods=["POST"])
    @login_required
    def proprio_delete(code: str):
        if reject_if_read_only():
            return redirect(url_for("proprio_list"))
        if proprio_store.delete(code):
            flash(f"Eliminata la ricorrenza {code}.", "success")
        else:
            flash(f"Ricorrenza {code} non trovata.", "danger")
        return redirect(url_for("proprio_list"))
