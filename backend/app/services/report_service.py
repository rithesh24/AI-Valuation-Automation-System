"""Report generation, Stages 2 and 3 (D5). Stage 2 (Mapping): skeleton
extraction + mapping cache — the Claude mapping call itself lives in
claude_service.py (only that module talks to Claude, per
docs/ARCHITECTURE.md); this module extracts the skeleton, hashes it, and
caches/reuses the resulting mapping so Claude is only called once per unique
template. Stage 3 (Injection): applies a mapping deterministically, never
generating new formatted elements — only mutating existing Run text and
cloning existing table rows — so formatting fidelity holds by construction.
"""

import copy
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table, _Row
from docx.text.paragraph import Paragraph
from pydantic import BaseModel

from app.core.db import get_connection
from app.models.template_mapping import FieldMapping, SkeletonLocation
from app.models.valuation_schema import INFO_NOT_AVAILABLE, ValuationReportData
from app.services.claude_service import ClaudeService
from app.services.document_parser import DocumentParser, DocumentParserError
from app.services.upload_service import UploadCategory, UploadService

_TABLE_CELL_LOCATION_RE = re.compile(r"^t(\d+)r(\d+)c(\d+)$")
_OCR_EXTENSIONS = {".jpg", ".jpeg", ".png"}


class ReportServiceError(Exception):
    """Raised when a template can't be read. Message is safe to show the user."""


class InjectionResult(BaseModel):
    output_path: str
    filled_fields: list[str] = []
    unmapped_fields: list[str] = []
    """Fields that held a real (non-sentinel) value but had no usable
    location to write it to — a template location that didn't survive to
    the populated document, not merely a field the template never had."""


class QualityCheckResult(BaseModel):
    passed: bool
    injection_failures: list[str] = []
    """Scalar fields with a real value but no mapped template location —
    would-be-blank fields (docs/ARCHITECTURE.md: "no placeholder/empty
    fields left behind")."""
    disclosed_unavailable: list[str] = []
    """Fields honestly marked unavailable (non-fabrication rule) — not a
    failure, just surfaced for the valuer's review."""


