import asyncio
import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page, async_playwright
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# Real portal + element IDs confirmed by driving the live site with Playwright
# (see docs/DECISIONS.md D14) — this is eASR 1.9, the classic dropdown-based
# version, not the map-click "eASR 2.0 (Beta)" that eASRCommon.aspx redirects
# to when no district is supplied.
_BASE_URL = "https://easr.igrmaharashtra.gov.in/eASRCommon.aspx"
_YEAR_SELECT = "#ctl00_ContentPlaceHolder5_ddlYear"
_TALUKA_SELECT = "#ctl00_ContentPlaceHolder5_ddlTaluka"
_VILLAGE_SELECT = "#ctl00_ContentPlaceHolder5_ddlVillage"
_RURAL_TABLE = "#ctl00_ContentPlaceHolder5_ruralDataGrid"
_URBAN_TABLE = "#ctl00_ContentPlaceHolder5_grdUrbanSubZoneWiseRate"
_RESULT_TABLE = f"{_RURAL_TABLE}, {_URBAN_TABLE}"

_SOURCE_LABEL = "IGR Maharashtra e ASR (igreval)"


class EASRServiceError(Exception):
    """Raised when eASR retrieval fails outright. Message is safe to show the user."""


class EASRSearchInput(BaseModel):
    year: str
    """e.g. "2026-2027" — the hyphen is optional, stripped internally to match the portal."""
    district: str
    """Must match the portal's own `hDistName` identifier exactly (confirmed working: "Pune",
    "Thane", "Nagpur"). Not every district's identifier is known yet — see D14."""
    taluka: str
    """Marathi label, must match a real option in the portal's Taluka dropdown."""
    village: str
    """Marathi label, must match a real option in the portal's Village dropdown."""
    survey_no: str | None = None
    """Narrows results to rows whose sub-division text contains this value. Only meaningful for
    urban/municipal-corporation villages; rural villages have no survey-number concept — see D14."""


class EASRGuidelineResult(BaseModel):
    search_input: EASRSearchInput
    found: bool
    """True if at least one row is being returned; False = confirmed empty/no-match result."""
    columns: list[str] = []
    """The scraped header row, in order, exactly as shown on the portal (rural and urban
    villages show different tables with different columns — this is not a fixed schema)."""
    rows: list[dict[str, str | None]] = []
    """Each row keyed by its column header. A blank/missing cell is None, never a guessed value."""
    preamble: dict[str, str] = {}
    """Labeled values shown above the table, e.g. {"Vibhag Number": "6"} for rural villages."""
    source: str
    accessed_at: datetime
    note: str | None = None
    """Set when a result is incomplete for a documented reason (see D14's pagination limitation)."""


