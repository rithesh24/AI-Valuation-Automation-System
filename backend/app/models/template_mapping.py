"""Stage 2 (Template Mapping) data shapes (D5), shared between report_service.py
(produces SkeletonLocation, consumes FieldMapping) and claude_service.py /
prompt_builder.py (consumes SkeletonLocation, produces FieldMapping) — living
here rather than in either service avoids a circular import between them.
"""

from pydantic import BaseModel


class SkeletonLocation(BaseModel):
    location_id: str
    type: str
    """"paragraph" or "table_cell"."""
    text: str
    context: list[str] = []
    """The "nearby label text" signal (docs/ARCHITECTURE.md): the previous
    non-blank paragraph's text for a paragraph location, or every other
    cell's text in the same table row for a table-cell location."""


class FieldMapping(BaseModel):
    location_id: str | None = None
    confidence: str | None = None
    """"high" / "medium" / "low", set when location_id is not None."""
    status: str | None = None
    """"not_present" when location_id is None."""
