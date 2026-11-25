"""Aplicación deliberadamente vulnerable para la evaluación OCY1102 EV3.

Solo debe ejecutarse en el laboratorio local. El alumnado debe revisar y corregir
los defectos; estos comentarios no enumeran las respuestas de la evaluación.
"""

import os
import sqlite3
import time
from pathlib import Path

from flask import Flask, abort, g, redirect, render_template, request, session, url_for
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from werkzeug.security import check_password_hash, generate_password_hash


HTTP_REQUESTS = Counter(
    "securedev_http_requests_total",
    "Solicitudes HTTP de la aplicación",
    ["endpoint", "method", "status"],
)
HTTP_DURATION = Histogram(
    "securedev_http_request_duration_seconds",
    "Duración de solicitudes HTTP",
    ["endpoint"],
)
LOGIN_FAILURES = Counter(
    "securedev_login_failures_total",
    "Intentos de acceso fallidos",
)


def create_app(database_path=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave-insegura-solo-laboratorio")
    app.config["DATABASE_PATH"] = str(
        database_path or os.getenv("DATABASE_PATH", str(Path(__file__).with_name("securedev.db")))
    )

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_error):
        connection = g.pop("db", None)
        if connection is not None:
            connection.close()

    @app.before_request
    def start_request_timer():
        g.request_started_at = time.perf_counter()

    @app.after_request
    def record_request(response):
        if request.endpoint != "metrics":
            endpoint = request.endpoint or "unknown"
            HTTP_REQUESTS.labels(endpoint, request.method, str(response.status_code)).inc()
            HTTP_DURATION.labels(endpoint).observe(time.perf_counter() - g.request_started_at)
        return response

    with app.app_context():
        Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)
        connection = db()
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY,
                owner_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY,
                ticket_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                body TEXT NOT NULL
            );
            """
        )
        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
                [
                    (1, "ana", generate_password_hash("ana123")),
                    (2, "bruno", generate_password_hash("bruno123")),
                ],
            )
            connection.executemany(
                "INSERT INTO tickets (id, owner_id, title, body) VALUES (?, ?, ?, ?)",
                [
                    (1, 1, "Revisión de despliegue", "Preparar evidencias de CI/CD."),
                    (2, 2, "Acceso al panel", "Revisar registros de acceso."),
                ],
            )
        connection.commit()

    def current_user():
        return session.get("user_id")

    @app.route("/")
    def index():
        if not current_user():
            return redirect(url_for("login"))
        tickets = db().execute(
            "SELECT id, title FROM tickets WHERE owner_id = ? ORDER BY id", (current_user(),)
        ).fetchall()
        return render_template("index.html", tickets=tickets)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            user = db().execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?", (username,)
            ).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                return redirect(url_for("index"))
            LOGIN_FAILURES.inc()
            error = "Credenciales inválidas"
        return render_template("login.html", error=error)

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/tickets/<int:ticket_id>")
    def ticket(ticket_id):
        if not current_user():
            return redirect(url_for("login"))
        item = db().execute(
            "SELECT id, owner_id, title, body FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if item is None:
            abort(404)
        comments = db().execute(
            "SELECT body FROM comments WHERE ticket_id = ? ORDER BY id", (ticket_id,)
        ).fetchall()
        return render_template("ticket.html", ticket=item, comments=comments)

    @app.post("/tickets/<int:ticket_id>/comments")
    def add_comment(ticket_id):
        if not current_user():
            return redirect(url_for("login"))
        if db().execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            abort(404)
        body = request.form.get("body", "")
        db().execute(
            "INSERT INTO comments (ticket_id, author_id, body) VALUES (?, ?, ?)",
            (ticket_id, current_user(), body),
        )
        db().commit()
        return redirect(url_for("ticket", ticket_id=ticket_id))

    @app.get("/search")
    def search():
        if not current_user():
            return redirect(url_for("login"))
        query = request.args.get("q", "")
        sql = f"SELECT id, title FROM tickets WHERE title LIKE '%{query}%' ORDER BY id"
        tickets = db().execute(sql).fetchall()
        return render_template("search.html", tickets=tickets, query=query)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics():
        return app.response_class(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=8000)
