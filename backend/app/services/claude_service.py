"""Only this module communicates with Claude (docs/ARCHITECTURE.md)."""

import json
import logging
import time
from datetime import date

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


class ClaudeServiceError(Exception):
    """Raised when a Claude request fails outright. Message is safe to show the user."""


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
    ) -> ExtractionResult:
        """Runs Stage 1 (Extraction): documents + Tier 1 data -> ValuationReportData."""
        if not settings.ANTHROPIC_API_KEY:
            raise ClaudeServiceError(
                "ANTHROPIC_API_KEY is not configured. Set it from the app's Settings screen."
            )

        prompt = self._prompt_builder.build_extraction_prompt(
            document_texts=document_texts,
            tier1_official_data=tier1_official_data,
            valuation_date=valuation_date,
        )
        response = self._send_with_retries(prompt, tools=[_WEB_SEARCH_TOOL])
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

    def _send_with_retries(self, prompt: str, tools: list[dict]):
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return self._call_claude(prompt, tools)
            except _RETRYABLE_ERRORS as exc:
                last_error = exc
                logger.warning("Claude request attempt %d failed: %s", attempt + 1, exc)
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay_seconds)
            except anthropic.APIError as exc:
                raise ClaudeServiceError(f"Claude API request failed: {exc}") from exc

        raise ClaudeServiceError(
            f"Claude request failed after {self._max_retries + 1} attempts: {last_error}"
        )

    def _call_claude(self, prompt: str, tools: list[dict]):
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
            return stream.get_final_message()

    def _response_text(self, response) -> str:
        text_blocks = [block.text for block in response.content if block.type == "text"]
        if not text_blocks:
            raise ClaudeServiceError("Claude returned no text content.")
        return _strip_code_fence(text_blocks[-1].strip())


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)
