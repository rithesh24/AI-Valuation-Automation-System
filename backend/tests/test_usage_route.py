from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.services.usage_service import UsageService

client = TestClient(app)


def test_monthly_usage_endpoint_reflects_recorded_usage(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.db.settings.DATABASE_PATH", str(tmp_path / "test.db"))
    UsageService().record_usage(1000, 500, stage="extraction")

    now = datetime.now(timezone.utc)
    response = client.get("/usage/monthly", params={"year": now.year, "month": now.month})

    assert response.status_code == 200
    body = response.json()
    assert body["request_count"] == 1
    assert body["input_tokens"] == 1000
    assert body["output_tokens"] == 500
    assert body["total_tokens"] == 1500


def test_monthly_usage_endpoint_defaults_to_current_month(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.db.settings.DATABASE_PATH", str(tmp_path / "test.db"))
    UsageService().record_usage(10, 5, stage="mapping")

    response = client.get("/usage/monthly")

    assert response.status_code == 200
    assert response.json()["request_count"] == 1
