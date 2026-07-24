import asyncio

import pytest
from playwright.async_api import Error as PlaywrightError

from app.services.official_sources_service import (
    RERASearchInput,
    RERASearchResult,
    RERAService,
    RERAServiceError,
)


def _run(coro):
    return asyncio.run(coro)


class TestModels:
    def test_search_input_has_filter_false_when_empty(self):
        assert RERASearchInput().has_filter() is False

    def test_search_input_has_filter_true_with_any_field(self):
        assert RERASearchInput(district="Pune").has_filter() is True
        assert RERASearchInput(pincode="411001").has_filter() is True
        assert RERASearchInput(project_name_or_registration_number="Test").has_filter() is True


class TestCardParsing:
    """No browser involved: pure text-parsing logic against a captured real card."""

    def test_parses_a_real_captured_card(self):
        service = RERAService()
        card_text = (
            "# P52100012200\n\nNANDHA RESIDENCY\n\nAMIT C THAKUR\n\n"
            " Haveli  Find Route\nState\n\nMAHARASHTRA\n\nPincode\n\n412202\n\n"
            "Certificate\nDistrict\n\nPune\n\nLast Modified\n\n2017-09-01\n\n"
            "Extension Certificate\nN/A\nApplication\nView Details View Original Application"
        )
        result = service._parse_card_text(card_text, "https://maharerait.maharashtra.gov.in/public/project/view/11")

        assert result.registration_number == "P52100012200"
        assert result.project_name == "NANDHA RESIDENCY"
        assert result.promoter_name == "AMIT C THAKUR"
        assert result.taluka == "Haveli"
        assert result.state == "MAHARASHTRA"
        assert result.pincode == "412202"
        assert result.district == "Pune"
        assert result.last_modified == "2017-09-01"
        assert result.extension_certificate == "N/A"
        assert result.detail_url == "https://maharerait.maharashtra.gov.in/public/project/view/11"

    def test_extract_total_count(self):
        service = RERAService()
        assert service._extract_total_count("Showing Final 3443 Result") == 3443
        assert service._extract_total_count("no such text here") is None


class TestRetryLoop:
    """No real browser involved: RERAService._run_search is swapped for a fake."""

    def test_raises_immediately_when_no_filter_given(self):
        service = RERAService()
        with pytest.raises(RERAServiceError, match="At least one of"):
            _run(service.search_projects(RERASearchInput()))

    def test_retries_then_succeeds(self, monkeypatch):
        service = RERAService(max_retries=2, retry_delay_seconds=0)
        search_input = RERASearchInput(district="Pune")
        expected = RERASearchResult(
            search_input=search_input,
            found=True,
            source="MahaRERA (Maharashtra Real Estate Regulatory Authority), accessed 2026-07-24",
            accessed_at="2026-07-24T00:00:00Z",
        )

        calls = {"count": 0}

        async def fake_run_search(_search_input):
            calls["count"] += 1
            if calls["count"] < 3:
                raise PlaywrightError("navigation failed")
            return expected

        monkeypatch.setattr(service, "_run_search", fake_run_search)

        async def no_op_sleep(seconds):
            return None

        monkeypatch.setattr(asyncio, "sleep", no_op_sleep)

        result = _run(service.search_projects(search_input))

        assert result is expected
        assert calls["count"] == 3

    def test_raises_rera_service_error_after_exhausting_retries(self, monkeypatch):
        service = RERAService(max_retries=2, retry_delay_seconds=0)
        search_input = RERASearchInput(district="Pune")

        async def always_fails(_search_input):
            raise PlaywrightError("navigation failed")

        monkeypatch.setattr(service, "_run_search", always_fails)

        async def no_op_sleep(seconds):
            return None

        monkeypatch.setattr(asyncio, "sleep", no_op_sleep)

        with pytest.raises(RERAServiceError, match="after 3 attempts"):
            _run(service.search_projects(search_input))
