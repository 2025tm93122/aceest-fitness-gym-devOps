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
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_home_page_lists_all_programs(client):
    response = client.get("/")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Fat Loss (FL)" in page
    assert "Muscle Gain (MG)" in page
    assert "Beginner (BG)" in page


def test_fat_loss_program_displays_workout_and_diet(client):
    response = client.post("/", data={"program": "Fat Loss (FL)"})
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Back Squat" in page
    assert "Grilled Chicken" in page
    assert "2,000 kcal" in page


def test_beginner_program_displays_expected_content(client):
    response = client.post("/", data={"program": "Beginner (BG)"})
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Air Squats" in page
    assert "Balanced Tamil Meals" in page
