import importlib
from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    """Load app.py with a completely isolated SQLite test database."""

    database = tmp_path / "aceest_test.db"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_PATH", str(database))

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


def login(client, username="admin", password="admin"):
    return client.post(
        "/login",
        data={
            "username": username,
            "password": password,
        },
        follow_redirects=False,
    )


def create_client(
    client,
    name="Nia",
    program="Fat Loss",
    membership_status="Active",
    membership_end="2027-01-01",
):
    return client.post(
        "/client",
        data={
            "name": name,
            "age": "25",
            "height": "165",
            "weight": "60",
            "program": program,
            "target_weight": "55",
            "target_adherence": "90",
            "membership_status": membership_status,
            "membership_end": membership_end,
        },
        follow_redirects=False,
    )


# =========================================================
# HEALTH
# =========================================================

def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


# =========================================================
# LOGIN / LOGOUT / SESSION
# =========================================================

def test_login_page(client):
    response = client.get("/login")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "ACEest Login" in page
    assert "Username" in page
    assert "Password" in page


def test_valid_login(client):
    response = login(client)

    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_invalid_login(client):
    response = login(
        client,
        username="admin",
        password="wrong",
    )

    assert response.status_code == 200

    assert (
        "Invalid credentials"
        in response.get_data(as_text=True)
    )


def test_root_without_login(client):
    response = client.get("/")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_root_when_logged_in(client):
    login(client)

    response = client.get("/")

    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_dashboard_after_login(client):
    login(client)

    response = client.get("/dashboard")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "ACEest Dashboard" in page
    assert "Add / Save Client" in page
    assert "Generate AI Program" in page
    assert "Generate PDF Report" in page
    assert "Check Membership" in page


def test_logout(client):
    login(client)

    response = client.get("/logout")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    response = client.get("/dashboard")

    assert response.status_code == 302


# =========================================================
# CLIENT
# =========================================================

def test_client_requires_login(client):
    response = create_client(client)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_create_client(client, app_module):
    login(client)

    response = create_client(client)

    assert response.status_code == 302

    connection = app_module.get_connection()

    row = connection.execute(
        "SELECT * FROM clients WHERE name=?",
        ("Nia",),
    ).fetchone()

    connection.close()

    assert row is not None
    assert row["name"] == "Nia"
    assert row["age"] == 25
    assert row["height"] == 165
    assert row["weight"] == 60

    # Current v3.2.4 conversion uses factor 25.
    assert row["calories"] == 1500

    assert row["target_weight"] == 55
    assert row["target_adherence"] == 90
    assert row["membership_status"] == "Active"
    assert row["membership_end"] == "2027-01-01"


def test_client_without_weight(client, app_module):
    login(client)

    response = client.post(
        "/client",
        data={
            "name": "ZeroWeight",
            "age": "25",
            "height": "165",
            "weight": "0",
            "program": "Beginner",
            "target_weight": "",
            "target_adherence": "",
            "membership_status": "",
            "membership_end": "",
        },
    )

    assert response.status_code == 302

    connection = app_module.get_connection()

    row = connection.execute(
        "SELECT * FROM clients WHERE name=?",
        ("ZeroWeight",),
    ).fetchone()

    connection.close()

    assert row["calories"] is None
    assert row["target_weight"] is None
    assert row["target_adherence"] is None
    assert row["membership_status"] == "Active"


def test_update_existing_client(client, app_module):
    login(client)

    create_client(client)

    response = client.post(
        "/client",
        data={
            "name": "Nia",
            "age": "26",
            "height": "166",
            "weight": "62",
            "program": "Muscle Gain",
            "target_weight": "65",
            "target_adherence": "95",
            "membership_status": "Active",
            "membership_end": "2028-01-01",
        },
    )

    assert response.status_code == 302

    connection = app_module.get_connection()

    row = connection.execute(
        "SELECT * FROM clients WHERE name=?",
        ("Nia",),
    ).fetchone()

    connection.close()

    assert row["age"] == 26
    assert row["height"] == 166
    assert row["weight"] == 62
    assert row["calories"] == 1550
    assert row["target_weight"] == 65
    assert row["target_adherence"] == 95
    assert row["membership_end"] == "2028-01-01"


