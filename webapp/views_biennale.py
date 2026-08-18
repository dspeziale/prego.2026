"""Gestione del lezionario Biennale."""

from flask import abort, flash, redirect, render_template, request, url_for

from biennale import (
    BIENNALE_READING_LABELS, CYCLES, ROMAN_WEEKS, SEASONS, WEEKDAYS, YEARS,
    BiennaleStore,
)


def _form_context(entry):
    return {
        "entry": entry,
        "seasons": SEASONS,
        "weeks": ROMAN_WEEKS,
        "weekdays": WEEKDAYS,
        "years": YEARS,
        "cycles": CYCLES,
        "reading_labels": BIENNALE_READING_LABELS,
    }


def register(app, biennale_store, login_required, reject_if_read_only) -> None:
    """Registra le route sull'app (endpoint invariati)."""

    @app.route("/biennale")
    def biennale_list():
        return render_template(
            "biennale_list.html", entries=biennale_store.list_entries()
        )

    @app.route("/biennale/nuovo")
    @login_required
    def biennale_new():
        return render_template("biennale_form.html", **_form_context(None))

    @app.route("/biennale/<code>/modifica")
    @login_required
    def biennale_edit(code: str):
        entry = biennale_store.load(code)
        if entry is None:
            abort(404)
        return render_template("biennale_form.html", **_form_context(entry))

    @app.route("/biennale/salva", methods=["POST"])
    @login_required
    def biennale_save():
        if reject_if_read_only():
            return redirect(url_for("biennale_list"))
        try:
            entry = BiennaleStore.from_form(request.form)
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("biennale_new"))
        biennale_store.save(entry)
        flash(f"Salvato {entry['codice']}.json", "success")
        return redirect(url_for("biennale_list"))

    @app.route("/biennale/<code>/elimina", methods=["POST"])
    @login_required
    def biennale_delete(code: str):
        if reject_if_read_only():
            return redirect(url_for("biennale_list"))
        if biennale_store.delete(code):
            flash(f"Eliminato {code}.", "success")
        else:
            flash(f"Voce {code} non trovata.", "danger")
        return redirect(url_for("biennale_list"))
