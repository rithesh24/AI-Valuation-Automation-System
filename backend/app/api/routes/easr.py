from fastapi import APIRouter, HTTPException

from app.services.easr_service import (
    EASRGuidelineResult,
    EASRSearchInput,
    EASRService,
    EASRServiceError,
)

router = APIRouter()
easr_service = EASRService()


@router.post("/easr/lookup", response_model=EASRGuidelineResult)
async def easr_lookup(search_input: EASRSearchInput) -> EASRGuidelineResult:
    """Debug/manual-testing endpoint for driving the live eASR portal by hand.

    Disposable, not part of the documented architecture — Phase 5/6's report_service.py
    will be the real caller. See docs/DECISIONS.md D14.
    """
    try:
        return await easr_service.fetch_guideline_value(search_input)
    except EASRServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
