import re
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import settings
from app.models.valuation_schema import ValuationReportData
from app.services.claude_service import ClaudeServiceError
from app.services.document_parser import DocumentParser, DocumentParserError
from app.services.progress_tracker import get_progress
from app.services.report_service import (
    InjectionResult,
    QualityCheckResult,
    ReportService,
    ReportServiceError,
)

router = APIRouter()
report_service = ReportService()
document_parser = DocumentParser()

_REPORT_ID_RE = re.compile(r"^[0-9a-f-]{36}$")


class GenerateReportRequest(BaseModel):
    template_path: str
    data: ValuationReportData
    force_regenerate_mapping: bool = False


class GenerateReportResponse(BaseModel):
    report_id: str
    injection: InjectionResult
    quality_check: QualityCheckResult


class PreviewResponse(BaseModel):
    text: str


class ProgressResponse(BaseModel):
    percent: int
    stage: str


class GenerateFromSessionRequest(BaseModel):
    session_id: str
    valuation_date: date | None = None
    tier1_official_data: str | None = None
    force_regenerate_mapping: bool = False


class GenerateFromSessionResponse(BaseModel):
    report_id: str
    injection: InjectionResult
    quality_check: QualityCheckResult
    extracted_data: ValuationReportData


def _report_path(report_id: str) -> Path:
    if not _REPORT_ID_RE.match(report_id):
        raise HTTPException(status_code=400, detail="Invalid report_id.")
    path = Path(settings.REPORTS_DIR) / report_id / "report.docx"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found.")
    return path


@router.post("/reports/generate", response_model=GenerateReportResponse)
def generate_report(request: GenerateReportRequest) -> GenerateReportResponse:
    """Stage 2 + Stage 3 end to end: template -> (mapping, cached) -> populated .docx.

    Disposable/manual-testing endpoint, same status as /easr/lookup and
    /rera/lookup — the real caller will be a future full-pipeline orchestration
    (upload -> extraction -> this) once an API key makes that testable end to end.
    """
    try:
        mapping, _ = report_service.get_or_create_mapping(
            request.template_path, force_regenerate=request.force_regenerate_mapping
        )

        report_id = str(uuid.uuid4())
        output_dir = Path(settings.REPORTS_DIR) / report_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "report.docx"

        injection = report_service.inject_data(
            request.template_path, mapping, request.data, str(output_path)
        )
        quality_check = report_service.run_quality_check(mapping, request.data)
    except ReportServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return GenerateReportResponse(report_id=report_id, injection=injection, quality_check=quality_check)


@router.post("/reports/generate-from-session", response_model=GenerateFromSessionResponse)
def generate_report_from_session(
    request: GenerateFromSessionRequest,
) -> GenerateFromSessionResponse:
    """Full pipeline: a session's uploaded documents -> extraction -> mapping ->
    injection. This is the real caller `reports.generate` (above) was waiting
    on since Phase 6 — the one every other route/service in this pipeline was
    built to feed into.
    """
    try:
        report_id = str(uuid.uuid4())
        output_dir = Path(settings.REPORTS_DIR) / report_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "report.docx"

        injection, quality_check, extracted_data = report_service.generate_full_report(
            session_id=request.session_id,
            output_path=str(output_path),
            valuation_date=request.valuation_date,
            tier1_official_data=request.tier1_official_data,
            force_regenerate_mapping=request.force_regenerate_mapping,
        )
    except ReportServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return GenerateFromSessionResponse(
        report_id=report_id,
        injection=injection,
        quality_check=quality_check,
        extracted_data=extracted_data,
    )


@router.get("/reports/progress/{session_id}", response_model=ProgressResponse)
def get_generation_progress(session_id: str) -> ProgressResponse:
    """Polled by the frontend while /reports/generate-from-session is in flight."""
    progress = get_progress(session_id)
    return ProgressResponse(percent=progress["percent"], stage=progress["stage"])


@router.get("/reports/{report_id}/preview", response_model=PreviewResponse)
def preview_report(report_id: str) -> PreviewResponse:
    path = _report_path(report_id)
    try:
        return PreviewResponse(text=document_parser.extract_docx_text(str(path)))
    except DocumentParserError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/reports/{report_id}/download")
def download_report(report_id: str) -> FileResponse:
    path = _report_path(report_id)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="valuation_report.docx",
    )
