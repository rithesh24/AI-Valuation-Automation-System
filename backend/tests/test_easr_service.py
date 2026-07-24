import asyncio

import pytest
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from pydantic import ValidationError

from app.services.easr_service import (
    EASRGuidelineResult,
    EASRSearchInput,
    EASRService,
    EASRServiceError,
)

RURAL_TABLE_HTML = """
<table id="ctl00_ContentPlaceHolder5_ruralDataGrid">
  <tr><th>Assessment Type</th><th>Assessment Range</th><th>Rate Rs/-</th></tr>
  <tr><td>जिरायत शेत जमिन</td><td>0-1.25</td><td>4265500</td></tr>
  <tr><td>बिनशेती जमीनी/भूखंड</td><td></td><td>6750</td></tr>
</table>
"""

URBAN_TABLE_HTML = """
<table id="ctl00_ContentPlaceHolder5_grdUrbanSubZoneWiseRate">
  <tr>
    <th>Select</th><th>उपविभाग</th><th>खुली जमीन</th><th>निवासी सदनिका</th>
    <th>ऑफ़ीस</th><th>दुकाने</th><th>औद्योगिक</th><th>एकक (Rs./)</th>
  </tr>
  <tr>
    <td>SurveyNo</td><td>5/52-मुंबई पुणे महामार्ग</td><td>17780</td><td>70310</td>
    <td>80850</td><td>123340</td><td>0</td><td>चौ. मीटर</td>
  </tr>
  <tr>
    <td>SurveyNo</td><td>5/53-काळभोर नगर</td><td>19030</td><td>60420</td>
    <td>69510</td><td>138040</td><td>0</td><td>चौ. मीटर</td>
  </tr>
</table>
"""


def _run(coro):
    return asyncio.run(coro)


async def _check_chromium_available() -> bool:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            await browser.close()
            return True
    except Exception:
        return False


PLAYWRIGHT_BROWSERS_AVAILABLE = _run(_check_chromium_available())

requires_playwright_browsers = pytest.mark.skipif(
    not PLAYWRIGHT_BROWSERS_AVAILABLE,
    reason="Chromium not installed (run: playwright install chromium)",
)


class TestModels:
    def test_search_input_requires_core_fields(self):
        with pytest.raises(ValidationError):
            EASRSearchInput()  # type: ignore[call-arg]

    def test_search_input_survey_no_is_optional(self):
        search_input = EASRSearchInput(year="2026-2027", district="Pune", taluka="हवेली", village="आकुर्डी")
        assert search_input.survey_no is None

    def test_guideline_result_found_false_has_empty_rows_by_default(self):
        result = EASRGuidelineResult(
            search_input=EASRSearchInput(year="2026-2027", district="Pune", taluka="x", village="y"),
            found=False,
            source="IGR Maharashtra e ASR (igreval), accessed 2026-07-24",
            accessed_at="2026-07-24T00:00:00Z",
        )
        assert result.rows == []
        assert result.columns == []


class TestRetryLoop:
    """No real browser involved: EASRService._run_search is swapped for a fake."""

    def test_retries_then_succeeds(self, monkeypatch):
        service = EASRService(max_retries=2, retry_delay_seconds=0)
        search_input = EASRSearchInput(year="2026-2027", district="Pune", taluka="हवेली", village="आकुर्डी")
        expected = EASRGuidelineResult(
            search_input=search_input,
            found=True,
            source="IGR Maharashtra e ASR (igreval), accessed 2026-07-24",
            accessed_at="2026-07-24T00:00:00Z",
        )

        calls = {"count": 0}

        async def fake_run_search(_search_input):
            calls["count"] += 1
            if calls["count"] < 3:
                raise PlaywrightTimeoutError("timed out")
            return expected

        monkeypatch.setattr(service, "_run_search", fake_run_search)
        sleep_calls = []

        async def no_op_sleep(seconds):
            sleep_calls.append(seconds)

        monkeypatch.setattr(asyncio, "sleep", no_op_sleep)

        result = _run(service.fetch_guideline_value(search_input))

        assert result is expected
        assert calls["count"] == 3
        assert len(sleep_calls) == 2  # slept before attempt 2 and attempt 3

    def test_raises_easr_service_error_after_exhausting_retries(self, monkeypatch):
        service = EASRService(max_retries=2, retry_delay_seconds=0)
        search_input = EASRSearchInput(year="2026-2027", district="Pune", taluka="हवेली", village="आकुर्डी")

        async def always_fails(_search_input):
            raise PlaywrightError("navigation failed")

        monkeypatch.setattr(service, "_run_search", always_fails)

        async def no_op_sleep(seconds):
            return None

        monkeypatch.setattr(asyncio, "sleep", no_op_sleep)

        with pytest.raises(EASRServiceError, match="after 3 attempts"):
            _run(service.fetch_guideline_value(search_input))

    def test_non_retryable_error_short_circuits(self, monkeypatch):
        service = EASRService(max_retries=2, retry_delay_seconds=0)
        search_input = EASRSearchInput(year="2026-2027", district="Pune", taluka="हवेली", village="आकुर्डी")

        calls = {"count": 0}

        async def fails_with_bad_input(_search_input):
            calls["count"] += 1
            raise EASRServiceError("'x' is not a valid option")

        monkeypatch.setattr(service, "_run_search", fails_with_bad_input)

        with pytest.raises(EASRServiceError, match="not a valid option"):
            _run(service.fetch_guideline_value(search_input))

        assert calls["count"] == 1  # no retry attempted for a non-Playwright error


@requires_playwright_browsers
class TestTableParsing:
    """Real headless Chromium against local fixture HTML — no live-portal network calls."""

    def test_parses_rural_table(self):
        async def run():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_content(RURAL_TABLE_HTML)
                service = EASRService()
                table = page.locator("#ctl00_ContentPlaceHolder5_ruralDataGrid")
                columns, rows = await service._parse_table(table)
                await browser.close()
                return columns, rows

        columns, rows = _run(run())
        assert columns == ["Assessment Type", "Assessment Range", "Rate Rs/-"]
        assert rows[0] == {
            "Assessment Type": "जिरायत शेत जमिन",
            "Assessment Range": "0-1.25",
            "Rate Rs/-": "4265500",
        }
        # blank cell -> None, never an empty string
        assert rows[1]["Assessment Range"] is None

    def test_parses_urban_table_and_filters_by_survey_no(self):
        async def run():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_content(URBAN_TABLE_HTML)
                service = EASRService()
                table = page.locator("#ctl00_ContentPlaceHolder5_grdUrbanSubZoneWiseRate")
                columns, rows = await service._parse_table(table)
                filtered = service._filter_by_survey_no(columns, rows, "5/53")
                await browser.close()
                return columns, rows, filtered

        columns, rows, filtered = _run(run())
        assert len(rows) == 2
        assert len(filtered) == 1
        assert filtered[0]["उपविभाग"] == "5/53-काळभोर नगर"
        assert filtered[0]["खुली जमीन"] == "19030"
