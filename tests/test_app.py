import importlib
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    """Load the current repository app.py with an isolated test database."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "aceest_test.db"))
    sys.modules.pop("app", None)
    module = importlib.import_module("app")

    if hasattr(module, "DB_NAME"):
        module.DB_NAME = str(tmp_path / "aceest_test.db")
    if hasattr(module, "init_db"):
        module.init_db()
    if hasattr(module, "clients"):
        module.clients.clear()

    module.app.config.update(TESTING=True, SECRET_KEY="pytest-secret")
    yield module
    sys.modules.pop("app", None)


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()
def login(client):
    return client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )


def test_health(client):
    assert client.get("/health").get_json() == {"status": "healthy"}


def test_admin_login(client):
    response = login(client)
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_client_membership_workout_program_and_pdf_flow(client, app_module):
    login(client)
    saved = client.post(
        "/client",
        data={
            "name": "Nia",
            "age": "25",
            "height": "165",
            "weight": "60",
            "program": "Fat Loss",
            "target_weight": "55",
            "target_adherence": "90",
            "membership_status": "Active",
            "membership_end": "2027-01-01",
        },
    )
    assert saved.status_code == 302

    connection = app_module.get_connection()
    row = connection.execute("SELECT * FROM clients WHERE name=?", ("Nia",)).fetchone()
    connection.close()
    assert row["membership_status"] == "Active"
    assert row["membership_end"] == "2027-01-01"

    workout = client.post(
        "/workout",
        data={
            "client_name": "Nia",
            "date": "2026-10-11",
            "workout_type": "Strength",
            "duration_min": "60",
            "notes": "Squats",
        },
    )
    assert workout.status_code == 302

    membership = client.get("/membership?client_name=Nia")
    assert membership.status_code == 200
    membership_page = membership.get_data(as_text=True)
    assert "Membership: Active" in membership_page
    assert "2027-01-01" in membership_page

    generated = client.get("/generate?client_name=Nia")
    assert generated.status_code == 200
    assert "Program Generated" in generated.get_data(as_text=True)

    report = client.get("/report?client_name=Nia")
    assert report.status_code == 200
    assert report.mimetype == "application/pdf"
    assert report.data.startswith(b"%PDF")


def test_unauthenticated_dashboard_redirects_to_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
