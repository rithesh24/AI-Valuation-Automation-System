from datetime import date

from app.services.prompt_builder import PromptBuilder


def test_includes_document_text() -> None:
    prompt = PromptBuilder().build_extraction_prompt(
        document_texts={"sale_deed.pdf": "This is the sale deed content."}
    )
    assert "--- sale_deed.pdf ---" in prompt
    assert "This is the sale deed content." in prompt


def test_no_documents_says_so_explicitly() -> None:
    prompt = PromptBuilder().build_extraction_prompt(document_texts={})
    assert "No documents were provided." in prompt


def test_uses_given_valuation_date() -> None:
    prompt = PromptBuilder().build_extraction_prompt(
        document_texts={}, valuation_date=date(2026, 1, 15)
    )
    assert "2026-01-15" in prompt


def test_defaults_tier1_note_when_not_given() -> None:
    prompt = PromptBuilder().build_extraction_prompt(document_texts={})
    assert "No Tier 1 official/government data was retrieved" in prompt


def test_includes_given_tier1_data() -> None:
    prompt = PromptBuilder().build_extraction_prompt(
        document_texts={}, tier1_official_data="Ready Reckoner rate: Rs. 50000/sq.m"
    )
    assert "Ready Reckoner rate: Rs. 50000/sq.m" in prompt


def test_includes_canonical_schema_json() -> None:
    prompt = PromptBuilder().build_extraction_prompt(document_texts={})
    assert '"property_identification"' in prompt
    assert '"present_market_value"' in prompt
