"""Autenticazione degli utenti abilitati alle modifiche."""

from flask import flash, redirect, render_template, request, session, url_for


def register(app, user_store) -> None:
    """Registra le route sull'app (endpoint invariati)."""

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            if user_store.verify(username, password):
                session["user"] = username.strip()
                flash(f"Benvenuto, {session['user']}.", "success")
                target = request.args.get("next") or url_for("index")
                return redirect(target)
            flash("Credenziali non valide.", "danger")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.pop("user", None)
        flash("Sessione chiusa.", "success")
        return redirect(url_for("index"))