def test_client_name_required(client):
    login(client)

    response = client.post(
        "/client",
        data={
            "name": "",
            "program": "Fat Loss",
        },
    )

    assert response.status_code == 400

    assert (
        "Name is required"
        in response.get_data(as_text=True)
    )


def test_invalid_client_numbers(client):
    login(client)

    response = client.post(
        "/client",
        data={
            "name": "Nia",
            "age": "wrong",
            "height": "165",
            "weight": "60",
            "program": "Fat Loss",
        },
    )

    assert response.status_code == 400

    assert (
        "must be valid numbers"
        in response.get_data(as_text=True)
    )


def test_invalid_target_number(client):
    login(client)

    response = client.post(
        "/client",
        data={
            "name": "Nia",
            "age": "25",
            "height": "165",
            "weight": "60",
            "program": "Fat Loss",
            "target_weight": "invalid",
        },
    )

    assert response.status_code == 400


# =========================================================
# WORKOUT
# =========================================================

def test_workout_requires_login(client):
    response = client.post(
        "/workout",
        data={
            "client_name": "Nia",
            "duration_min": "60",
        },
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_add_workout(client, app_module):
    login(client)
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

    assert response.status_code == 302

    connection = app_module.get_connection()

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
    assert row["workout_type"] == "Strength"
    assert row["duration_min"] == 60
    assert row["notes"] == "Squats"


def test_invalid_workout_duration(client):
    login(client)

    response = client.post(
        "/workout",
        data={
            "client_name": "Nia",
            "date": "2026-10-12",
            "workout_type": "Strength",
            "duration_min": "not-a-number",
        },
    )

    assert response.status_code == 400

    assert (
        "Duration must be a number"
        in response.get_data(as_text=True)
    )


# =========================================================
# AI PROGRAM GENERATION
# =========================================================

def test_generate_requires_login(client):
    response = client.get(
        "/generate?client_name=Nia"
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_generate_fat_loss(client):
    login(client)

    create_client(
        client,
        name="FatUser",
        program="Fat Loss",
    )

    response = client.get(
        "/generate?client_name=FatUser"
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Program Generated" in page
    assert "FatUser" in page


def test_generate_muscle_gain(client):
    login(client)

    create_client(
        client,
        name="MuscleUser",
        program="Muscle Gain",
    )

    response = client.get(
        "/generate?client_name=MuscleUser"
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Program Generated" in page


def test_generate_beginner(client):
    login(client)

    create_client(
        client,
        name="BeginnerUser",
        program="Beginner",
    )

    response = client.get(
        "/generate?client_name=BeginnerUser"
    )

    assert response.status_code == 200

    assert (
        "Program Generated"
        in response.get_data(as_text=True)
    )


def test_generate_unknown_program(client):
    login(client)

    create_client(
        client,
        name="UnknownProgram",
        program="Something Else",
    )

    response = client.get(
        "/generate?client_name=UnknownProgram"
    )

    assert response.status_code == 200

    assert (
        "Program Generated"
        in response.get_data(as_text=True)
    )


def test_generate_unknown_client(client):
    login(client)

    response = client.get(
        "/generate?client_name=Nobody"
    )

    assert response.status_code == 404

    assert (
        "Client not found"
        in response.get_data(as_text=True)
    )


# =========================================================
# MEMBERSHIP
# =========================================================

def test_membership_requires_login(client):
    response = client.get(
        "/membership?client_name=Nia"
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_membership(client):
    login(client)
    create_client(client)

    response = client.get(
        "/membership?client_name=Nia"
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Membership: Active" in page
    assert "2027-01-01" in page


def test_membership_with_empty_values(client):
    login(client)

    create_client(
        client,
        name="NoMembershipDate",
        membership_status="",
        membership_end="",
    )

    response = client.get(
        "/membership?client_name=NoMembershipDate"
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Membership:" in page
    assert "N/A" in page


def test_membership_unknown_client(client):
    login(client)

    response = client.get(
        "/membership?client_name=Nobody"
    )

    assert response.status_code == 200

    assert (
        "Client not found"
        in response.get_data(as_text=True)
    )


# =========================================================
# PDF
# =========================================================

def test_report_requires_login(client):
    response = client.get(
        "/report?client_name=Nia"
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_report_unknown_client(client):
    login(client)

    response = client.get(
        "/report?client_name=Nobody"
    )

    assert response.status_code == 404

    assert (
        "Client not found"
        in response.get_data(as_text=True)
    )


def test_pdf_report(client):
    login(client)
    create_client(client)

    response = client.get(
        "/report?client_name=Nia"
    )

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")


def test_pdf_fallback(client, app_module, monkeypatch):
    login(client)
    create_client(client)

    monkeypatch.setattr(
        app_module,
        "FPDF",
        None,
    )

    response = client.get(
        "/report?client_name=Nia"
    )

    assert response.status_code == 200
    assert response.data.startswith(b"%PDF-1.4")


def test_build_basic_pdf(app_module):
    result = app_module.build_basic_pdf(
        "ACEest Test",
        [
            "Name: Nia",
            "Program: Fat Loss",
        ],
    )

    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF-1.4")
    assert b"%%EOF" in result


def test_pdf_escape(app_module):
    result = app_module.pdf_escape(
        r"ACEest (Nia) \ Test"
    )

    assert r"\(" in result
    assert r"\)" in result


# =========================================================
# DATABASE MIGRATION
# =========================================================

def test_column_names(app_module):
    connection = app_module.get_connection()

    columns = app_module.column_names(
        connection,
        "clients",
    )

    connection.close()

    assert "name" in columns
    assert "height" in columns
    assert "membership_status" in columns
    assert "membership_end" in columns


def test_ensure_column(app_module):
    connection = app_module.get_connection()

    connection.execute(
        """
        CREATE TABLE migration_test (
            id INTEGER PRIMARY KEY
        )
        """
    )

    app_module.ensure_column(
        connection,
        "migration_test",
        "extra_value",
        "TEXT",
    )

    columns = app_module.column_names(
        connection,
        "migration_test",
    )

    assert "extra_value" in columns

    # Execute again to cover the already-existing branch.
    app_module.ensure_column(
        connection,
        "migration_test",
        "extra_value",
        "TEXT",
    )

    connection.close()


# =========================================================
# DASHBOARD DATA
# =========================================================

def test_dashboard_displays_saved_data(client):
    login(client)
    create_client(client)

    client.post(
        "/workout",
        data={
            "client_name": "Nia",
            "date": "2026-10-12",
            "workout_type": "Strength",
            "duration_min": "45",
            "notes": "Full body workout",
        },
    )

    response = client.get("/dashboard")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Nia" in page
    assert "Active" in page
    assert "2027-01-01" in page
    assert "Strength" in page
    assert "Full body workout" in page


# =========================================================
# COMPLETE END-TO-END FLOW
# =========================================================

def test_complete_application_flow(client):
    login(client)

    response = create_client(client)

    assert response.status_code == 302

    workout = client.post(
        "/workout",
        data={
            "client_name": "Nia",
            "date": "2026-10-12",
            "workout_type": "Strength",
            "duration_min": "60",
            "notes": "Squats",
        },
    )

    assert workout.status_code == 302

    membership = client.get(
        "/membership?client_name=Nia"
    )

    assert membership.status_code == 200

    generated = client.get(
        "/generate?client_name=Nia"
    )

    assert generated.status_code == 200

    report = client.get(
        "/report?client_name=Nia"
    )

    assert report.status_code == 200
    assert report.data.startswith(b"%PDF")

    dashboard = client.get("/dashboard")

    assert dashboard.status_code == 200

    logout_response = client.get("/logout")

    assert logout_response.status_code == 302
