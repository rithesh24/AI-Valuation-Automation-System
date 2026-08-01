import asyncio
import difflib
import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page, async_playwright
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# Real portal + element IDs confirmed by driving the live site with Playwright.
# Switched from eASR 1.9 to eASR 2.0 (see docs/DECISIONS.md D34): 2.0 renders
# District/Taluka/Village in English (1.9 only offered Marathi labels), which
# is what lets extracted document text be matched against dropdown options
# without a Marathi lookup table. Same ASP.NET control IDs carried over from
# 1.9 for Year/Taluka/Village/rural-table; District and the urban-table id
# changed — reconfirmed live, not assumed. Note: the portal's own banner
# labels 2.0 "Beta, verify with eASR 1.9" — accepted per D34.
_BASE_URL = "https://igreval.maharashtra.gov.in/eASR2.0/eASRCommon.aspx"
_YEAR_SELECT = "#ctl00_ContentPlaceHolder5_ddlYear"
_TALUKA_SELECT = "#ctl00_ContentPlaceHolder5_ddlTaluka"
_DISTRICT_SELECT = "#ctl00_ContentPlaceHolder5_ddlDistrict"
"""Always present once a valid hDistName is supplied. Usually pre-resolved to a
single option (e.g. "Pune"); districts that split into sub-entries (currently
only Mumbai: "Mumbai City" / "Mumbai Suburban") render more than one option,
in which case `EASRSearchInput.district_option` must select between them."""
_VILLAGE_SELECT = "#ctl00_ContentPlaceHolder5_ddlVillage"
_RURAL_TABLE = "#ctl00_ContentPlaceHolder5_ruralDataGrid"
_URBAN_TABLE = "#ctl00_ContentPlaceHolder5_dg_Valuation2_0"
_RESULT_TABLE = f"{_RURAL_TABLE}, {_URBAN_TABLE}"

_SOURCE_LABEL = "IGR Maharashtra e ASR (igreval)"

_MATCH_CUTOFF = 0.6
"""difflib similarity threshold for EASRService._best_match's typo-tolerant fallback
(substring containment is tried first and preferred) — see D37."""

_KNOWN_DISTRICT_CODES: dict[str, str] = {
    "mumbai suburban": "Bombaymains",
    "mumbai city": "Bombaymains",
    "mumbai": "Bombaymains",
    "pune": "Pune",
    "thane": "Thane",
    "nagpur": "Nagpur",
}
"""Free-text district name (lowercased, substring match) -> portal hDistName code, seeded
with the identifiers already confirmed working (D14/D30/D34). Extend as new districts are
confirmed live — never guess an unconfirmed code (D14's original reasoning still applies)."""

# --- eASR 1.9 fallback (D37): 2.0 is self-labeled Beta and sometimes has no data for a
# village that 1.9 does. Only Mumbai is covered — 1.9's Mumbai flow has no Taluka step
# (D14/D30), just District-choice ("मुंबई(मेन)"/"मुंबई(उपनगर)") + a single flat Village
# dropdown covering the whole sub-district. Village value IDs are NOT shared with 2.0
# (confirmed live), so a seeded translation table is used instead of guessing.
_LEGACY_BASE_URL = "https://easr.igrmaharashtra.gov.in/eASRCommon.aspx"
_LEGACY_YEAR_SELECT = "#ctl00_ContentPlaceHolder5_ddlYear"
_LEGACY_DISTRICT_SELECT = "#ctl00_ContentPlaceHolder5_ddlDistrict"
_LEGACY_VILLAGE_SELECT = "#ctl00_ContentPlaceHolder5_ddlVillage"
_LEGACY_RURAL_TABLE = "#ctl00_ContentPlaceHolder5_ruralDataGrid"
_LEGACY_URBAN_TABLE = "#ctl00_ContentPlaceHolder5_grdUrbanSubZoneWiseRate"
_LEGACY_RESULT_TABLE = f"{_LEGACY_RURAL_TABLE}, {_LEGACY_URBAN_TABLE}"

