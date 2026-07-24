import asyncio
import logging
import re
from datetime import datetime, timezone

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, async_playwright
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# Real portal + element IDs confirmed by driving the live site with Playwright
# (see docs/DECISIONS.md D16). Note: maharera.mahaonline.gov.in (the commonly-cited
# URL) no longer resolves — this is the current domain.
_BASE_URL = "https://maharera.maharashtra.gov.in/projects-search-result"
_PROJECT_NAME_INPUT = "#edit-project-name"
_PINCODE_INPUT = "#edit-project-location"
_DISTRICT_SELECT = "#edit-project-district"
_SEARCH_SUBMIT = "#edit-submit"
_RESULT_CARD = ".row.shadow.p-3.mb-5.bg-body.rounded"

_SOURCE_LABEL = "MahaRERA (Maharashtra Real Estate Regulatory Authority)"


class RERAServiceError(Exception):
    """Raised when RERA retrieval fails outright. Message is safe to show the user."""


class RERASearchInput(BaseModel):
    project_name_or_registration_number: str | None = None
    """Matches the portal's own combined field: free-text project name OR MahaRERA registration number."""
    district: str | None = None
    """English district label, must match a real option in the portal's District dropdown."""
    pincode: str | None = None

    def has_filter(self) -> bool:
        return bool(self.project_name_or_registration_number or self.district or self.pincode)


class RERAProjectResult(BaseModel):
    registration_number: str | None = None
    project_name: str | None = None
    promoter_name: str | None = None
    taluka: str | None = None
    state: str | None = None
    district: str | None = None
    pincode: str | None = None
    last_modified: str | None = None
    extension_certificate: str | None = None
    detail_url: str | None = None


class RERASearchResult(BaseModel):
    search_input: RERASearchInput
    found: bool
    """True if at least one project is being returned; False = confirmed empty result."""
    projects: list[RERAProjectResult] = []
    """Only the first results page (up to 10 projects) — see D16 for the pagination limitation."""
    total_result_count: int | None = None
    """The portal's own "Showing Final N Result" count, which may exceed len(projects)."""
    source: str
    accessed_at: datetime


class RERAService:
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

    async def search_projects(self, search_input: RERASearchInput) -> RERASearchResult:
        """Searches MahaRERA's registered-projects listing. Retries on transient Playwright
        failures; raises RERAServiceError immediately for non-retryable failures (no filter
        given, an unrecognized district) — same contract as EASRService, see D14/D16.
        """
        if not search_input.has_filter():
            raise RERAServiceError(
                "At least one of project_name_or_registration_number, district, or pincode "
                "is required — searching with no filter would match all registered projects."
            )

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._run_search(search_input)
            except PlaywrightError as exc:
                last_error = exc
                logger.warning(
                    "RERA search attempt %s/%s failed: %s",
                    attempt + 1,
                    self._max_retries + 1,
                    exc,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_delay_seconds * (attempt + 1))
        raise RERAServiceError(
            f"Could not retrieve RERA data after {self._max_retries + 1} attempts: {last_error}"
        ) from last_error

    async def _run_search(self, search_input: RERASearchInput) -> RERASearchResult:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=self._headless)
            except Exception as exc:
                raise RERAServiceError(
                    "Playwright's Chromium browser is not installed. Run "
                    "'playwright install chromium' in the backend environment."
                ) from exc

            try:
                page = await browser.new_page()
                page.set_default_timeout(self._timeout_ms)
                return await self._search_on_page(page, search_input)
            finally:
                await browser.close()

    async def _search_on_page(self, page: Page, search_input: RERASearchInput) -> RERASearchResult:
        await page.goto(_BASE_URL, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        if search_input.project_name_or_registration_number:
            await page.fill(_PROJECT_NAME_INPUT, search_input.project_name_or_registration_number)
        if search_input.pincode:
            await page.fill(_PINCODE_INPUT, search_input.pincode)
        if search_input.district:
            await self._select_district(page, search_input.district)

        await page.click(_SEARCH_SUBMIT)
        # The results list re-renders via AJAX with no confirmed "loading finished" indicator
        # (see D16) — a settle wait is the same pragmatic approach used for eASR (D14).
        await page.wait_for_timeout(2000)

        accessed_at = datetime.now(timezone.utc)
        body_text = await page.locator("body").inner_text()
        total_result_count = self._extract_total_count(body_text)

        cards = page.locator(_RESULT_CARD)
        card_count = await cards.count()

        projects: list[RERAProjectResult] = []
        for i in range(card_count):
            card = cards.nth(i)
            card_text = await card.inner_text()
            detail_href = None
            detail_link = card.locator("a:has-text('View Details')")
            if await detail_link.count() > 0:
                detail_href = await detail_link.first.get_attribute("href")
            projects.append(self._parse_card_text(card_text, detail_href))

        return RERASearchResult(
            search_input=search_input,
            found=bool(projects),
            projects=projects,
            total_result_count=total_result_count,
            source=f"{_SOURCE_LABEL}, accessed {accessed_at.date().isoformat()}",
            accessed_at=accessed_at,
        )

    async def _select_district(self, page: Page, target_label: str) -> None:
        select = page.locator(_DISTRICT_SELECT)
        options = select.locator("option")
        count = await options.count()
        target = target_label.strip()
        for i in range(count):
            option = options.nth(i)
            text = (await option.inner_text()).strip()
            if text == target:
                value = await option.get_attribute("value")
                await select.select_option(value=value)
                return
        raise RERAServiceError(f"'{target_label}' is not a valid option for the RERA District dropdown.")

    def _extract_total_count(self, body_text: str) -> int | None:
        match = re.search(r"Showing Final\s+(\d+)\s+Result", body_text)
        return int(match.group(1)) if match else None

    def _parse_card_text(self, card_text: str, detail_url: str | None) -> RERAProjectResult:
        lines = [line.strip() for line in card_text.split("\n") if line.strip()]

        def value_after_label(label: str) -> str | None:
            try:
                idx = lines.index(label)
            except ValueError:
                return None
            return lines[idx + 1] if idx + 1 < len(lines) else None

        registration_number = None
        if lines and lines[0].startswith("#"):
            registration_number = lines[0].lstrip("#").strip()

        taluka = None
        for line in lines:
            if "Find Route" in line:
                taluka = line.replace("Find Route", "").strip() or None
                break

        return RERAProjectResult(
            registration_number=registration_number,
            project_name=lines[1] if len(lines) > 1 else None,
            promoter_name=lines[2] if len(lines) > 2 else None,
            taluka=taluka,
            state=value_after_label("State"),
            pincode=value_after_label("Pincode"),
            district=value_after_label("District"),
            last_modified=value_after_label("Last Modified"),
            extension_certificate=value_after_label("Extension Certificate"),
            detail_url=detail_url,
        )
