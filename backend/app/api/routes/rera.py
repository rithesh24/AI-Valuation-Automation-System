from fastapi import APIRouter, HTTPException

from app.services.official_sources_service import (
    RERASearchInput,
    RERASearchResult,
    RERAService,
    RERAServiceError,
)

router = APIRouter()
rera_service = RERAService()


@router.post("/rera/lookup", response_model=RERASearchResult)
async def rera_lookup(search_input: RERASearchInput) -> RERASearchResult:
    """Debug/manual-testing endpoint for driving the live MahaRERA portal by hand.

    Disposable, not part of the documented architecture — Phase 5/6's report_service.py
    will be the real caller. See docs/DECISIONS.md D16.
    """
    try:
        return await rera_service.search_projects(search_input)
    except RERAServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
