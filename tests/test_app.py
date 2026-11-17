import unittest
from datetime import date
from contextlib import closing
import os
import sqlite3
import tempfile
from unittest.mock import patch

from app import app


class BookingPageTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        app.config["DATABASE"] = self.database_path
        self.addCleanup(self.temp_dir.cleanup)
        environment = patch.dict(
            os.environ,
            {
                "STUDIO_INITIAL_USERNAME": "test-user",
                "STUDIO_INITIAL_PASSWORD": "test-password",
            },
        )
        environment.start()
        self.addCleanup(environment.stop)
        self.client = app.test_client()

    def login(self):
        return self.client.post(
            "/", data={"name": "test-user", "password": "test-password"}
        )

    def test_homepage_renders_login_form(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Seja bem-vindo!", response.data)
        self.assertIn(b'name="password"', response.data)
        self.assertIn(b"Studio Fl\xc3\xa1vio Celso", response.data)

    def test_valid_login_opens_booking_page(self):
        response = self.login()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/agendamento")
        booking_response = self.client.get("/agendamento")
        self.assertIn(b"Marque seu hor\xc3\xa1rio", booking_response.data)
        self.assertIn(b'id="barber"', booking_response.data)
        self.assertIn(b"Fl\xc3\xa1vio", booking_response.data)
        self.assertIn(b'name="service_optional_1"', booking_response.data)
        self.assertIn(b'name="service_optional_2"', booking_response.data)

    def test_invalid_login_shows_error(self):
        response = self.client.post(
            "/", data={"name": "test-user", "password": "wrong"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Nome ou senha incorretos", response.data)

    def test_database_initializes_catalog_and_demo_user(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        with closing(sqlite3.connect(self.database_path)) as db:
            barber_count = db.execute("SELECT COUNT(*) FROM barbers").fetchone()[0]
            service_count = db.execute("SELECT COUNT(*) FROM services").fetchone()[0]
            user = db.execute(
                "SELECT username, password_hash FROM users WHERE username = ?",
                ("test-user",),
            ).fetchone()

        self.assertEqual(barber_count, 3)
        self.assertEqual(service_count, 4)
        self.assertEqual(user[0], "test-user")
        self.assertNotEqual(user[1], "test-password")

    def test_booking_requires_login(self):
        response = self.client.get("/agendamento")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

    def test_valid_booking_displays_submission_message(self):
        self.login()
        response = self.client.post(
            "/agendamento",
            data={
                "date": date.today().isoformat(),
                "time": "14:00",
                "barber": "flavio",
                "service": "fade",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pedido enviado", response.data)
        self.assertIn(b"com Fl\xc3\xa1vio", response.data)
        self.assertIn(b"Corte Degrad", response.data)
        self.assertIn(b"Total: R$ 35,00", response.data)
        with closing(sqlite3.connect(self.database_path)) as db:
            appointment = db.execute(
                "SELECT appointment_date, appointment_time, barber_id, total_cents "
                "FROM appointments"
            ).fetchone()
            saved_services = db.execute(
                "SELECT service_id, price_cents FROM appointment_services"
            ).fetchall()

        self.assertEqual(
            appointment,
            (date.today().isoformat(), "14:00", "flavio", 3500),
        )
        self.assertEqual(saved_services, [("fade", 3500)])

    def test_booking_accepts_three_distinct_services(self):
        self.login()
        response = self.client.post(
            "/agendamento",
            data={
                "date": date.today().isoformat(),
                "time": "14:00",
                "barber": "ricardo",
                "service": "fade",
                "service_optional_1": "social",
                "service_optional_2": "barba",
            },
        )

        self.assertIn(b"com Ricardo", response.data)
        self.assertIn(b"Corte Degrad", response.data)
        self.assertIn(b"Corte Social", response.data)
        self.assertIn(b"Barba", response.data)
        self.assertIn(b"Total: R$ 90,00", response.data)

    def test_duplicate_services_are_rejected(self):
        self.login()
        response = self.client.post(
            "/agendamento",
            data={
                "date": date.today().isoformat(),
                "time": "14:00",
                "barber": "anderson",
                "service": "fade",
                "service_optional_1": "fade",
            },
        )

        self.assertIn(b"mesmo servi", response.data)

    def test_eyebrow_service_can_be_selected(self):
        self.login()
        response = self.client.post(
            "/agendamento",
            data={
                "date": date.today().isoformat(),
                "time": "14:00",
                "barber": "anderson",
                "service": "sobrancelha",
            },
        )

        self.assertIn(b"Sobrancelha - R$ 15,00", response.data)
        self.assertIn(b"Total: R$ 15,00", response.data)

    def test_invalid_barber_is_rejected(self):
        self.login()
        response = self.client.post(
            "/agendamento",
            data={
                "date": date.today().isoformat(),
                "time": "14:00",
                "barber": "unknown",
                "service": "fade",
            },
        )

        self.assertIn(b"barbeiro v", response.data)

    def test_unavailable_time_is_rejected(self):
        self.login()
        response = self.client.post(
            "/agendamento",
            data={
                "date": date.today().isoformat(),
                "time": "12:30",
                "barber": "flavio",
                "service": "fade",
            },
        )

        self.assertIn(b"Selecione um dos hor", response.data)

    def test_logout_returns_to_login_and_protects_booking(self):
        self.login()
        response = self.client.post("/sair")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        self.assertEqual(self.client.get("/agendamento").status_code, 302)


if __name__ == "__main__":
    unittest.main()
