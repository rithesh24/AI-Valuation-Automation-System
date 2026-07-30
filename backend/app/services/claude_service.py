"""Only this module communicates with Claude (docs/ARCHITECTURE.md)."""

import json
import logging
import time
from datetime import date
from typing import Callable

import anthropic
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.models.template_mapping import FieldMapping, SkeletonLocation
from app.models.valuation_schema import ValuationReportData
from app.services.prompt_builder import PromptBuilder
from app.services.usage_service import UsageService

logger = logging.getLogger(__name__)

_MAX_OUTPUT_TOKENS = 64000
# Anthropic's hosted web-search server tool (D8 Tier 2 comparable research).
# _20260209 adds server-side dynamic filtering (Sonnet 5/Opus 4.6+); bump this
# if the API rejects it or Anthropic ships a newer variant.
_WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}
_RETRYABLE_ERRORS = (
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)
# Best-effort labels for stream content-block types, surfaced as progress
# status (docs/PROGRESS.md, 2026-07-30) — same total tokens either way,
# streaming just lets us read events we'd otherwise discard until the end.
_STREAM_STATUS_LABELS = {
    "thinking": "Reasoning about the property",
    "text": "Drafting the extracted data",
    "server_tool_use": "Searching the web for comparables",
    "tool_use": "Searching the web for comparables",
    "web_search_tool_result": "Reviewing search results",
}


class ClaudeServiceError(Exception):
    """Raised when a Claude request fails outright. Message is safe to show the user."""


class _EmptyResponseError(Exception):
    """Internal only: Claude replied but gave no usable text (D27 follow-up).
    Treated as retryable in _send_with_retries, not raised out to callers directly."""


class ExtractionResult(BaseModel):
    data: ValuationReportData
    input_tokens: int
    output_tokens: int


