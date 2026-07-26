from datetime import datetime, timezone

import pytest

from app.services.usage_service import UsageService


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.db.settings.DATABASE_PATH", str(tmp_path / "test.db"))


def test_record_and_aggregate_current_month() -> None:
    service = UsageService()
    service.record_usage(1000, 500, stage="extraction")
    service.record_usage(2000, 1000, stage="mapping")

    now = datetime.now(timezone.utc)
    usage = service.get_monthly_usage(year=now.year, month=now.month)

    assert usage["request_count"] == 2
    assert usage["input_tokens"] == 3000
    assert usage["output_tokens"] == 1500
    assert usage["total_tokens"] == 4500


def test_cost_uses_configured_per_million_pricing(monkeypatch) -> None:
    monkeypatch.setattr("app.services.usage_service.settings.ANTHROPIC_INPUT_PRICE_PER_MTOK", 2.0)
    monkeypatch.setattr("app.services.usage_service.settings.ANTHROPIC_OUTPUT_PRICE_PER_MTOK", 10.0)
    service = UsageService()
    service.record_usage(1_000_000, 1_000_000, stage="extraction")

    now = datetime.now(timezone.utc)
    usage = service.get_monthly_usage(year=now.year, month=now.month)

    assert usage["cost_usd"] == pytest.approx(12.0)


def test_month_with_no_usage_returns_zeros() -> None:
    service = UsageService()

    usage = service.get_monthly_usage(year=1999, month=1)

    assert usage == {
        "year": 1999,
        "month": 1,
        "request_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
    }


def test_usage_is_scoped_to_requested_month() -> None:
    service = UsageService()
    service.record_usage(100, 50, stage="extraction")

    other_month = 1 if datetime.now(timezone.utc).month != 1 else 2
    usage = service.get_monthly_usage(year=datetime.now(timezone.utc).year, month=other_month)

    assert usage["request_count"] == 0
