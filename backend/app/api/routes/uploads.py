from fastapi import APIRouter, Form, HTTPException, UploadFile

from app.services.upload_service import (
    UploadCategory,
    UploadedFileInfo,
    UploadService,
    UploadValidationError,
)

router = APIRouter()
upload_service = UploadService()


@router.post("/uploads", response_model=list[UploadedFileInfo])
def upload_files(
    files: list[UploadFile],
    category: UploadCategory = Form(...),
    session_id: str | None = Form(default=None),
) -> list[UploadedFileInfo]:
    try:
        return upload_service.save_files(files, category, session_id)
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