class ReportService:
    def extract_template_skeleton(self, template_path: str) -> list[SkeletonLocation]:
        try:
            document = Document(template_path)
        except Exception as exc:
            raise ReportServiceError(f"Could not read the template file: {exc}") from exc

        locations: list[SkeletonLocation] = []
        previous_paragraph_text = ""
        table_index = 0
        for block in _iter_block_items(document):
            if isinstance(block, Paragraph):
                locations.append(
                    SkeletonLocation(
                        location_id=f"p{len(locations)}",
                        type="paragraph",
                        text=block.text,
                        context=[previous_paragraph_text] if previous_paragraph_text else [],
                    )
                )
                if block.text.strip():
                    previous_paragraph_text = block.text
            else:
                for row_idx, row in enumerate(block.rows):
                    row_texts = [cell.text for cell in row.cells]
                    for col_idx, cell in enumerate(row.cells):
                        locations.append(
                            SkeletonLocation(
                                location_id=f"t{table_index}r{row_idx}c{col_idx}",
                                type="table_cell",
                                text=cell.text,
                                context=[t for i, t in enumerate(row_texts) if i != col_idx],
                            )
                        )
                table_index += 1
        return locations

    def skeleton_hash(self, skeleton: list[SkeletonLocation]) -> str:
        """Hash used to key the Stage 2 mapping cache (D6)."""
        payload = json.dumps([loc.model_dump() for loc in skeleton], sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_cached_mapping(self, skeleton_hash: str) -> dict[str, FieldMapping] | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT mapping_json FROM template_mapping_cache WHERE skeleton_hash = ?",
                (skeleton_hash,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row[0])
        return {name: FieldMapping.model_validate(value) for name, value in payload.items()}

    def save_mapping(
        self, skeleton_hash: str, mapping: dict[str, FieldMapping], bank_name: str = ""
    ) -> None:
        payload = json.dumps({name: fm.model_dump() for name, fm in mapping.items()})
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO template_mapping_cache "
                "(skeleton_hash, bank_name, first_seen_at, mapping_json) VALUES ("
                "  ?, ?,"
                "  COALESCE((SELECT first_seen_at FROM template_mapping_cache WHERE skeleton_hash = ?), ?),"
                "  ?"
                ")",
                (
                    skeleton_hash,
                    bank_name,
                    skeleton_hash,
                    datetime.now(timezone.utc).isoformat(),
                    payload,
                ),
            )

    def get_or_create_mapping(
        self,
        template_path: str,
        claude_service: ClaudeService | None = None,
        bank_name: str = "",
        force_regenerate: bool = False,
    ) -> tuple[dict[str, FieldMapping], str]:
        """Stage 2 entry point: template -> (field mapping, skeleton hash).

        Calls Claude only on a cache miss or an explicit regenerate override
        (D6's manual "regenerate mapping" action) — reused templates are
        mapped once, not once per report.
        """
        skeleton = self.extract_template_skeleton(template_path)
        skeleton_hash = self.skeleton_hash(skeleton)

        if not force_regenerate:
            cached = self.get_cached_mapping(skeleton_hash)
            if cached is not None:
                return cached, skeleton_hash

        mapping = (claude_service or ClaudeService()).map_template_fields(skeleton)
        self.save_mapping(skeleton_hash, mapping, bank_name=bank_name)
        return mapping, skeleton_hash

    def inject_data(
        self,
        template_path: str,
        mapping: dict[str, FieldMapping],
        data: ValuationReportData,
        output_path: str,
    ) -> InjectionResult:
        """Stage 3: applies `mapping` to a copy of the template, filling in `data`.

        Scalar fields have the existing Run's text replaced in place (keeps
        its formatting). Repeating groups (e.g. comparable_evidence[].*) get
        their prototype table row cloned once per extra list item, using the
        column position each subfield's mapped location already encodes —
        no separate column-mapping format needed from Claude.
        """
        try:
            document = Document(template_path)
        except Exception as exc:
            raise ReportServiceError(f"Could not read the template file: {exc}") from exc

        paragraphs, tables = _locate_structure(document)
        scalar_mapping, repeating_groups = _split_mapping(mapping)

        filled_fields: list[str] = []
        unmapped_fields: list[str] = []

        for field_name, field_mapping in scalar_mapping.items():
            value = _get_field_value(data, field_name)
            if value is None:
                continue
            location = None
            if field_mapping.location_id is not None:
                location = _resolve_location(field_mapping.location_id, paragraphs, tables)
            if location is None:
                if value != INFO_NOT_AVAILABLE:
                    unmapped_fields.append(field_name)
                continue
            _set_paragraph_text(location, value)
            filled_fields.append(field_name)

        for group_name, group_mapping in repeating_groups.items():
            items = _get_list_field(data, group_name)
            filled, unmapped = _inject_repeating_group(tables, group_name, group_mapping, items)
            filled_fields.extend(filled)
            unmapped_fields.extend(unmapped)

        document.save(output_path)
        return InjectionResult(
            output_path=output_path, filled_fields=filled_fields, unmapped_fields=unmapped_fields
        )

    def generate_full_report(
        self,
        session_id: str,
        output_path: str,
        valuation_date: date | None = None,
        tier1_official_data: str | None = None,
        force_regenerate_mapping: bool = False,
        upload_service: UploadService | None = None,
        document_parser: DocumentParser | None = None,
        claude_service: ClaudeService | None = None,
    ) -> tuple[InjectionResult, QualityCheckResult, ValuationReportData]:
        """Full pipeline entry point (docs/ARCHITECTURE.md's Data Flow): a
        session's uploaded documents -> parsed text -> Stage 1 extraction ->
        Stage 2 mapping (cached) -> Stage 3 injection -> quality check.

        Tier 1 official data (eASR) is an optional caller-supplied string —
        looking it up is a separate, manual step (D14/D15: it needs
        valuer-provided District/Taluka/Village inputs that can't be derived
        from the uploaded documents alone).
        """
        upload_service = upload_service or UploadService()
        document_parser = document_parser or DocumentParser()
        claude_service = claude_service or ClaudeService()

        template_paths = upload_service.list_session_files(session_id, UploadCategory.TEMPLATE)
        if len(template_paths) != 1:
            raise ReportServiceError(
                f"Expected exactly one uploaded template for session '{session_id}', "
                f"found {len(template_paths)}."
            )
        template_path = template_paths[0]

        document_paths = upload_service.list_session_files(
            session_id, UploadCategory.PROPERTY_DOCUMENT
        )
        if not document_paths:
            raise ReportServiceError(
                f"No property documents uploaded for session '{session_id}'."
            )

        document_texts = {
            Path(path).name: _parse_document(document_parser, path) for path in document_paths
        }

        extraction = claude_service.extract_valuation_data(
            document_texts=document_texts,
            tier1_official_data=tier1_official_data,
            valuation_date=valuation_date,
        )

        mapping, _ = self.get_or_create_mapping(
            template_path, claude_service=claude_service, force_regenerate=force_regenerate_mapping
        )
        injection = self.inject_data(template_path, mapping, extraction.data, output_path)
        quality_check = self.run_quality_check(mapping, extraction.data)
        return injection, quality_check, extraction.data

    def run_quality_check(
        self, mapping: dict[str, FieldMapping], data: ValuationReportData
    ) -> QualityCheckResult:
        """Scans scalar fields (before injection) for real values with no
        usable template location — repeating-group fields aren't covered
        (structurally different; would need the injected document itself,
        not just the mapping — a documented V1 limit)."""
        scalar_mapping, _ = _split_mapping(mapping)
        injection_failures: list[str] = []
        disclosed_unavailable: list[str] = []
        for field_name, field_mapping in scalar_mapping.items():
            value = _get_field_value(data, field_name)
            if value is None:
                continue
            if value == INFO_NOT_AVAILABLE:
                disclosed_unavailable.append(field_name)
            elif field_mapping.location_id is None:
                injection_failures.append(field_name)
        return QualityCheckResult(
            passed=not injection_failures,
            injection_failures=injection_failures,
            disclosed_unavailable=disclosed_unavailable,
        )


