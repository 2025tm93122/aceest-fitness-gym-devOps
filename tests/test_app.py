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


def test_health(client):
    assert client.get("/health").get_json() == {"status": "healthy"}


def test_save_client_persists_and_calculates_calories(client, app_module):
    response = client.post(
        "/",
        data={
            "action": "save",
            "name": "Nia",
            "age": "25",
            "weight": "60",
            "program": "Fat Loss (FL)",
        },
    )
    assert response.status_code == 200
    assert "Client data saved" in response.get_data(as_text=True)
    connection = app_module.get_conn()
    row = connection.execute("SELECT * FROM clients WHERE name=?", ("Nia",)).fetchone()
    connection.close()
    assert row is not None
    assert row["calories"] == 1320


def test_save_weekly_progress(client, app_module):
    response = client.post(
        "/",
        data={"action": "progress", "name": "Nia", "adherence": "88"},
    )
    assert response.status_code == 200
    assert "Weekly progress logged" in response.get_data(as_text=True)
    connection = app_module.get_conn()
    row = connection.execute(
        "SELECT client_name, adherence FROM progress ORDER BY id DESC LIMIT 1"
    ).fetchone()
    connection.close()
    assert row["client_name"] == "Nia"
    assert row["adherence"] == 88


def test_client_name_and_program_are_required(client):
    response = client.post("/", data={"action": "save", "name": "", "program": ""})
    assert response.status_code == 200
    assert "Name and Program required" in response.get_data(as_text=True)
