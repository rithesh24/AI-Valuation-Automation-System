"""Token/cost tracking (docs/ARCHITECTURE.md, D10, D17, D18) — SQLite-backed,
single-user desktop scale, no ORM.
"""

from datetime import datetime, timezone

from app.core.config import settings
from app.core.db import get_connection


class UsageService:
    def record_usage(self, input_tokens: int, output_tokens: int, stage: str) -> None:
        cost_usd = (
            input_tokens / 1_000_000 * settings.ANTHROPIC_INPUT_PRICE_PER_MTOK
            + output_tokens / 1_000_000 * settings.ANTHROPIC_OUTPUT_PRICE_PER_MTOK
        )
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO usage_log (recorded_at, stage, input_tokens, output_tokens, cost_usd)
                VALUES (?, ?, ?, ?, ?)
                """,
                (datetime.now(timezone.utc).isoformat(), stage, input_tokens, output_tokens, cost_usd),
            )

    def get_monthly_usage(self, year: int | None = None, month: int | None = None) -> dict:
        now = datetime.now(timezone.utc)
        year = year if year is not None else now.year
        month = month if month is not None else now.month
        month_prefix = f"{year:04d}-{month:02d}"

        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*),
                    COALESCE(SUM(input_tokens), 0),
                    COALESCE(SUM(output_tokens), 0),
                    COALESCE(SUM(cost_usd), 0.0)
                FROM usage_log
                WHERE recorded_at LIKE ?
                """,
                (f"{month_prefix}%",),
            ).fetchone()

        request_count, input_tokens, output_tokens, cost_usd = row
        return {
            "year": year,
            "month": month,
            "request_count": request_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost_usd,
        }
