import importlib
from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    database = tmp_path / "aceest_test.db"

    monkeypatch.setenv(
        "DATABASE_PATH",
        str(database),
    )

    sys.modules.pop("app", None)

    module = importlib.import_module("app")

    module.DB_NAME = str(database)
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


def create_client(client):
    return client.post(
        "/client",
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


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "healthy"
    }


def test_empty_dashboard(client):
    response = client.get("/")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "ACEest Functional Fitness System" in page
    assert "Client Management" in page
    assert "Weekly Progress" in page
    assert "Workout Logging" in page
    assert "Body Metrics" in page
    assert "BMI &amp; Risk Info" in page or "BMI & Risk Info" in page


def test_create_client(client, app_module):
    response = create_client(client)

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Nia" in page
    assert "1320" in page

    connection = app_module.conn()

    row = connection.execute(
        "SELECT * FROM clients WHERE name=?",
        ("Nia",),
    ).fetchone()

    connection.close()

    assert row is not None
    assert row["age"] == 25
    assert row["height"] == 165
    assert row["weight"] == 60
    assert row["calories"] == 1320
    assert row["target_weight"] == 55
    assert row["target_adherence"] == 90


def test_invalid_client(client):
    response = client.post(
        "/client",
        data={
            "name": "",
            "program": "Unknown",
        },
    )

    assert response.status_code == 400

    assert (
        "Name and a valid program are required"
        in response.get_data(as_text=True)
    )


def test_progress(client, app_module):
    create_client(client)

    response = client.post(
        "/progress",
        data={
            "client_name": "Nia",
            "adherence": "85",
        },
    )

    assert response.status_code == 200
    assert "85%" in response.get_data(as_text=True)

    connection = app_module.conn()

    row = connection.execute(
        """
        SELECT adherence
        FROM progress
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    connection.close()

    assert row["adherence"] == 85


def test_progress_requires_client(client):
    response = client.post(
        "/progress",
        data={
            "client_name": "",
            "adherence": "80",
        },
    )

    assert response.status_code == 400

    assert (
        response.get_json()["error"]
        == "client_name is required"
    )


def test_workout(client, app_module):
    create_client(client)

    response = client.post(
        "/workout",
        data={
            "client_name": "Nia",
            "date": "2026-10-12",
            "workout_type": "Strength",
            "duration_min": "60",
            "notes": "Squats",
        },
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Strength" in page
    assert "Squats" in page

    connection = app_module.conn()

    row = connection.execute(
        """
        SELECT *
        FROM workouts
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    connection.close()

    assert row["client_name"] == "Nia"
    assert row["duration_min"] == 60


def test_workout_requires_fields(client):
    response = client.post(
        "/workout",
        data={
            "client_name": "",
            "workout_type": "",
        },
    )

    assert response.status_code == 400

    assert (
        response.get_json()["error"]
        == "client_name and workout_type are required"
    )


def test_metrics(client, app_module):
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

    assert response.status_code == 200

    connection = app_module.conn()

    row = connection.execute(
        """
        SELECT *
        FROM metrics
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    connection.close()

    assert row["weight"] == 60
    assert row["waist"] == 75
    assert row["bodyfat"] == 22


def test_metrics_requires_client(client):
    response = client.post(
        "/metrics",
        data={
            "client_name": "",
        },
    )

    assert response.status_code == 400

    assert (
        response.get_json()["error"]
        == "client_name is required"
    )


def test_bmi_normal(client):
    response = client.post(
        "/bmi",
        data={
            "height": "165",
            "weight": "60",
        },
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "BMI: 22.0 (Normal)" in page


def test_bmi_underweight(app_module):
    result = app_module.bmi_info(
        180,
        50,
    )

    assert result[1] == "Underweight"


def test_bmi_overweight(app_module):
    result = app_module.bmi_info(
        170,
        80,
    )

    assert result[1] == "Overweight"


def test_bmi_obese(app_module):
    result = app_module.bmi_info(
        160,
        90,
    )

    assert result[1] == "Obese"


def test_invalid_bmi(client):
    response = client.post(
        "/bmi",
        data={
            "height": "0",
            "weight": "60",
        },
    )

    assert response.status_code == 400

    assert (
        "Invalid height or weight"
        in response.get_data(as_text=True)
    )


def test_parse_int(app_module):
    assert app_module.parse_int("10") == 10
    assert app_module.parse_int("10.9") == 10
    assert app_module.parse_int("") == 0
    assert app_module.parse_int(None) == 0
    assert app_module.parse_int("abc") == 0


def test_parse_float(app_module):
    assert app_module.parse_float("10.5") == 10.5
    assert app_module.parse_float("") == 0.0
    assert app_module.parse_float(None) == 0.0
    assert app_module.parse_float("abc") == 0.0


def test_complete_flow(client, app_module):
    create_client(client)

    client.post(
        "/progress",
        data={
            "client_name": "Nia",
            "adherence": "90",
        },
    )

    client.post(
        "/workout",
        data={
            "client_name": "Nia",
            "date": "2026-10-12",
            "workout_type": "Strength",
            "duration_min": "45",
            "notes": "Full body",
        },
    )

    client.post(
        "/metrics",
        data={
            "client_name": "Nia",
            "date": "2026-10-12",
            "weight": "59",
            "waist": "74",
            "bodyfat": "21",
        },
    )

    response = client.get("/")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Nia" in page
    assert "90%" in page
    assert "Strength" in page
    assert "Full body" in page
    assert "74.0" in page

    connection = app_module.conn()

    assert (
        connection.execute(
            "SELECT COUNT(*) FROM clients"
        ).fetchone()[0]
        == 1
    )

    assert (
        connection.execute(
            "SELECT COUNT(*) FROM progress"
        ).fetchone()[0]
        == 1
    )

    assert (
        connection.execute(
            "SELECT COUNT(*) FROM workouts"
        ).fetchone()[0]
        == 1
    )

    assert (
        connection.execute(
            "SELECT COUNT(*) FROM metrics"
        ).fetchone()[0]
        == 1
    )

    connection.close()