class ClaudeService:
    def __init__(
        self,
        max_retries: int | None = None,
        retry_delay_seconds: float | None = None,
    ) -> None:
        self._prompt_builder = PromptBuilder()
        self._usage_service = UsageService()
        self._max_retries = (
            max_retries if max_retries is not None else settings.ANTHROPIC_MAX_RETRIES
        )
        self._retry_delay_seconds = (
            retry_delay_seconds
            if retry_delay_seconds is not None
            else settings.ANTHROPIC_RETRY_DELAY_SECONDS
        )

    def extract_valuation_data(
        self,
        document_texts: dict[str, str],
        tier1_official_data: str | None = None,
        valuation_date: date | None = None,
        on_status: Callable[[str, int], None] | None = None,
    ) -> ExtractionResult:
        """Runs Stage 1 (Extraction): documents + Tier 1 data -> ValuationReportData.

        `on_status(label, block_count)`, if given, is called as the stream's
        content blocks arrive (thinking / web search / drafting) — this is
        the slow, variable-duration call, so it's the one worth surfacing
        progress for.
        """
        if not settings.ANTHROPIC_API_KEY:
            raise ClaudeServiceError(
                "ANTHROPIC_API_KEY is not configured. Set it from the app's Settings screen."
            )

        prompt = self._prompt_builder.build_extraction_prompt(
            document_texts=document_texts,
            tier1_official_data=tier1_official_data,
            valuation_date=valuation_date,
        )
        response = self._send_with_retries(prompt, tools=[_WEB_SEARCH_TOOL], on_status=on_status)
        raw_text = self._response_text(response)
        try:
            data = ValuationReportData.model_validate(json.loads(raw_text))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ClaudeServiceError(f"Claude response did not match the expected schema: {exc}") from exc

        self._usage_service.record_usage(
            response.usage.input_tokens, response.usage.output_tokens, stage="extraction"
        )
        return ExtractionResult(
            data=data,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    def map_template_fields(self, skeleton: list[SkeletonLocation]) -> dict[str, FieldMapping]:
        """Runs Stage 2 (Template Mapping): schema fields + template skeleton -> locations."""
        if not settings.ANTHROPIC_API_KEY:
            raise ClaudeServiceError(
                "ANTHROPIC_API_KEY is not configured. Set it from the app's Settings screen."
            )

        prompt = self._prompt_builder.build_mapping_prompt(skeleton)
        response = self._send_with_retries(prompt, tools=[])
        raw_text = self._response_text(response)
        try:
            payload: dict = json.loads(raw_text)
            mapping = {name: FieldMapping.model_validate(value) for name, value in payload.items()}
        except (json.JSONDecodeError, ValidationError, AttributeError) as exc:
            raise ClaudeServiceError(f"Claude response did not match the expected schema: {exc}") from exc

        self._usage_service.record_usage(
            response.usage.input_tokens, response.usage.output_tokens, stage="mapping"
        )
        return mapping

    def _send_with_retries(
        self,
        prompt: str,
        tools: list[dict],
        on_status: Callable[[str, int], None] | None = None,
    ):
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._call_claude(prompt, tools, on_status=on_status)
                self._response_text(response)  # raises _EmptyResponseError on a blank/truncated reply
                return response
            except _RETRYABLE_ERRORS as exc:
                last_error = exc
                logger.warning("Claude request attempt %d failed: %s", attempt + 1, exc)
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay_seconds)
            except _EmptyResponseError as exc:
                # A blank/truncated final text block (D27 follow-up, 2026-07-30) usually
                # means the model ran out of budget on a slow turn — not a permanent
                # failure, so it gets the same retry treatment as a transient API error.
                last_error = exc
                logger.warning("Claude request attempt %d returned an unusable response: %s", attempt + 1, exc)
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay_seconds)
            except anthropic.APIError as exc:
                raise ClaudeServiceError(f"Claude API request failed: {exc}") from exc

        raise ClaudeServiceError(
            f"Claude request failed after {self._max_retries + 1} attempts: {last_error}"
        )

    def _call_claude(
        self,
        prompt: str,
        tools: list[dict],
        on_status: Callable[[str, int], None] | None = None,
    ):
        """Sonnet 5 runs adaptive thinking by default (no `thinking` param set —
        that's a deliberate choice, not an oversight) and Stage 1's web-search
        tool can chain several search/code-execution rounds — both eat into
        max_tokens before the final JSON text block is written. 64000 (up from
        the original 8192) gives real headroom; streaming is required for any
        max_tokens this large to avoid an SDK HTTP timeout on a slow turn."""
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        with client.messages.stream(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=_MAX_OUTPUT_TOKENS,
            tools=tools,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            if on_status:
                self._report_stream_status(stream, on_status)
            return stream.get_final_message()

    def _report_stream_status(self, stream, on_status: Callable[[str, int], None]) -> None:
        """Best-effort status from raw stream events (block count + type) —
        never lets a status-reporting issue break the actual extraction,
        since this is UX only, not the result."""
        block_count = 0
        try:
            for event in stream:
                if getattr(event, "type", None) != "content_block_start":
                    continue
                block_count += 1
                block_type = getattr(event.content_block, "type", "")
                on_status(_STREAM_STATUS_LABELS.get(block_type, "Processing"), block_count)
        except Exception:
            logger.warning("Progress-status streaming failed; continuing without it.", exc_info=True)

    def _response_text(self, response) -> str:
        text_blocks = [block.text for block in response.content if block.type == "text"]
        if not text_blocks:
            raise _EmptyResponseError("Claude returned no text content.")
        text = _strip_code_fence(text_blocks[-1].strip())
        if not text:
            # The exact D27 follow-up bug (docs/DECISIONS.md, 2026-07-30): a text
            # block was present but blank — json.loads("") gives the cryptic
            # "Expecting value: line 1 column 1 (char 0)" with no clue why.
            raise _EmptyResponseError("Claude returned a blank text block (likely truncated).")
        return text


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)