class EASRService:
    def __init__(
        self,
        headless: bool | None = None,
        timeout_ms: int | None = None,
        max_retries: int | None = None,
        retry_delay_seconds: float | None = None,
    ) -> None:
        self._headless = settings.EASR_HEADLESS if headless is None else headless
        self._timeout_ms = timeout_ms or settings.EASR_TIMEOUT_MS
        self._max_retries = settings.EASR_MAX_RETRIES if max_retries is None else max_retries
        self._retry_delay_seconds = (
            settings.EASR_RETRY_DELAY_SECONDS if retry_delay_seconds is None else retry_delay_seconds
        )

    async def fetch_guideline_value(self, search_input: EASRSearchInput) -> EASRGuidelineResult:
        """Retrieves guideline rates for a survey/subzone. Retries on transient Playwright
        failures (timeouts, navigation errors); raises EASRServiceError immediately for
        non-retryable failures (bad input, missing Chromium) — see docs/DECISIONS.md D14
        for the full retryable/non-retryable contract.
        """
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._run_search(search_input)
            except PlaywrightError as exc:
                last_error = exc
                logger.warning(
                    "eASR lookup attempt %s/%s failed: %s",
                    attempt + 1,
                    self._max_retries + 1,
                    exc,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_delay_seconds * (attempt + 1))
        raise EASRServiceError(
            f"Could not retrieve eASR data after {self._max_retries + 1} attempts: {last_error}"
        ) from last_error

    async def _run_search(self, search_input: EASRSearchInput) -> EASRGuidelineResult:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=self._headless)
            except Exception as exc:
                raise EASRServiceError(
                    "Playwright's Chromium browser is not installed. Run "
                    "'playwright install chromium' in the backend environment."
                ) from exc

            try:
                page = await browser.new_page()
                page.set_default_timeout(self._timeout_ms)
                return await self._search_on_page(page, search_input)
            finally:
                await browser.close()

    async def _search_on_page(self, page: Page, search_input: EASRSearchInput) -> EASRGuidelineResult:
        url = f"{_BASE_URL}?hDistName={quote(search_input.district)}"
        await page.goto(url, wait_until="networkidle")
        # The page keeps settling briefly after "networkidle" fires (observed empirically
        # against the live portal); querying the DOM immediately can hit a destroyed
        # execution context if a late reflow/redirect is still in flight.
        await page.wait_for_timeout(1000)

        if await page.locator(_TALUKA_SELECT).count() == 0:
            raise EASRServiceError(
                f"District '{search_input.district}' was not recognized by the eASR portal "
                "(no search form rendered). Verify the exact district identifier it expects."
            )

        await self._select_by_label(page, _YEAR_SELECT, search_input.year.replace("-", ""))
        await self._select_by_label(page, _TALUKA_SELECT, search_input.taluka)

        await page.wait_for_function(
            """(sel) => {
                const el = document.querySelector(sel);
                return el && el.options.length > 1;
            }""",
            arg=_VILLAGE_SELECT,
        )
        await self._select_by_label(page, _VILLAGE_SELECT, search_input.village)

        await page.wait_for_selector(_RESULT_TABLE)

        accessed_at = datetime.now(timezone.utc)
        source = f"{_SOURCE_LABEL}, accessed {accessed_at.date().isoformat()}"

        rural_table = page.locator(_RURAL_TABLE)
        if await rural_table.count() > 0:
            columns, rows = await self._parse_table(rural_table)
            return EASRGuidelineResult(
                search_input=search_input,
                found=bool(rows),
                columns=columns,
                rows=rows,
                preamble=await self._extract_vibhag_number(page),
                source=source,
                accessed_at=accessed_at,
            )

        urban_table = page.locator(_URBAN_TABLE)
        columns, rows = await self._parse_table(urban_table)

        note = None
        if search_input.survey_no:
            matched = self._filter_by_survey_no(columns, rows, search_input.survey_no)
            if not matched and rows:
                note = (
                    "No row on the first results page matched the given survey number. This "
                    "village has additional result pages, which this version does not yet "
                    "paginate through — see docs/DECISIONS.md D14."
                )
            rows = matched

        return EASRGuidelineResult(
            search_input=search_input,
            found=bool(rows),
            columns=columns,
            rows=rows,
            source=source,
            accessed_at=accessed_at,
            note=note,
        )

    async def _select_by_label(self, page: Page, select_selector: str, target_label: str) -> None:
        """Selects a <select> option by its trimmed visible text.

        Not Playwright's built-in label match: portal option text has inconsistent
        surrounding whitespace (e.g. "अष्टापूर " vs "नागपूर    "), which would make
        exact-label matching fail unpredictably.
        """
        # Every dropdown on this ASP.NET WebForms page triggers a postback (AutoPostBack),
        # including ones that don't visibly change anything (e.g. re-selecting the
        # already-selected Year). Querying the DOM immediately after select_option() can
        # race a postback still in flight and hit a destroyed execution context — retry
        # rather than treat that as a real failure.
        select = page.locator(select_selector)
        options = select.locator("option")
        count = 0
        for settle_attempt in range(3):
            try:
                count = await options.count()
                break
            except PlaywrightError as exc:
                if "Execution context was destroyed" not in str(exc) or settle_attempt == 2:
                    raise
                await page.wait_for_timeout(500)
        target = target_label.strip()
        for i in range(count):
            option = options.nth(i)
            text = (await option.inner_text()).strip()
            if text == target:
                value = await option.get_attribute("value")
                await select.select_option(value=value)
                return
        raise EASRServiceError(
            f"'{target_label}' is not a valid option for {select_selector} on the eASR portal."
        )

    async def _parse_table(self, table: Locator) -> tuple[list[str], list[dict[str, str | None]]]:
        rows = table.locator("tr")
        row_count = await rows.count()
        if row_count == 0:
            return [], []

        header_texts = await rows.nth(0).locator("th, td").all_inner_texts()
        columns = [h.strip() for h in header_texts]

        data_rows: list[dict[str, str | None]] = []
        for i in range(1, row_count):
            cell_texts = [c.strip() for c in await rows.nth(i).locator("td").all_inner_texts()]
            if not any(cell_texts):
                continue
            row: dict[str, str | None] = {
                columns[idx]: (cell_texts[idx] if idx < len(cell_texts) and cell_texts[idx] else None)
                for idx in range(len(columns))
            }
            data_rows.append(row)
        return columns, data_rows

    def _filter_by_survey_no(
        self, columns: list[str], rows: list[dict[str, str | None]], survey_no: str
    ) -> list[dict[str, str | None]]:
        # The sub-division column (उपविभाग) is always the second column, right after "Select",
        # and embeds the survey number in its text (e.g. "5/52-मुंबई पुणे महामार्ग ...").
        subzone_column = columns[1] if len(columns) > 1 else None
        if not subzone_column:
            return rows
        return [
            row
            for row in rows
            if row.get(subzone_column) and survey_no in row[subzone_column]
        ]

    async def _extract_vibhag_number(self, page: Page) -> dict[str, str]:
        try:
            text = await page.get_by_text("Vibhag Number", exact=False).first.inner_text()
        except PlaywrightError:
            return {}
        match = re.search(r"Vibhag Number\D*(\d+)", text)
        return {"Vibhag Number": match.group(1)} if match else {}
