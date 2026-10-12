import importlib
from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    """Load app.py with an isolated SQLite database."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(
        "DATABASE_PATH",
        str(tmp_path / "aceest_test.db"),
    )

    sys.modules.pop("app", None)

    module = importlib.import_module("app")

    module.DB_NAME = str(tmp_path / "aceest_test.db")
    module.init_db()

    module.app.config.update(
        TESTING=True,
        SECRET_KEY="pytest-secret",
    )

    yield module

    sys.modules.pop("app", None)


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


def create_client(client, name="Nia"):
    return client.post(
        "/api/clients",
        json={
            "name": name,
            "age": 25,
            "height": 165,
            "weight": 60,
            "program": "Fat Loss (FL) – 3 day",
            "target_weight": 55,
            "target_adherence": 90,
        },
    )


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

def test_dashboard_empty(client):
    response = client.get("/")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "ACEest Functional Fitness System" in page
    assert "Client Management" in page
    assert "Weekly Progress" in page
    assert "Workout Logging" in page
    assert "Body Metrics" in page
    assert "BMI" in page
    assert "No progress data" in page


def test_dashboard_with_data(client):
    create_client(client)

    client.post(
        "/progress",
        json={
            "client_name": "Nia",
            "adherence": 87,
        },
    )

    client.post(
        "/workout",
        json={
            "client_name": "Nia",
            "date": "2026-10-12",
            "workout_type": "Strength",
            "duration_min": 60,
            "notes": "Good session",
            "exercise_name": "Squat",
            "sets": 3,
            "reps": 10,
            "exercise_weight": 40,
        },
    )

    client.post(
        "/metrics",
        json={
            "client_name": "Nia",
            "date": "2026-10-12",
            "weight": 60,
            "waist": 75,
            "bodyfat": 22,
        },
    )

    response = client.get("/")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Nia" in page
    assert "87%" in page
    assert "Strength" in page
    assert "Good session" in page
    assert "75.0" in page


# ---------------------------------------------------------
# Client API
# ---------------------------------------------------------

def test_create_and_fetch_client(client):
    response = create_client(client)

    assert response.status_code == 201

    data = response.get_json()

    assert data["name"] == "Nia"
    assert data["age"] == 25
    assert data["height"] == 165
    assert data["weight"] == 60
    assert data["calories"] == 1320
    assert data["target_weight"] == 55
    assert data["target_adherence"] == 90

    fetched = client.get("/api/clients/Nia")

    assert fetched.status_code == 200
    assert fetched.get_json()["name"] == "Nia"


def test_list_clients(client):
    create_client(client)

    response = client.get("/api/clients")

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["name"] == "Nia"


def test_missing_client_returns_404(client):
    response = client.get("/api/clients/Unknown")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Client not found"


def test_missing_name_rejected(client):
    response = client.post(
        "/api/clients",
        json={
            "program": "Fat Loss (FL) – 3 day",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Name is required"


def test_invalid_program_rejected(client):
    response = client.post(
        "/api/clients",
        json={
            "name": "Nia",
            "program": "Unknown",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Valid program is required"


# ---------------------------------------------------------
# HTML Client Form
# ---------------------------------------------------------

def test_save_client_form(client):
    response = client.post(
        "/",
        data={
            "name": "Nia",
            "age": "25",
            "height": "165",
            "weight": "60",
            "program": "Fat Loss (FL) – 3 day",
            "target_weight": "55",
            "target_adherence": "90",
        },
    )

    assert response.status_code == 302

    response = client.get("/")

    assert response.status_code == 200
    assert "Nia" in response.get_data(as_text=True)


def test_invalid_client_form(client):
    response = client.post(
        "/",
        data={
            "name": "",
            "program": "Unknown",
        },
    )

    assert response.status_code == 400
    assert "Name and a valid program are required" in response.get_data(
        as_text=True
    )


# ---------------------------------------------------------
# Progress
# ---------------------------------------------------------

def test_progress_api(client):
    create_client(client)

    response = client.post(
        "/progress",
        json={
            "client_name": "Nia",
            "adherence": 87,
        },
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["message"] == "Weekly progress logged"
    assert data["client_name"] == "Nia"
    assert data["adherence"] == 87

    progress = client.get("/api/progress/Nia")

    assert progress.status_code == 200
    assert progress.get_json()[0]["adherence"] == 87


def test_progress_missing_client_name(client):
    response = client.post(
        "/progress",
        json={
            "adherence": 80,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "client_name is required"


def test_progress_form_redirect(client):
    create_client(client)

    response = client.post(
        "/progress",
        data={
            "client_name": "Nia",
            "adherence": "80",
        },
    )

    assert response.status_code == 302


# ---------------------------------------------------------
# Workout
# ---------------------------------------------------------

def test_workout_api(client):
    create_client(client)

    response = client.post(
        "/workout",
        json={
            "client_name": "Nia",
            "date": "2026-10-12",
            "workout_type": "Strength",
            "duration_min": 60,
            "notes": "Good session",
            "exercise_name": "Squat",
            "sets": 3,
            "reps": 10,
            "exercise_weight": 40,
        },
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["message"] == "Workout logged successfully"
    assert data["workout_id"] > 0

    workouts = client.get("/api/workouts/Nia")

    assert workouts.status_code == 200
    assert workouts.get_json()[0]["workout_type"] == "Strength"


def test_workout_without_exercise(client):
    create_client(client)

    response = client.post(
        "/workout",
        json={
            "client_name": "Nia",
            "date": "2026-10-12",
            "workout_type": "Mobility",
            "duration_min": 30,
            "notes": "",
        },
    )

    assert response.status_code == 201


def test_invalid_workout(client):
    response = client.post(
        "/workout",
        json={
            "client_name": "",
            "workout_type": "",
        },
    )

    assert response.status_code == 400

    assert (
        response.get_json()["error"]
        == "client_name and workout_type are required"
    )


def test_workout_form_redirect(client):
    create_client(client)

    response = client.post(
        "/workout",
        data={
            "client_name": "Nia",
            "date": "2026-10-12",
            "workout_type": "Strength",
            "duration_min": "45",
            "notes": "Form workout",
            "exercise_name": "",
        },
    )

    assert response.status_code == 302


# ---------------------------------------------------------
# Metrics
# ---------------------------------------------------------

def test_metrics_api(client):
    create_client(client)

    response = client.post(
        "/metrics",
        json={
            "client_name": "Nia",
            "date": "2026-10-12",
            "weight": 60,
            "waist": 75,
            "bodyfat": 22,
        },
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["message"] == "Metrics logged successfully"

    metrics = client.get("/api/metrics/Nia")

    assert metrics.status_code == 200
    assert metrics.get_json()[0]["weight"] == 60.0
    assert metrics.get_json()[0]["waist"] == 75.0
    assert metrics.get_json()[0]["bodyfat"] == 22.0


def test_metrics_missing_client(client):
    response = client.post(
        "/metrics",
        json={
            "weight": 60,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "client_name is required"


def test_metrics_form_redirect(client):
    create_client(client)

    response = client.post(
        "/metrics",
        data={
            "client_name": "Nia",
            "date": "2026-10-12",
            "weight": "60",
            "waist": "75",
            "bodyfat": "22",
        },
    )

    assert response.status_code == 302


# ---------------------------------------------------------
# BMI
# ---------------------------------------------------------

def test_calculate_bmi_normal(app_module):
    result = app_module.calculate_bmi(165, 60)

    assert result["bmi"] == 22.0
    assert result["category"] == "Normal"


def test_calculate_bmi_underweight(app_module):
    result = app_module.calculate_bmi(180, 50)

    assert result["category"] == "Underweight"


def test_calculate_bmi_overweight(app_module):
    result = app_module.calculate_bmi(170, 80)

    assert result["category"] == "Overweight"


def test_calculate_bmi_obese(app_module):
    result = app_module.calculate_bmi(160, 90)

    assert result["category"] == "Obese"


def test_calculate_bmi_invalid(app_module):
    assert app_module.calculate_bmi(0, 60) is None
    assert app_module.calculate_bmi(165, 0) is None


def test_bmi_for_saved_client(client):
    create_client(client)

    response = client.get("/api/bmi/Nia")

    assert response.status_code == 200

    data = response.get_json()

    assert data["client"] == "Nia"
    assert data["bmi"] == 22.0
    assert data["category"] == "Normal"


def test_bmi_unknown_client(client):
    response = client.get("/api/bmi/Unknown")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Client not found"


def test_bmi_client_with_invalid_dimensions(client):
    client.post(
        "/api/clients",
        json={
            "name": "NoDimensions",
            "program": "Beginner (BG)",
            "height": 0,
            "weight": 0,
        },
    )

    response = client.get("/api/bmi/NoDimensions")

    assert response.status_code == 400

    assert (
        response.get_json()["error"]
        == "Client has missing or invalid height/weight"
    )


def test_bmi_json_endpoint(client):
    response = client.post(
        "/bmi",
        json={
            "height": 165,
            "weight": 60,
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["bmi"] == 22.0
    assert data["category"] == "Normal"


def test_bmi_invalid_json(client):
    response = client.post(
        "/bmi",
        json={
            "height": 0,
            "weight": 0,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Valid height and weight are required"


def test_bmi_html(client):
    response = client.post(
        "/bmi",
        data={
            "height": "165",
            "weight": "60",
        },
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "BMI: 22.0" in page
    assert "Normal" in page


def test_bmi_invalid_html(client):
    response = client.post(
        "/bmi",
        data={
            "height": "0",
            "weight": "0",
        },
    )

    assert response.status_code == 400
    assert "Enter valid height and weight" in response.get_data(as_text=True)


# ---------------------------------------------------------
# Parsing Helpers
# ---------------------------------------------------------

def test_parse_float(app_module):
    assert app_module.parse_float("10.5") == 10.5
    assert app_module.parse_float("") == 0.0
    assert app_module.parse_float(None) == 0.0
    assert app_module.parse_float("invalid") == 0.0


def test_parse_int(app_module):
    assert app_module.parse_int("10") == 10
    assert app_module.parse_int("10.8") == 10
    assert app_module.parse_int("") == 0
    assert app_module.parse_int(None) == 0
    assert app_module.parse_int("invalid") == 0


# ---------------------------------------------------------
# Empty API collections
# ---------------------------------------------------------

def test_empty_progress(client):
    response = client.get("/api/progress/Unknown")

    assert response.status_code == 200
    assert response.get_json() == []


def test_empty_workouts(client):
    response = client.get("/api/workouts/Unknown")

    assert response.status_code == 200
    assert response.get_json() == []


def test_empty_metrics(client):
    response = client.get("/api/metrics/Unknown")

    assert response.status_code == 200
    assert response.get_json() == []
