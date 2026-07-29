import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_data_dir(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.services.settings_service.settings.DATABASE_PATH", str(tmp_path / "avas.db"))
    monkeypatch.setattr("app.services.settings_service.settings.ANTHROPIC_API_KEY", "")


def test_get_status_false_when_unset() -> None:
    response = client.get("/settings/api-key")

    assert response.status_code == 200
    assert response.json() == {"configured": False}


def test_put_sets_key_and_status_reflects_it() -> None:
    put_response = client.put("/settings/api-key", json={"api_key": "sk-test-123"})
    assert put_response.status_code == 200
    assert put_response.json() == {"configured": True}

    get_response = client.get("/settings/api-key")
    assert get_response.json() == {"configured": True}


def test_put_rejects_empty_key() -> None:
    response = client.put("/settings/api-key", json={"api_key": "   "})

    assert response.status_code == 400


def test_response_never_echoes_the_key_value() -> None:
    response = client.put("/settings/api-key", json={"api_key": "sk-super-secret"})

    assert "sk-super-secret" not in response.text
