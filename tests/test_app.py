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


def test_save_client_adds_to_client_list(client, app_module):
    response = client.post(
        "/",
        data={
            "name": "Nia",
            "age": "25",
            "weight": "60",
            "program": "Fat Loss (FL)",
            "adherence": "90",
            "notes": "Consistent training",
        },
    )
    assert response.status_code == 200
    assert "Client Nia saved successfully" in response.get_data(as_text=True)
    assert len(app_module.clients) == 1
    assert app_module.clients[0][0] == "Nia"
    assert app_module.clients[0][4] == 90


def test_export_csv_contains_saved_client(client):
    client.post(
        "/",
        data={
            "name": "Nia",
            "age": "25",
            "weight": "60",
            "program": "Beginner (BG)",
            "adherence": "75",
            "notes": "Week one",
        },
    )
    response = client.get("/export.csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    csv_text = response.get_data(as_text=True)
    assert "Name,Age,Weight,Program,Adherence,Notes" in csv_text
    assert "Nia,25,60.0,Beginner (BG),75,Week one" in csv_text


def test_reset_clears_clients(client, app_module):
    app_module.clients.append(("Nia", 25, 60.0, "Beginner (BG)", 75, ""))
    response = client.get("/reset")
    assert response.status_code == 200
    assert app_module.clients == []
    assert "Client list reset" in response.get_data(as_text=True)


def test_invalid_numeric_input_is_handled(client):
    response = client.post(
        "/",
        data={"name": "Nia", "age": "abc", "program": "Beginner (BG)"},
    )
    assert response.status_code == 200
    assert "must be numeric" in response.get_data(as_text=True)
