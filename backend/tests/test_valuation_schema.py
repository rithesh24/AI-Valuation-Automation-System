from app.models.valuation_schema import (
    INFO_NOT_AVAILABLE,
    ComparableEvidence,
    ValuationReportData,
    canonical_schema_field_list,
)


def test_defaults_to_non_fabrication_sentinel() -> None:
    data = ValuationReportData()
    assert data.property_identification.district == INFO_NOT_AVAILABLE
    assert data.concluded_values.present_market_value == INFO_NOT_AVAILABLE
    assert data.valuer_and_inspection_details.valuer_name == INFO_NOT_AVAILABLE
    assert data.ownership_and_title.flow_of_title_narrative == INFO_NOT_AVAILABLE
    assert data.site_and_building_particulars.locality.distance_from_bus_stop == INFO_NOT_AVAILABLE
    assert data.occupancy_details.occupancy_status == INFO_NOT_AVAILABLE
    assert data.prior_valuation.previously_valued == INFO_NOT_AVAILABLE


def test_serializes_to_json() -> None:
    data = ValuationReportData(comparable_evidence=[ComparableEvidence(location="Pune")])
    dumped = data.model_dump_json()
    assert '"location":"Pune"' in dumped.replace(" ", "")


def test_field_list_flattens_nested_sections_with_descriptions() -> None:
    fields = canonical_schema_field_list()
    names = dict(fields)
    assert "property_identification.district" in names
    assert names["property_identification.district"] == "District"
    assert "valuer_and_inspection_details.valuer_name" in names
    assert "site_and_building_particulars.locality.distance_from_railway_station" in names
    assert "occupancy_details.occupancy_status" in names
    assert "insurance_particulars.company_name" in names
    assert "prior_valuation.previously_valued" in names
    assert "concluded_values.marketability_opinion" in names
    assert "statutory_position.rera_bank_account_details" in names


def test_field_list_marks_repeating_structures() -> None:
    fields = canonical_schema_field_list()
    names = [name for name, _ in fields]
    assert any(name.startswith("comparable_evidence[].") for name in names)
    assert "comparable_evidence[].location" in names
    assert "tax_payment_details[].tax_type" in names