def _parse_document(document_parser: DocumentParser, path: str) -> str:
    extension = Path(path).suffix.lower()
    try:
        if extension == ".pdf":
            return document_parser.extract_pdf_text(path)
        if extension == ".docx":
            return document_parser.extract_docx_text(path)
        if extension in _OCR_EXTENSIONS:
            return document_parser.ocr_scanned_document(path)
    except DocumentParserError as exc:
        raise ReportServiceError(f"Could not parse '{path}': {exc}") from exc
    raise ReportServiceError(f"Unsupported document type for '{path}'.")


def _iter_block_items(document: Document):
    """Yields the document body's paragraphs and tables in document order.

    python-docx has no built-in combined iterator (Document.paragraphs and
    .tables are separate, unordered relative to each other) — this is the
    standard recipe for walking the body's actual XML child order.
    """
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _locate_structure(document: Document) -> tuple[list[Paragraph], list[Table]]:
    """Same document-order walk as extract_template_skeleton, but returning the
    live python-docx objects (not a serializable skeleton) for injection to
    mutate. Location IDs are positional, so this reproduces the same p{n}/
    t{n} indices as long as it runs before any structural edits (row cloning
    only ever appends, never shifting earlier indices — see _clone_row_after)."""
    paragraphs: list[Paragraph] = []
    tables: list[Table] = []
    for block in _iter_block_items(document):
        if isinstance(block, Paragraph):
            paragraphs.append(block)
        else:
            tables.append(block)
    return paragraphs, tables


def _resolve_location(
    location_id: str, paragraphs: list[Paragraph], tables: list[Table]
) -> Paragraph | None:
    if location_id.startswith("p"):
        try:
            index = int(location_id[1:])
        except ValueError:
            return None
        return paragraphs[index] if index < len(paragraphs) else None

    match = _TABLE_CELL_LOCATION_RE.match(location_id)
    if not match:
        return None
    table_idx, row_idx, col_idx = (int(group) for group in match.groups())
    if table_idx >= len(tables) or row_idx >= len(tables[table_idx].rows):
        return None
    cells = tables[table_idx].rows[row_idx].cells
    return cells[col_idx].paragraphs[0] if col_idx < len(cells) else None


def _set_paragraph_text(paragraph: Paragraph, text: str) -> None:
    """Mutates the paragraph's existing runs in place — the source of Stage 3's
    formatting-fidelity guarantee (D5). `paragraph.text = ...` / `cell.text =
    ...` are never used for injection: python-docx's setter for those drops
    every existing run and replaces it with one plain, unformatted run."""
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