_LEGACY_MUMBAI_DISTRICT_OPTIONS: dict[str, str] = {
    "mumbai suburban": "मुंबई(उपनगर)",
    "mumbai city": "मुंबई(मेन)",
}

_LEGACY_VILLAGE_TRANSLATIONS: dict[str, str] = {
    "malad (east) (borivali)": "मालाड ( पुर्व ) ( बोरीवली )",
}
"""eASR 2.0 English village label (lowercased) -> confirmed eASR 1.9 Marathi equivalent.
Seed with real, live-confirmed cases only (see D37) — never a guessed translation. Extend
as new 2.0 data gaps are found for villages the client actually uses."""


class EASRServiceError(Exception):
    """Raised when eASR retrieval fails outright. Message is safe to show the user."""


class EASRSearchInput(BaseModel):
    year: str
    """e.g. "2026-2027" — the hyphen is optional; normalized internally to match the portal."""
    district: str
    """Must match the portal's own `hDistName` identifier exactly (confirmed working on
    eASR 2.0: "Pune", "Bombaymains" for Mumbai — see D14/D30/D34; "Thane"/"Nagpur" carried
    over from 1.9, not independently re-verified). Not every district's identifier is known
    yet."""
    taluka: str | None = None
    """English label (D34 — eASR 2.0 renders Taluka in English), must match a real option in
    the portal's Taluka dropdown. Required for every district confirmed so far, including
    Mumbai (unlike 1.9, 2.0 gives Mumbai a real Taluka dropdown — see D34)."""
    village: str
    """English label (D34), must match a real option in the portal's Village dropdown."""
    district_option: str | None = None
    """Required whenever the District dropdown renders more than one option after loading
    (currently only Mumbai: "Mumbai City" / "Mumbai Suburban"). Most districts pre-resolve
    to a single option and don't need this — see D34."""
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

        district_option_count = await page.locator(f"{_DISTRICT_SELECT} option").count()
        if district_option_count == 0:
            raise EASRServiceError(
                f"District '{search_input.district}' was not recognized by the eASR portal "
                "(no search form rendered). Verify the exact district identifier it expects."
            )

        await self._select_by_label(page, _YEAR_SELECT, self._normalize_year(search_input.year))

        if district_option_count > 1:
            # Currently only Mumbai (D34): District renders "Mumbai City" / "Mumbai Suburban".
            if not search_input.district_option:
                raise EASRServiceError(
                    f"District '{search_input.district}' presents multiple sub-districts and "
                    "requires 'district_option' to be specified (e.g. Mumbai City vs Suburban)."
                )
            await self._select_by_label(page, _DISTRICT_SELECT, search_input.district_option)

        if not search_input.taluka:
            raise EASRServiceError(
                f"District '{search_input.district}' requires 'taluka' to be specified."
            )
        await self._select_by_label(page, _TALUKA_SELECT, search_input.taluka)

        await page.wait_for_function(
            """(sel) => {
                const el = document.querySelector(sel);
                return el && el.options.length > 1;
            }""",
            arg=_VILLAGE_SELECT,
        )
        await self._select_by_label(page, _VILLAGE_SELECT, search_input.village)

        return await self._read_results(page, search_input)

    async def _read_results(self, page: Page, search_input: EASRSearchInput) -> EASRGuidelineResult:
        """Reads whichever result table rendered (rural or urban) once District/Taluka/
        Village have already been selected — shared by both the manual (`_search_on_page`)
        and auto-match (`_auto_search_on_page`) flows."""
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

    async def try_auto_lookup(
        self,
        year: str,
        district_text: str,
        taluka_text: str,
        village_text: str,
        survey_no: str | None = None,
    ) -> EASRGuidelineResult | None:
        """Best-effort: resolves free-text location fields (e.g. Stage 1 extraction's
        District/Taluka/Village) against the eASR 2.0 portal's real dropdown options —
        possible now that they're in English (D34/D36) — and runs the lookup automatically.
        Falls back to eASR 1.9 (D37) for Mumbai villages seeded in
        `_LEGACY_VILLAGE_TRANSLATIONS`, since 2.0 (self-labeled Beta) is sometimes missing
        data 1.9 has for the exact same village.

        Returns None on any unresolved district, ambiguous/no match, or portal failure —
        never raises. Callers should fall back to the manual EasrLookupSection flow;
        auto-fetching is a convenience, not a substitute for the valuer confirming an
        official government lookup when it isn't confident.
        """
        district_code = self._resolve_district_code(district_text)
        if not district_code:
            logger.info("eASR auto-lookup: no known portal code for district '%s'", district_text)
            return None

        resolved: tuple[str | None, str, str] | None = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self._headless)
                try:
                    page = await browser.new_page()
                    page.set_default_timeout(self._timeout_ms)
                    resolved = await self._resolve_and_select(
                        page, year, district_code, district_text, taluka_text, village_text
                    )
                    if resolved is None:
                        return None
                    district_option, taluka_option, village_option = resolved
                    search_input = EASRSearchInput(
                        year=year,
                        district=district_code,
                        district_option=district_option,
                        taluka=taluka_option,
                        village=village_option,
                        survey_no=survey_no,
                    )
                    result = await self._read_results(page, search_input)
                    if result.found:
                        return result
                finally:
                    await browser.close()
        except Exception:
            logger.info("eASR 2.0 auto-lookup failed or found nothing", exc_info=True)

        if resolved and district_code == "Bombaymains":
            district_option, _taluka_option, village_option = resolved
            return await self._try_legacy_mumbai_fallback(
                year, district_option, village_option, survey_no
            )
        return None

    async def _resolve_and_select(
        self,
        page: Page,
        year: str,
        district_code: str,
        district_text: str,
        taluka_text: str,
        village_text: str,
    ) -> tuple[str | None, str, str] | None:
        """Navigates to the district and selects District/Taluka/Village by fuzzy-matching
        free text against the real dropdown options. Returns the resolved
        (district_option, taluka_option, village_option) labels once Village is selected —
        district_option is None when the District dropdown only had one entry — or None if
        any step has no confident match."""
        url = f"{_BASE_URL}?hDistName={quote(district_code)}"
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        await self._select_by_label(page, _YEAR_SELECT, self._normalize_year(year))

        district_option: str | None = None
        district_texts = await self._option_texts(page, _DISTRICT_SELECT)
        if len(district_texts) > 1:
            district_option = self._best_match(district_text, district_texts)
            if not district_option:
                return None
            await self._select_by_label(page, _DISTRICT_SELECT, district_option)

        await page.wait_for_function(
            """(sel) => {
                const el = document.querySelector(sel);
                return el && el.options.length > 1;
            }""",
            arg=_TALUKA_SELECT,
        )
        taluka_texts = [
            t for t in await self._option_texts(page, _TALUKA_SELECT) if not t.startswith("- -")
        ]
        taluka_option = self._best_match(taluka_text, taluka_texts)
        if not taluka_option:
            return None
        await self._select_by_label(page, _TALUKA_SELECT, taluka_option)

        await page.wait_for_function(
            """(sel) => {
                const el = document.querySelector(sel);
                return el && el.options.length > 1;
            }""",
            arg=_VILLAGE_SELECT,
        )
        village_texts = [
            t for t in await self._option_texts(page, _VILLAGE_SELECT) if not t.startswith("- -")
        ]
        village_option = self._best_match(village_text, village_texts)
        if not village_option:
            return None
        await self._select_by_label(page, _VILLAGE_SELECT, village_option)

        return district_option, taluka_option, village_option

    async def _try_legacy_mumbai_fallback(
        self,
        year: str,
        district_option_2_0: str,
        village_2_0: str,
        survey_no: str | None,
    ) -> EASRGuidelineResult | None:
        """Narrow fallback (D37): eASR 2.0 sometimes has no data for a village that 1.9
        does (2.0 is self-labeled Beta). Only covers Mumbai (1.9's flow for Mumbai has no
        Taluka step — D14/D30), and only villages already confirmed and seeded in
        `_LEGACY_VILLAGE_TRANSLATIONS` — never guesses a Marathi translation."""
        legacy_village = _LEGACY_VILLAGE_TRANSLATIONS.get(village_2_0.strip().lower())
        legacy_district = _LEGACY_MUMBAI_DISTRICT_OPTIONS.get(district_option_2_0.strip().lower())
        if not legacy_village or not legacy_district:
            return None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self._headless)
                try:
                    page = await browser.new_page()
                    page.set_default_timeout(self._timeout_ms)
                    await page.goto(
                        f"{_LEGACY_BASE_URL}?hDistName=Bombaymains", wait_until="networkidle"
                    )
                    await page.wait_for_timeout(1000)
                    await self._select_by_label(page, _LEGACY_YEAR_SELECT, year.replace("-", ""))
                    await self._select_by_label(page, _LEGACY_DISTRICT_SELECT, legacy_district)
                    await page.wait_for_function(
                        """(sel) => {
                            const el = document.querySelector(sel);
                            return el && el.options.length > 1;
                        }""",
                        arg=_LEGACY_VILLAGE_SELECT,
                    )
                    await self._select_by_label(page, _LEGACY_VILLAGE_SELECT, legacy_village)
                    await page.wait_for_selector(_LEGACY_RESULT_TABLE)

                    accessed_at = datetime.now(timezone.utc)
                    access_date = accessed_at.date().isoformat()
                    source = f"{_SOURCE_LABEL} (1.9 fallback), accessed {access_date}"
                    search_input = EASRSearchInput(
                        year=year,
                        district="Bombaymains",
                        district_option=district_option_2_0,
                        village=village_2_0,
                        survey_no=survey_no,
                    )

                    rural = page.locator(_LEGACY_RURAL_TABLE)
                    if await rural.count() > 0:
                        columns, rows = await self._parse_table(rural)
                        return EASRGuidelineResult(
                            search_input=search_input,
                            found=bool(rows),
                            columns=columns,
                            rows=rows,
                            preamble=await self._extract_vibhag_number(page),
                            source=source,
                            accessed_at=accessed_at,
                        )

                    urban = page.locator(_LEGACY_URBAN_TABLE)
                    columns, rows = await self._parse_table(urban)
                    if survey_no:
                        rows = self._filter_by_survey_no(columns, rows, survey_no)
                    return EASRGuidelineResult(
                        search_input=search_input,
                        found=bool(rows),
                        columns=columns,
                        rows=rows,
                        source=source,
                        accessed_at=accessed_at,
                    )
                finally:
                    await browser.close()
        except Exception:
            logger.info("eASR 1.9 fallback also failed", exc_info=True)
            return None

    @staticmethod
    async def _option_texts(page: Page, select_selector: str) -> list[str]:
        return await page.locator(select_selector).evaluate(
            "el => Array.from(el.options).map(o => o.text.trim())"
        )

    @staticmethod
    def _resolve_district_code(district_text: str) -> str | None:
        normalized = district_text.strip().lower()
        for key, code in _KNOWN_DISTRICT_CODES.items():
            if key in normalized:
                return code
        return None

    @staticmethod
    def _best_match(candidate: str, options: list[str]) -> str | None:
        """Prefers substring containment (e.g. "Malad" in "Malad (East) (Borivali)") over
        whole-string similarity, since portal labels append parenthetical qualifiers the
        extracted text won't have. Returns None — never guesses — when zero or multiple
        options contain the candidate and no single close match stands out."""
        if not candidate or not options:
            return None
        candidate_norm = candidate.strip().lower()
        substring_matches = [o for o in options if candidate_norm in o.lower()]
        if len(substring_matches) == 1:
            return substring_matches[0]
        if len(substring_matches) > 1:
            return None
        close = difflib.get_close_matches(candidate.strip(), options, n=1, cutoff=_MATCH_CUTOFF)
        return close[0] if close else None

    @staticmethod
    def _normalize_year(year: str) -> str:
        """eASR 2.0's Year dropdown options include the hyphen (e.g. "2026-2027") — unlike
        1.9, which didn't. Accepts either "2026-2027" or "20262027" and always returns the
        hyphenated form the portal expects."""
        digits = year.replace("-", "")
        return f"{digits[:4]}-{digits[4:]}" if len(digits) == 8 else year

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
