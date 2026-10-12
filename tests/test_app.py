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


def login(client, username="admin", password="admin"):
    return client.post(
        "/login",
        data={
            "username": username,
            "password": password,
        },
        follow_redirects=False,
    )


def create_client(client, name="Nia", program="Fat Loss (FL) – 3 day"):
    return client.post(
        "/client",
        data={
            "name": name,
            "age": "25",
            "height": "165",
            "weight": "60",
            "program": program,
            "membership_expiry": "2027-01-01",
        },
        follow_redirects=False,
    )


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_root_redirects_to_login(client):
    response = client.get("/")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_page(client):
    response = client.get("/login")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "ACEest Login" in page
    assert "Username" in page
    assert "Password" in page


def test_admin_login(client):
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
    assert "Invalid credentials" in response.get_data(as_text=True)


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_dashboard_after_login(client):
    login(client)

    response = client.get("/dashboard")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "ACEest Fitness Dashboard" in page
    assert "Add / Save Client" in page
    assert "Generate AI Program" in page
    assert "Export PDF Report" in page
    assert "Check Membership" in page


def test_root_after_login_redirects_dashboard(client):
    login(client)

    response = client.get("/")

    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_logout(client):
    login(client)

    response = client.get("/logout")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    dashboard = client.get("/dashboard")

    assert dashboard.status_code == 302


def test_client_requires_login(client):
    response = create_client(client)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_create_client(client, app_module):
    login(client)

    response = create_client(client)

    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]

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
    assert row["calories"] == 1320
    assert row["membership_expiry"] == "2027-01-01"


def test_update_existing_client(client, app_module):
    login(client)

    create_client(client)

    response = client.post(
        "/client",
        data={
            "name": "Nia",
            "age": "26",
            "height": "165",
            "weight": "61",
            "program": "Fat Loss (FL) – 5 day",
            "membership_expiry": "2028-01-01",
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
    assert row["weight"] == 61
    assert row["calories"] == 1464
    assert row["membership_expiry"] == "2028-01-01"


def test_client_name_required(client):
    login(client)

    response = client.post(
        "/client",
        data={
            "name": "",
            "program": "Beginner (BG)",
        },
    )

    assert response.status_code == 400
    assert "Name is required" in response.get_data(as_text=True)


def test_client_invalid_numbers(client):
    login(client)

    response = client.post(
        "/client",
        data={
            "name": "Nia",
            "age": "not-number",
            "height": "165",
            "weight": "60",
            "program": "Beginner (BG)",
        },
    )

    assert response.status_code == 400

    assert (
        "Age, height and weight must be valid numbers"
        in response.get_data(as_text=True)
    )


def test_generate_requires_login(client):
    response = client.post(
        "/generate",
        data={
            "client_name": "Nia",
            "experience": "beginner",
        },
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_generate_fat_loss_program(client):
    login(client)
    create_client(client)

    response = client.post(
        "/generate",
        data={
            "client_name": "Nia",
            "experience": "beginner",
        },
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Generated AI Program" in page
    assert "Conditioning" in page
    assert "beginner" in page


def test_generate_muscle_gain_program(client):
    login(client)

    create_client(
        client,
        name="Alex",
        program="Muscle Gain (MG) – PPL",
    )

    response = client.post(
        "/generate",
        data={
            "client_name": "Alex",
            "experience": "intermediate",
        },
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Hypertrophy" in page
    assert "intermediate" in page


def test_generate_full_body_program(client):
    login(client)

    create_client(
        client,
        name="Sam",
        program="Beginner (BG)",
    )

    response = client.post(
        "/generate",
        data={
            "client_name": "Sam",
            "experience": "advanced",
        },
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Full Body" in page
    assert "advanced" in page


def test_invalid_experience_defaults_beginner(client):
    login(client)
    create_client(client)

    response = client.post(
        "/generate",
        data={
            "client_name": "Nia",
            "experience": "invalid",
        },
    )

    assert response.status_code == 200
    assert "beginner" in response.get_data(as_text=True)


def test_generate_unknown_client(client):
    login(client)

    response = client.post(
        "/generate",
        data={
            "client_name": "Unknown",
            "experience": "beginner",
        },
    )

    assert response.status_code == 404
    assert "Client not found" in response.get_data(as_text=True)


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

    assert "Membership Expiry" in page
    assert "2027-01-01" in page


def test_membership_unknown_client(client):
    login(client)

    response = client.get(
        "/membership?client_name=Unknown"
    )

    assert response.status_code == 200
    assert "Client not found" in response.get_data(as_text=True)


def test_report_requires_login(client):
    response = client.get(
        "/report?client_name=Nia"
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_pdf_report(client):
    login(client)
    create_client(client)

    response = client.get(
        "/report?client_name=Nia"
    )

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")


def test_report_unknown_client(client):
    login(client)

    response = client.get(
        "/report?client_name=Unknown"
    )

    assert response.status_code == 404
    assert "Client not found" in response.get_data(as_text=True)


def test_bmi_helpers_not_present_but_database_migration(app_module):
    connection = app_module.get_connection()

    columns = app_module.column_names(
        connection,
        "clients",
    )

    connection.close()

    assert "height" in columns
    assert "target_weight" in columns
    assert "target_adherence" in columns
    assert "membership_expiry" in columns


def test_ensure_column(app_module):
    connection = app_module.get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS migration_test (
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

    # Calling it again must not fail or duplicate the column.
    app_module.ensure_column(
        connection,
        "migration_test",
        "extra_value",
        "TEXT",
    )

    connection.close()


def test_pdf_escape(app_module):
    escaped = app_module.pdf_escape(
        r"Test (ACEest) \ Report"
    )

    assert r"\(" in escaped
    assert r"\)" in escaped
    assert "\\" in escaped


def test_basic_pdf_fallback(app_module):
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


def test_create_report_fallback(client, app_module, monkeypatch):
    login(client)
    create_client(client)

    connection = app_module.get_connection()

    row = connection.execute(
        "SELECT * FROM clients WHERE name=?",
        ("Nia",),
    ).fetchone()

    connection.close()

    monkeypatch.setattr(
        app_module,
        "FPDF",
        None,
    )

    result = app_module.create_report_pdf(row)

    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")


def test_complete_application_flow(client):
    login(client)

    create_client(client)

    dashboard = client.get("/dashboard")

    assert dashboard.status_code == 200
    assert "Nia" in dashboard.get_data(as_text=True)

    generated = client.post(
        "/generate",
        data={
            "client_name": "Nia",
            "experience": "beginner",
        },
    )

    assert generated.status_code == 200
    assert "Conditioning" in generated.get_data(as_text=True)

    membership = client.get(
        "/membership?client_name=Nia"
    )

    assert membership.status_code == 200
    assert "2027-01-01" in membership.get_data(as_text=True)

    report = client.get(
        "/report?client_name=Nia"
    )

    assert report.status_code == 200
    assert report.data.startswith(b"%PDF")

    logout_response = client.get("/logout")

    assert logout_response.status_code == 302
