import re
import uuid
from enum import Enum
from pathlib import Path

from fastapi import UploadFile
from pydantic import BaseModel

from app.core.config import settings


class UploadCategory(str, Enum):
    PROPERTY_DOCUMENT = "property_document"
    TEMPLATE = "template"
    SUPPORTING_IMAGE = "supporting_image"


ALLOWED_EXTENSIONS: dict[UploadCategory, set[str]] = {
    UploadCategory.PROPERTY_DOCUMENT: {".pdf", ".docx", ".jpg", ".jpeg", ".png"},
    UploadCategory.TEMPLATE: {".docx"},
    UploadCategory.SUPPORTING_IMAGE: {".jpg", ".jpeg", ".png"},
}


class UploadValidationError(Exception):
    """Raised when an uploaded file fails validation. Message is safe to show the user."""


class UploadedFileInfo(BaseModel):
    session_id: str
    category: UploadCategory
    original_filename: str
    stored_filename: str
    path: str
    size_bytes: int


def _sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or "unnamed"


class UploadService:
    def __init__(self, upload_dir: str | None = None, max_size_mb: int | None = None) -> None:
        self._upload_dir = Path(upload_dir or settings.UPLOAD_DIR)
        self._max_size_bytes = (max_size_mb or settings.MAX_UPLOAD_SIZE_MB) * 1024 * 1024

    def validate_file(self, file: UploadFile, category: UploadCategory) -> str:
        """Checks the filename/extension are acceptable for the category.

        Returns the sanitized filename. Raises UploadValidationError otherwise.
        """
        if not file.filename:
            raise UploadValidationError("Uploaded file is missing a filename.")

        sanitized = _sanitize_filename(file.filename)
        extension = Path(sanitized).suffix.lower()
        allowed = ALLOWED_EXTENSIONS[category]
        if extension not in allowed:
            raise UploadValidationError(
                f"File type '{extension}' is not allowed for category '{category.value}'. "
                f"Allowed types: {', '.join(sorted(allowed))}."
            )
        return sanitized

    def save_temp_file(
        self, file: UploadFile, category: UploadCategory, session_id: str
    ) -> UploadedFileInfo:
        """Validates and streams an uploaded file to disk, enforcing the max size limit."""
        sanitized_filename = self.validate_file(file, category)

        session_dir = self._upload_dir / session_id / category.value
        session_dir.mkdir(parents=True, exist_ok=True)
        destination = session_dir / sanitized_filename

        size_bytes = 0
        chunk_size = 1024 * 1024
        with destination.open("wb") as out_file:
            while chunk := file.file.read(chunk_size):
                size_bytes += len(chunk)
                if size_bytes > self._max_size_bytes:
                    out_file.close()
                    destination.unlink(missing_ok=True)
                    raise UploadValidationError(
                        f"File '{sanitized_filename}' exceeds the maximum allowed size of "
                        f"{self._max_size_bytes // (1024 * 1024)} MB."
                    )
                out_file.write(chunk)

        return UploadedFileInfo(
            session_id=session_id,
            category=category,
            original_filename=file.filename or sanitized_filename,
            stored_filename=sanitized_filename,
            path=str(destination),
            size_bytes=size_bytes,
        )

    def save_files(
        self, files: list[UploadFile], category: UploadCategory, session_id: str | None
    ) -> list[UploadedFileInfo]:
        resolved_session_id = session_id or str(uuid.uuid4())
        return [
            self.save_temp_file(file, category, resolved_session_id) for file in files
        ]
