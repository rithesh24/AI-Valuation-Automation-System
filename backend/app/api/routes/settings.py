from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.settings_service import SettingsService, SettingsServiceError

router = APIRouter()
settings_service = SettingsService()


class ApiKeyStatusResponse(BaseModel):
    configured: bool


class SetApiKeyRequest(BaseModel):
    api_key: str


@router.get("/settings/api-key", response_model=ApiKeyStatusResponse)
def get_api_key_status() -> ApiKeyStatusResponse:
    return ApiKeyStatusResponse(configured=settings_service.is_api_key_configured())


@router.put("/settings/api-key", response_model=ApiKeyStatusResponse)
def set_api_key(request: SetApiKeyRequest) -> ApiKeyStatusResponse:
    try:
        settings_service.set_api_key(request.api_key)
    except SettingsServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiKeyStatusResponse(configured=settings_service.is_api_key_configured())
