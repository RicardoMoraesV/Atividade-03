from datetime import date
import os
import secrets
import sqlite3

from dotenv import load_dotenv
from flask import Flask, current_app, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["DATABASE"] = os.path.join(app.instance_path, "studio.sqlite3")

AVAILABLE_TIMES = ("09:00", "10:00", "14:00", "15:00")


def get_db():
    if "db" not in g:
        database_path = current_app.config["DATABASE"]
        database_directory = os.path.dirname(database_path)
        if database_directory:
            os.makedirs(database_directory, exist_ok=True)

        db = sqlite3.connect(database_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        g.db = db

    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, encoding="utf-8") as schema_file:
        db.executescript(schema_file.read())

    if db.execute("SELECT 1 FROM users LIMIT 1").fetchone() is None:
        initial_password = os.environ.get("STUDIO_INITIAL_PASSWORD")
        if not initial_password:
            raise RuntimeError(
                "Configure STUDIO_INITIAL_PASSWORD no arquivo .env "
                "antes de inicializar o banco."
            )

        initial_username = os.environ.get("STUDIO_INITIAL_USERNAME", "123")
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (initial_username, generate_password_hash(initial_password)),
        )
    db.commit()


@app.before_request
def ensure_database():
    database_path = current_app.config["DATABASE"]
    if current_app.extensions.get("studio_database_path") != database_path:
        init_db()
        current_app.extensions["studio_database_path"] = database_path


def format_price(price_cents):
    return f"R$ {price_cents // 100},{price_cents % 100:02d}"


@app.route("/", methods=("GET", "POST"))
def login():
    error = None

    if request.method == "POST":
        name = request.form.get("name", "")
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT id, password_hash FROM users WHERE username = ? AND active = 1",
            (name,),
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("booking"))

        error = "Nome ou senha incorretos."

    return render_template("index.html", error=error)


@app.route("/agendamento", methods=("GET", "POST"))
def booking():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    db = get_db()
    barber_rows = db.execute(
        "SELECT id, name FROM barbers WHERE active = 1 ORDER BY name"
    ).fetchall()
    service_rows = db.execute(
        "SELECT id, name, price_cents FROM services "
        "WHERE active = 1 ORDER BY name"
    ).fetchall()
    barbers = {row["id"]: row["name"] for row in barber_rows}
    service_prices = {row["id"]: row["price_cents"] for row in service_rows}
    services = {
        row["id"]: f"{row['name']} - {format_price(row['price_cents'])}"
        for row in service_rows
    }

    today = date.today()
    date_value = today.isoformat()
    time_value = "14:00"
    barber_value = "flavio" if "flavio" in barbers else next(iter(barbers), "")
    default_service = "fade" if "fade" in services else next(iter(services), "")
    service_values = [default_service, "", ""]
    message = None
    error = None

    if request.method == "POST":
        date_value = request.form.get("date", "")
        time_value = request.form.get("time", "")
        barber_value = request.form.get("barber", "")
        service_values = [
            request.form.get("service", ""),
            request.form.get("service_optional_1", ""),
            request.form.get("service_optional_2", ""),
        ]
        selected_services = [service for service in service_values if service]

        try:
            appointment_date = date.fromisoformat(date_value)
        except ValueError:
            error = "Selecione uma data válida."
        else:
            if appointment_date < today:
                error = "A data do agendamento não pode estar no passado."
            elif time_value not in AVAILABLE_TIMES:
                error = "Selecione um dos horários disponíveis."
            elif barber_value not in barbers:
                error = "Selecione um barbeiro válido."
            elif not service_values[0] or any(
                service not in services for service in selected_services
            ):
                error = "Selecione ao menos um serviço válido."
            elif len(selected_services) != len(set(selected_services)):
                error = "Não selecione o mesmo serviço mais de uma vez."
            else:
                service_names = ", ".join(
                    services[service] for service in selected_services
                )
                total_cents = sum(
                    service_prices[service] for service in selected_services
                )
                with db:
                    cursor = db.execute(
                        """
                        INSERT INTO appointments
                            (user_id, appointment_date, appointment_time, barber_id, total_cents)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            appointment_date.isoformat(),
                            time_value,
                            barber_value,
                            total_cents,
                        ),
                    )
                    appointment_id = cursor.lastrowid
                    db.executemany(
                        """
                        INSERT INTO appointment_services
                            (appointment_id, service_id, price_cents)
                        VALUES (?, ?, ?)
                        """,
                        [
                            (appointment_id, service, service_prices[service])
                            for service in selected_services
                        ],
                    )

                message = (
                    f"Pedido enviado para {appointment_date.strftime('%d/%m/%Y')} "
                    f"às {time_value} com {barbers[barber_value]}. "
                    f"Serviços: {service_names}. "
                    f"Total: {format_price(total_cents)}."
                )

    return render_template(
        "booking.html",
        today=today.isoformat(),
        date_value=date_value,
        time_value=time_value,
        barber_value=barber_value,
        service_values=service_values,
        times=AVAILABLE_TIMES,
        barbers=barbers,
        services=services,
        message=message,
        error=error,
    )


@app.route("/sair", methods=("POST",))
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