def _get_field_value(data: ValuationReportData, dotted_name: str) -> str | None:
    obj: object = data
    for part in dotted_name.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj if isinstance(obj, str) else None


def _get_list_field(data: ValuationReportData, group_name: str) -> list[BaseModel]:
    """group_name is e.g. "comparable_evidence[]" — strips the marker to get
    the actual ValuationReportData attribute name."""
    value = getattr(data, group_name[: -len("[]")], None)
    return value if isinstance(value, list) else []


def _split_mapping(
    mapping: dict[str, FieldMapping],
) -> tuple[dict[str, FieldMapping], dict[str, dict[str, FieldMapping]]]:
    """Splits a Stage 2 mapping into scalar fields and repeating groups, keyed
    by group name (e.g. "comparable_evidence[]" -> {"location": FieldMapping(...), ...})."""
    scalar: dict[str, FieldMapping] = {}
    groups: dict[str, dict[str, FieldMapping]] = {}
    for name, field_mapping in mapping.items():
        if "[]." in name:
            group_name, sub_field = name.split("[].", 1)
            groups.setdefault(f"{group_name}[]", {})[sub_field] = field_mapping
        else:
            scalar[name] = field_mapping
    return scalar, groups


def _inject_repeating_group(
    tables: list[Table],
    group_name: str,
    group_mapping: dict[str, FieldMapping],
    items: list[BaseModel],
) -> tuple[list[str], list[str]]:
    filled_fields: list[str] = []
    unmapped_fields: list[str] = [f"{group_name}.{sub}" for sub in group_mapping if not items]

    col_by_subfield, anchor = _resolve_group_columns(tables, group_name, group_mapping, unmapped_fields)
    if anchor is None or not items:
        return filled_fields, unmapped_fields

    table_idx, row_idx = anchor
    prototype_tr = tables[table_idx].rows[row_idx]._tr
    anchor_tr = prototype_tr
    for item_index, item in enumerate(items):
        tr = prototype_tr if item_index == 0 else _clone_row_after(anchor_tr, prototype_tr)
        anchor_tr = tr
        row = _Row(tr, tables[table_idx])
        for sub_field, col_idx in col_by_subfield.items():
            value = getattr(item, sub_field, None)
            if not isinstance(value, str) or col_idx >= len(row.cells):
                continue
            _set_paragraph_text(row.cells[col_idx].paragraphs[0], value)
            filled_fields.append(f"{group_name}.{sub_field}[{item_index}]")

    return filled_fields, unmapped_fields


def _resolve_group_columns(
    tables: list[Table],
    group_name: str,
    group_mapping: dict[str, FieldMapping],
    unmapped_fields: list[str],
) -> tuple[dict[str, int], tuple[int, int] | None]:
    """Every subfield's mapped location already encodes (table, row, column) —
    the column position IS the column mapping, no separate format needed from
    Claude. Subfields must agree on one (table, row); anything else (missing
    location, wrong table/row) is reported and skipped rather than guessed."""
    resolved: dict[str, tuple[int, int, int]] = {}
    for sub_field, field_mapping in group_mapping.items():
        match = field_mapping.location_id and _TABLE_CELL_LOCATION_RE.match(field_mapping.location_id)
        if not match:
            unmapped_fields.append(f"{group_name}.{sub_field}")
            continue
        resolved[sub_field] = tuple(int(g) for g in match.groups())

    if not resolved:
        return {}, None

    anchors = [(t, r) for t, r, _ in resolved.values()]
    anchor = max(set(anchors), key=anchors.count)

    col_by_subfield: dict[str, int] = {}
    for sub_field, (table_idx, row_idx, col_idx) in resolved.items():
        if (table_idx, row_idx) == anchor:
            col_by_subfield[sub_field] = col_idx
        else:
            unmapped_fields.append(f"{group_name}.{sub_field}")

    return col_by_subfield, anchor


def _clone_row_after(anchor_tr, prototype_tr):
    """Duplicates the prototype row's XML and inserts it after anchor_tr —
    Stage 3 never builds a row from scratch, only clones an existing
    correctly-formatted one (D5)."""
    new_tr = copy.deepcopy(prototype_tr)
    anchor_tr.addnext(new_tr)
    return new_tr
