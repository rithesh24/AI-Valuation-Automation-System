from pathlib import Path

import pytest
from docx import Document

from app.models.template_mapping import FieldMapping
from app.models.valuation_schema import ComparableEvidence, ValuationReportData
from app.services.report_service import ReportService, ReportServiceError


def _build_template(path: Path) -> None:
    document = Document()
    document.add_paragraph("VALUATION REPORT")
    document.add_paragraph("Name of Owner")
    document.add_paragraph("")  # blank value line under the label above
    table = document.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "District"
    table.rows[0].cells[1].text = ""
    table.rows[1].cells[0].text = "Taluka"
    table.rows[1].cells[1].text = ""
    document.save(path)


class TestExtractTemplateSkeleton:
    def test_extracts_paragraphs_in_document_order(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_template(path)

        skeleton = ReportService().extract_template_skeleton(str(path))
        paragraph_texts = [loc.text for loc in skeleton if loc.type == "paragraph"]

        assert paragraph_texts == ["VALUATION REPORT", "Name of Owner", ""]

    def test_blank_paragraph_context_is_previous_non_blank_paragraph(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_template(path)

        skeleton = ReportService().extract_template_skeleton(str(path))
        blank_value_line = next(loc for loc in skeleton if loc.type == "paragraph" and loc.text == "")

        assert blank_value_line.context == ["Name of Owner"]

    def test_table_cell_context_is_the_rest_of_its_row(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_template(path)

        skeleton = ReportService().extract_template_skeleton(str(path))
        district_label = next(loc for loc in skeleton if loc.text == "District")
        district_value = next(
            loc for loc in skeleton if loc.type == "table_cell" and loc.location_id == "t0r0c1"
        )

        assert district_label.context == [""]
        assert district_value.context == ["District"]

    def test_location_ids_are_unique(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_template(path)

        skeleton = ReportService().extract_template_skeleton(str(path))
        ids = [loc.location_id for loc in skeleton]

        assert len(ids) == len(set(ids))

    def test_missing_file_raises_report_service_error(self) -> None:
        try:
            ReportService().extract_template_skeleton("does_not_exist.docx")
            assert False, "expected ReportServiceError"
        except ReportServiceError:
            pass


class TestSkeletonHash:
    def test_stable_for_identical_content(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_template(path)
        service = ReportService()

        skeleton_a = service.extract_template_skeleton(str(path))
        skeleton_b = service.extract_template_skeleton(str(path))

        assert service.skeleton_hash(skeleton_a) == service.skeleton_hash(skeleton_b)

    def test_changes_when_a_label_changes(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_template(path)
        service = ReportService()
        original_hash = service.skeleton_hash(service.extract_template_skeleton(str(path)))

        document = Document(str(path))
        document.paragraphs[1].text = "Name of Purchaser"
        document.save(path)

        changed_hash = service.skeleton_hash(service.extract_template_skeleton(str(path)))

        assert original_hash != changed_hash


class _FakeClaudeService:
    """Stands in for ClaudeService in mapping-cache tests — no real API call."""

    def __init__(self, mapping: dict[str, FieldMapping]) -> None:
        self.mapping = mapping
        self.calls = 0

    def map_template_fields(self, _skeleton) -> dict[str, FieldMapping]:
        self.calls += 1
        return self.mapping


@pytest.fixture(autouse=True)
def _isolated_database(tmp_path: Path, monkeypatch) -> None:
    """Points the SQLite cache at a fresh per-test file so tests don't share state."""
    monkeypatch.setattr(
        "app.core.db.settings.DATABASE_PATH", str(tmp_path / "test.db")
    )


class TestMappingCache:
    def test_cache_miss_calls_claude_and_saves(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_template(path)
        fake_mapping = {"property_identification.district": FieldMapping(location_id="t0r0c1")}
        claude = _FakeClaudeService(fake_mapping)
        service = ReportService()

        mapping, skeleton_hash = service.get_or_create_mapping(str(path), claude_service=claude)

        assert claude.calls == 1
        assert mapping == fake_mapping
        assert service.get_cached_mapping(skeleton_hash) == fake_mapping

    def test_cache_hit_does_not_call_claude(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_template(path)
        fake_mapping = {"property_identification.district": FieldMapping(location_id="t0r0c1")}
        claude = _FakeClaudeService(fake_mapping)
        service = ReportService()
        service.get_or_create_mapping(str(path), claude_service=claude)

        mapping, _ = service.get_or_create_mapping(str(path), claude_service=claude)

        assert claude.calls == 1  # not called a second time
        assert mapping == fake_mapping

    def test_force_regenerate_calls_claude_again(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_template(path)
        claude = _FakeClaudeService(
            {"property_identification.district": FieldMapping(location_id="t0r0c1")}
        )
        service = ReportService()
        service.get_or_create_mapping(str(path), claude_service=claude)

        service.get_or_create_mapping(str(path), claude_service=claude, force_regenerate=True)

        assert claude.calls == 2

    def test_get_cached_mapping_returns_none_when_absent(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_template(path)
        service = ReportService()
        skeleton_hash = service.skeleton_hash(service.extract_template_skeleton(str(path)))

        assert service.get_cached_mapping(skeleton_hash) is None


def _build_injection_template(path: Path) -> None:
    document = Document()
    document.add_paragraph("VALUATION REPORT")
    paragraph = document.add_paragraph()
    run = paragraph.add_run("PLACEHOLDER")
    run.bold = True
    run.font.name = "Times New Roman"
    table = document.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Indicator"
    table.rows[0].cells[1].text = "Location"
    document.save(path)


class TestInjectData:
    def test_scalar_field_preserves_run_formatting(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_injection_template(path)
        mapping = {"property_identification.district": FieldMapping(location_id="p1")}
        data = ValuationReportData(property_identification={"district": "Pune"})
        out_path = tmp_path / "out.docx"

        result = ReportService().inject_data(str(path), mapping, data, str(out_path))

        assert result.filled_fields == ["property_identification.district"]
        out_doc = Document(str(out_path))
        run = out_doc.paragraphs[1].runs[0]
        assert run.text == "Pune"
        assert run.bold is True
        assert run.font.name == "Times New Roman"

    def test_repeating_group_clones_rows_and_fills_columns(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_injection_template(path)
        mapping = {
            "comparable_evidence[].indicator_number": FieldMapping(location_id="t0r1c0"),
            "comparable_evidence[].location": FieldMapping(location_id="t0r1c1"),
        }
        data = ValuationReportData(
            comparable_evidence=[
                ComparableEvidence(indicator_number="1", location="Kothrud"),
                ComparableEvidence(indicator_number="2", location="Baner"),
                ComparableEvidence(indicator_number="3", location="Wakad"),
            ]
        )
        out_path = tmp_path / "out.docx"

        ReportService().inject_data(str(path), mapping, data, str(out_path))

        out_doc = Document(str(out_path))
        rows = [[cell.text for cell in row.cells] for row in out_doc.tables[0].rows]
        assert rows == [
            ["Indicator", "Location"],
            ["1", "Kothrud"],
            ["2", "Baner"],
            ["3", "Wakad"],
        ]

    def test_unmapped_field_with_real_value_is_reported(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_injection_template(path)
        mapping = {
            "property_identification.district": FieldMapping(location_id=None, status="not_present")
        }
        data = ValuationReportData(property_identification={"district": "Pune"})
        out_path = tmp_path / "out.docx"

        result = ReportService().inject_data(str(path), mapping, data, str(out_path))

        assert result.unmapped_fields == ["property_identification.district"]

    def test_field_marked_unavailable_is_not_reported_as_unmapped(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_injection_template(path)
        mapping = {
            "property_identification.district": FieldMapping(location_id=None, status="not_present")
        }
        data = ValuationReportData()  # district defaults to the non-fabrication sentinel
        out_path = tmp_path / "out.docx"

        result = ReportService().inject_data(str(path), mapping, data, str(out_path))

        assert result.unmapped_fields == []
        assert result.filled_fields == []

    def test_empty_repeating_list_leaves_prototype_row_untouched(self, tmp_path: Path) -> None:
        path = tmp_path / "template.docx"
        _build_injection_template(path)
        mapping = {"comparable_evidence[].indicator_number": FieldMapping(location_id="t0r1c0")}
        data = ValuationReportData(comparable_evidence=[])
        out_path = tmp_path / "out.docx"

        result = ReportService().inject_data(str(path), mapping, data, str(out_path))

        assert result.filled_fields == []
        out_doc = Document(str(out_path))
        assert len(out_doc.tables[0].rows) == 2  # no rows cloned/removed


class TestRunQualityCheck:
    def test_flags_unmapped_field_with_real_value(self) -> None:
        mapping = {
            "property_identification.district": FieldMapping(location_id=None, status="not_present")
        }
        data = ValuationReportData(property_identification={"district": "Pune"})

        result = ReportService().run_quality_check(mapping, data)

        assert result.passed is False
        assert result.injection_failures == ["property_identification.district"]
        assert result.disclosed_unavailable == []

    def test_disclosed_unavailable_is_not_a_failure(self) -> None:
        mapping = {
            "property_identification.district": FieldMapping(location_id=None, status="not_present")
        }
        data = ValuationReportData()  # sentinel default

        result = ReportService().run_quality_check(mapping, data)

        assert result.passed is True
        assert result.disclosed_unavailable == ["property_identification.district"]
        assert result.injection_failures == []

    def test_mapped_field_with_real_value_passes(self) -> None:
        mapping = {
            "property_identification.district": FieldMapping(location_id="p1", confidence="high")
        }
        data = ValuationReportData(property_identification={"district": "Pune"})

        result = ReportService().run_quality_check(mapping, data)

        assert result.passed is True
        assert result.injection_failures == []
