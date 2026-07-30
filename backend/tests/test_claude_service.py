import anthropic
import httpx
import pytest

from app.models.template_mapping import SkeletonLocation
from app.services.claude_service import ClaudeService, ClaudeServiceError

_REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


class _TextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _Usage:
    def __init__(self, input_tokens: int = 100, output_tokens: int = 50) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.content = [_TextBlock(text)]
        self.usage = _Usage()


_VALID_JSON = '{"property_identification": {"district": "Pune"}}'


@pytest.fixture(autouse=True)
def _isolated_usage_db(monkeypatch, tmp_path) -> None:
    """Claude calls now record usage (see usage_service.py) — keep that off the real db file."""
    monkeypatch.setattr("app.core.db.settings.DATABASE_PATH", str(tmp_path / "test.db"))


def test_raises_when_api_key_missing(monkeypatch) -> None:
    monkeypatch.setattr("app.services.claude_service.settings.ANTHROPIC_API_KEY", "")
    service = ClaudeService()
    with pytest.raises(ClaudeServiceError, match="ANTHROPIC_API_KEY"):
        service.extract_valuation_data(document_texts={})


class TestRetryLoop:
    """No real API call: ClaudeService._call_claude is swapped for a fake."""

    def test_retries_then_succeeds(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.claude_service.settings.ANTHROPIC_API_KEY", "sk-test")
        service = ClaudeService(max_retries=2, retry_delay_seconds=0)

        calls = {"count": 0}

        def fake_call_claude(_prompt, _tools, on_status=None):
            calls["count"] += 1
            if calls["count"] < 3:
                raise anthropic.APIConnectionError(request=_REQUEST)
            return _FakeResponse(_VALID_JSON)

        monkeypatch.setattr(service, "_call_claude", fake_call_claude)

        result = service.extract_valuation_data(document_texts={"a.pdf": "text"})

        assert calls["count"] == 3
        assert result.data.property_identification.district == "Pune"
        assert result.input_tokens == 100
        assert result.output_tokens == 50

    def test_raises_claude_service_error_after_exhausting_retries(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.claude_service.settings.ANTHROPIC_API_KEY", "sk-test")
        service = ClaudeService(max_retries=2, retry_delay_seconds=0)

        def always_fails(_prompt, _tools, on_status=None):
            raise anthropic.APIConnectionError(request=_REQUEST)

        monkeypatch.setattr(service, "_call_claude", always_fails)

        with pytest.raises(ClaudeServiceError, match="after 3 attempts"):
            service.extract_valuation_data(document_texts={})

    def test_non_retryable_api_error_short_circuits(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.claude_service.settings.ANTHROPIC_API_KEY", "sk-test")
        service = ClaudeService(max_retries=2, retry_delay_seconds=0)

        calls = {"count": 0}

        def fails_auth(_prompt, _tools, on_status=None):
            calls["count"] += 1
            response = httpx.Response(401, request=_REQUEST)
            raise anthropic.AuthenticationError("invalid key", response=response, body=None)

        monkeypatch.setattr(service, "_call_claude", fails_auth)

        with pytest.raises(ClaudeServiceError, match="invalid key"):
            service.extract_valuation_data(document_texts={})

        assert calls["count"] == 1  # no retry for a non-transient API error

    def test_raises_on_malformed_json_response(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.claude_service.settings.ANTHROPIC_API_KEY", "sk-test")
        service = ClaudeService(max_retries=2, retry_delay_seconds=0)

        monkeypatch.setattr(
            service, "_call_claude", lambda _prompt, _tools, on_status=None: _FakeResponse("not json")
        )

        with pytest.raises(ClaudeServiceError, match="did not match the expected schema"):
            service.extract_valuation_data(document_texts={})

    def test_strips_markdown_code_fence(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.claude_service.settings.ANTHROPIC_API_KEY", "sk-test")
        service = ClaudeService(max_retries=2, retry_delay_seconds=0)

        fenced = f"```json\n{_VALID_JSON}\n```"
        monkeypatch.setattr(
            service, "_call_claude", lambda _prompt, _tools, on_status=None: _FakeResponse(fenced)
        )

        result = service.extract_valuation_data(document_texts={})
        assert result.data.property_identification.district == "Pune"

    def test_retries_on_a_blank_text_block(self, monkeypatch) -> None:
        """The exact D27 follow-up bug: a text block present but empty (a
        truncated/blank generation) used to fail immediately with a cryptic
        json.loads error and no retry at all. It should now retry like any
        other transient failure and succeed once a real response arrives."""
        monkeypatch.setattr("app.services.claude_service.settings.ANTHROPIC_API_KEY", "sk-test")
        service = ClaudeService(max_retries=2, retry_delay_seconds=0)

        calls = {"count": 0}

        def fake_call_claude(_prompt, _tools, on_status=None):
            calls["count"] += 1
            if calls["count"] < 2:
                return _FakeResponse("")  # blank final text block
            return _FakeResponse(_VALID_JSON)

        monkeypatch.setattr(service, "_call_claude", fake_call_claude)

        result = service.extract_valuation_data(document_texts={"a.pdf": "text"})

        assert calls["count"] == 2
        assert result.data.property_identification.district == "Pune"

    def test_raises_a_clear_error_when_every_attempt_is_blank(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.claude_service.settings.ANTHROPIC_API_KEY", "sk-test")
        service = ClaudeService(max_retries=1, retry_delay_seconds=0)

        monkeypatch.setattr(
            service, "_call_claude", lambda _prompt, _tools, on_status=None: _FakeResponse("")
        )

        with pytest.raises(ClaudeServiceError, match="after 2 attempts"):
            service.extract_valuation_data(document_texts={})

    def test_retries_when_no_text_block_at_all(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.claude_service.settings.ANTHROPIC_API_KEY", "sk-test")
        service = ClaudeService(max_retries=2, retry_delay_seconds=0)

        calls = {"count": 0}

        class _NoTextResponse:
            content: list = []
            usage = _Usage()

        def fake_call_claude(_prompt, _tools, on_status=None):
            calls["count"] += 1
            if calls["count"] < 2:
                return _NoTextResponse()
            return _FakeResponse(_VALID_JSON)

        monkeypatch.setattr(service, "_call_claude", fake_call_claude)

        result = service.extract_valuation_data(document_texts={"a.pdf": "text"})

        assert calls["count"] == 2
        assert result.data.property_identification.district == "Pune"


class _FakeStreamEvent:
    def __init__(self, block_type: str) -> None:
        self.type = "content_block_start"
        self.content_block = type("Block", (), {"type": block_type})()


class TestReportStreamStatus:
    """_report_stream_status is the logic behind on_status (D28-adjacent
    progress work, 2026-07-30) — tested directly against fake events rather
    than mocking the whole Anthropic stream/client."""

    def test_reports_a_label_per_content_block(self) -> None:
        service = ClaudeService()
        received: list[tuple[str, int]] = []
        events = [_FakeStreamEvent("thinking"), _FakeStreamEvent("server_tool_use"), _FakeStreamEvent("text")]

        service._report_stream_status(events, lambda label, count: received.append((label, count)))

        assert received == [
            ("Reasoning about the property", 1),
            ("Searching the web for comparables", 2),
            ("Drafting the extracted data", 3),
        ]

    def test_unknown_block_type_gets_a_generic_label(self) -> None:
        service = ClaudeService()
        received: list[tuple[str, int]] = []

        service._report_stream_status(
            [_FakeStreamEvent("something_new")], lambda label, count: received.append((label, count))
        )

        assert received == [("Processing", 1)]

    def test_swallows_a_mid_stream_error_without_crashing(self) -> None:
        service = ClaudeService()
        received: list[tuple[str, int]] = []

        def bad_events():
            yield _FakeStreamEvent("thinking")
            raise RuntimeError("boom")

        service._report_stream_status(bad_events(), lambda label, count: received.append((label, count)))

        assert received == [("Reasoning about the property", 1)]


class TestMapTemplateFields:
    def test_parses_mapping_response(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.claude_service.settings.ANTHROPIC_API_KEY", "sk-test")
        service = ClaudeService(max_retries=2, retry_delay_seconds=0)
        mapping_json = (
            '{"property_identification.district": {"location_id": "t0r0c1", "confidence": "high"},'
            ' "property_identification.pin_code": {"location_id": null, "status": "not_present"}}'
        )
        monkeypatch.setattr(
            service, "_call_claude", lambda _prompt, _tools, on_status=None: _FakeResponse(mapping_json)
        )

        skeleton = [SkeletonLocation(location_id="p0", type="paragraph", text="District")]
        result = service.map_template_fields(skeleton)

        assert result["property_identification.district"].location_id == "t0r0c1"
        assert result["property_identification.district"].confidence == "high"
        assert result["property_identification.pin_code"].status == "not_present"

    def test_uses_no_tools_unlike_extraction(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.claude_service.settings.ANTHROPIC_API_KEY", "sk-test")
        service = ClaudeService(max_retries=0, retry_delay_seconds=0)
        seen_tools = {}

        def fake_call_claude(_prompt, tools, on_status=None):
            seen_tools["tools"] = tools
            return _FakeResponse("{}")

        monkeypatch.setattr(service, "_call_claude", fake_call_claude)

        service.map_template_fields([])

        assert seen_tools["tools"] == []
