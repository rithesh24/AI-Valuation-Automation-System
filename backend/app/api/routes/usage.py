from fastapi import APIRouter
from pydantic import BaseModel

from app.services.usage_service import UsageService

router = APIRouter()
usage_service = UsageService()


class MonthlyUsageResponse(BaseModel):
    year: int
    month: int
    request_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


@router.get("/usage/monthly", response_model=MonthlyUsageResponse)
def get_monthly_usage(year: int | None = None, month: int | None = None) -> MonthlyUsageResponse:
    return MonthlyUsageResponse(**usage_service.get_monthly_usage(year=year, month=month))
