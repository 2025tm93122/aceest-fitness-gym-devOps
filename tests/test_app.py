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


def create_client(client):
    return client.post(
        "/api/clients",
        json={
            "name": "Nia",
            "age": 25,
            "height": 165,
            "weight": 60,
            "program": "Fat Loss (FL) – 3 day",
            "target_weight": 55,
            "target_adherence": 90,
        },
    )


def test_health(client):
    assert client.get("/health").get_json() == {"status": "healthy"}


def test_create_and_fetch_client(client):
    response = create_client(client)
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Nia"
    assert data["calories"] == 1320
    fetched = client.get("/api/clients/Nia")
    assert fetched.status_code == 200
    assert fetched.get_json()["target_adherence"] == 90


def test_progress_workout_and_metrics_apis(client):
    create_client(client)
    progress = client.post("/progress", json={"client_name": "Nia", "adherence": 87})
    assert progress.status_code == 201
    workout = client.post(
        "/workout",
        json={
            "client_name": "Nia",
            "date": "2026-10-11",
            "workout_type": "Strength",
            "duration_min": 60,
            "notes": "Good session",
            "exercise_name": "Squat",
            "sets": 3,
            "reps": 10,
            "exercise_weight": 40,
        },
    )
    assert workout.status_code == 201
    metrics = client.post(
        "/metrics",
        json={
            "client_name": "Nia",
            "date": "2026-10-11",
            "weight": 60,
            "waist": 75,
            "bodyfat": 22,
        },
    )
    assert metrics.status_code == 201
    assert client.get("/api/progress/Nia").get_json()[0]["adherence"] == 87
    assert client.get("/api/workouts/Nia").get_json()[0]["workout_type"] == "Strength"
    assert client.get("/api/metrics/Nia").get_json()[0]["waist"] == 75.0


def test_bmi_for_saved_client(client):
    create_client(client)
    response = client.get("/api/bmi/Nia")
    assert response.status_code == 200
    data = response.get_json()
    assert data["client"] == "Nia"
    assert data["bmi"] == 22.0
    assert data["category"] == "Normal"


def test_invalid_client_payload_is_rejected(client):
    response = client.post("/api/clients", json={"name": "Nia", "program": "Unknown"})
    assert response.status_code == 400
