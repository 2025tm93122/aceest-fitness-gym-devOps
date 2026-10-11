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


def test_save_client_and_progress_chart(client, app_module):
    save = client.post(
        "/",
        data={
            "action": "save",
            "name": "Nia",
            "age": "25",
            "weight": "60",
            "program": "Fat Loss (FL)",
        },
    )
    assert save.status_code == 200
    progress = client.post(
        "/", data={"action": "progress", "name": "Nia", "adherence": "82"}
    )
    assert progress.status_code == 200
    page = progress.get_data(as_text=True)
    assert "Weekly progress logged" in page
    assert "<svg" in page
    assert "82%" in page
    connection = app_module.conn()
    row = connection.execute("SELECT adherence FROM progress ORDER BY id DESC LIMIT 1").fetchone()
    connection.close()
    assert row["adherence"] == 82


def test_empty_progress_has_friendly_message(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "No progress data available" in response.get_data(as_text=True)
