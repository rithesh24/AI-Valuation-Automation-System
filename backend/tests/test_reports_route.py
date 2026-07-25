import uuid
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from app.models.template_mapping import FieldMapping
from app.services.claude_service import ClaudeService

client = TestClient(app)


def _build_template(path: Path) -> None:
    document = Document()
    document.add_paragraph("VALUATION REPORT")
    document.add_paragraph("")
    document.save(path)


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path: Path, monkeypatch) -> None:
    """Points reports storage and the mapping cache at fresh per-test files."""
    monkeypatch.setattr("app.core.config.settings.REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setattr("app.core.db.settings.DATABASE_PATH", str(tmp_path / "test.db"))


@pytest.fixture(autouse=True)
def _fake_claude_mapping(monkeypatch) -> None:
    """No real API call: ClaudeService.map_template_fields is swapped for a fake."""

    def fake_map_template_fields(self, skeleton):  # noqa: ARG001
        return {"property_identification.district": FieldMapping(location_id="p1")}

    monkeypatch.setattr(ClaudeService, "map_template_fields", fake_map_template_fields)


def test_generate_preview_download_flow(tmp_path: Path) -> None:
    template_path = tmp_path / "template.docx"
    _build_template(template_path)

    response = client.post(
        "/reports/generate",
        json={
            "template_path": str(template_path),
            "data": {"property_identification": {"district": "Pune"}},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["injection"]["filled_fields"] == ["property_identification.district"]
    assert body["quality_check"]["passed"] is True
    report_id = body["report_id"]

    preview = client.get(f"/reports/{report_id}/preview")
    assert preview.status_code == 200
    assert "Pune" in preview.json()["text"]

    download = client.get(f"/reports/{report_id}/download")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_preview_unknown_report_id_returns_404() -> None:
    response = client.get(f"/reports/{uuid.uuid4()}/preview")
    assert response.status_code == 404


def test_preview_invalid_report_id_format_returns_400() -> None:
    response = client.get("/reports/not-a-uuid/preview")
    assert response.status_code == 400


def test_generate_with_bad_template_path_returns_400() -> None:
    response = client.post(
        "/reports/generate",
        json={"template_path": "does_not_exist.docx", "data": {}},
    )
    assert response.status_code == 400
