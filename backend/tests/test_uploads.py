import io

import pytest
from fastapi.testclient import TestClient

import app.api.routes.uploads as uploads_route
from app.main import app
from app.services.upload_service import UploadService

client = TestClient(app)


@pytest.fixture(autouse=True)
def small_upload_service(tmp_path, monkeypatch):
    service = UploadService(upload_dir=str(tmp_path), max_size_mb=1)
    monkeypatch.setattr(uploads_route, "upload_service", service)
    return service


def test_upload_valid_property_document():
    response = client.post(
        "/uploads",
        data={"category": "property_document"},
        files={"files": ("sale_deed.pdf", io.BytesIO(b"%PDF-1.4 fake content"), "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["original_filename"] == "sale_deed.pdf"
    assert body[0]["category"] == "property_document"
    assert body[0]["session_id"]


def test_upload_rejects_disallowed_extension_for_template():
    response = client.post(
        "/uploads",
        data={"category": "template"},
        files={"files": ("template.pdf", io.BytesIO(b"not a docx"), "application/pdf")},
    )
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]


def test_upload_rejects_oversized_file():
    oversized_content = b"0" * (2 * 1024 * 1024)  # 2 MB, over the 1 MB test limit
    response = client.post(
        "/uploads",
        data={"category": "supporting_image"},
        files={"files": ("photo.jpg", io.BytesIO(oversized_content), "image/jpeg")},
    )
    assert response.status_code == 400
    assert "exceeds the maximum allowed size" in response.json()["detail"]


def test_upload_groups_files_by_session_id():
    first_response = client.post(
        "/uploads",
        data={"category": "property_document"},
        files={"files": ("doc1.pdf", io.BytesIO(b"content one"), "application/pdf")},
    )
    session_id = first_response.json()[0]["session_id"]

    second_response = client.post(
        "/uploads",
        data={"category": "property_document", "session_id": session_id},
        files={"files": ("doc2.pdf", io.BytesIO(b"content two"), "application/pdf")},
    )

    assert second_response.json()[0]["session_id"] == session_id
