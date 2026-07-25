"""Canonical valuation data schema (D9).

Shared contract across the three-stage report pipeline (D5): Stage 1
(claude_service.py extraction) produces a ValuationReportData; Stage 2
(template mapping) matches its fields against the uploaded template using
canonical_schema_field_list(); Stage 3 (injection) reads the filled instance
field-by-field. Field names/groupings/descriptions are taken from
docs/UPDATED_PROMPTS.md Stage 1 (sections 2-20), not the raw client prompt.

Every leaf field is a plain string so Stage 3 can write it straight into a
python-docx Run.text, and so "unavailable" can be represented the same way
real data is: as the literal INFO_NOT_AVAILABLE sentinel (non-fabrication
rule, docs/UPDATED_PROMPTS.md section 21), never a null.
"""

import typing

from pydantic import BaseModel, Field

INFO_NOT_AVAILABLE = (
    "Information not available / not provided – refer Limiting Conditions."
)


def _str_field(description: str) -> str:
    return Field(default=INFO_NOT_AVAILABLE, description=description)


# --- Section 2: Documents Referred To -------------------------------------


class DocumentReference(BaseModel):
    name: str = _str_field("Name of the document")
    nature: str = _str_field("Nature of the document")
    date_of_execution_or_issue: str = _str_field("Date of execution or issue")
    registration_number: str = _str_field("Registration number")
    registration_date: str = _str_field("Registration date")
    issuing_authority: str = _str_field("Issuing authority")
    registering_authority: str = _str_field("Registering authority")
    sub_registrar_office: str = _str_field("Sub-Registrar office")
    document_number: str = _str_field("Document number")
    property_particulars: str = _str_field("Property particulars stated in the document")
    copy_type: str = _str_field(
        "Original / certified copy / photocopy / scanned copy / online extract"
    )


# --- Section 3: Property Identification ------------------------------------


class PropertyIdentification(BaseModel):
    unit_number: str = _str_field("Flat/shop/office/gala/unit/plot/bungalow/factory number")
    floor: str = _str_field("Floor")
    wing: str = _str_field("Wing")
    building_name: str = _str_field("Building name")
    society_name: str = _str_field("Society name")
    project_name: str = _str_field("Project name")
    plot_number: str = _str_field("Plot number")
    survey_number: str = _str_field("Survey number")
    gat_number: str = _str_field("Gat number")
    hissa_number: str = _str_field("Hissa number")
    cts_number: str = _str_field("CTS number")
    city_survey_number: str = _str_field("City Survey number")
    final_plot_number: str = _str_field("Final Plot number")
    revenue_village: str = _str_field("Revenue village")
    locality: str = _str_field("Locality")
    sub_locality: str = _str_field("Sub-locality")
    street_or_road: str = _str_field("Street or road")
    taluka: str = _str_field("Taluka")
    district: str = _str_field("District")
    state: str = _str_field("State")
    pin_code: str = _str_field("PIN code")
    latitude_longitude: str = _str_field("Latitude and longitude, if required")
    nearest_landmark: str = _str_field("Nearest landmark")
    municipal_ward: str = _str_field("Municipal ward")
    planning_authority: str = _str_field("Planning authority")
    registration_district: str = _str_field("Registration district")
    registration_sub_district: str = _str_field("Registration sub-district")
    sub_registrar_office: str = _str_field("Relevant Sub-Registrar office")
    rera_registration_number: str = _str_field("RERA registration number")
    discrepancy_note: str = _str_field(
        "Discrepancy between descriptions across documents and which was adopted, with reason"
    )


# --- Section 4: Ownership and Flow of Title ---------------------------------


class TitleTransaction(BaseModel):
    date: str = _str_field("Transaction date")
    parties: str = _str_field("Parties to the transaction")
    document_type: str = _str_field("Document type")
    registration_particulars: str = _str_field("Registration particulars")
    area_transferred: str = _str_field("Area transferred")
    consideration: str = _str_field("Consideration")
    property_description: str = _str_field("Property description")
    rights_transferred: str = _str_field("Rights transferred")
    mutation_or_society_transfer_details: str = _str_field(
        "Mutation or society-transfer details"
    )


class OwnershipAndTitle(BaseModel):
    present_owners: str = _str_field("Present owner(s)")
    seller_transferor: str = _str_field("Seller or transferor")
    purchaser_transferee: str = _str_field("Purchaser or transferee")
    developer_promoter: str = _str_field("Developer or promoter")
    landowner: str = _str_field("Landowner")
    lessor_lessee: str = _str_field("Lessor and lessee")
    society_or_condominium: str = _str_field("Society or condominium")
    borrower_mortgagor: str = _str_field("Borrower or mortgagor")
    occupant_tenant: str = _str_field("Occupant or tenant")
    nature_of_ownership: str = _str_field(
        "Freehold / leasehold / society membership / apartment ownership / tenancy / "
        "occupancy / undivided share / development rights / assignment rights / "
        "industrial leasehold rights"
    )
    flow_of_title: list[TitleTransaction] = Field(
        default_factory=list,
        description="Chronological flow of title, one entry per transaction",
    )
    title_flags: list[str] = Field(
        default_factory=list,
        description=(
            "Missing link documents, unregistered documents, incomplete title chain, "
            "name mismatch, area discrepancy, absence of conveyance/share certificate, "
            "expired lease, transfer restrictions, mortgage, charge, litigation, "
            "attachment, acquisition, reservation, tenancy, third-party possession"
        ),
    )
    title_narration_caveat: str = _str_field(
        "Statement that the title narration is based on documents furnished and is "
        "subject to independent legal verification (title is never certified)"
    )


# --- Section 5: Area and Measurement Reconciliation -------------------------


class AreaReconciliation(BaseModel):
    carpet_area: str = _str_field("Carpet area")
    rera_carpet_area: str = _str_field("RERA carpet area")
    built_up_area: str = _str_field("Built-up area")
    super_built_up_area: str = _str_field("Super built-up area")
    saleable_area: str = _str_field("Saleable area")
    balcony_area: str = _str_field("Balcony area")
    terrace_area: str = _str_field("Terrace area")
    loft_or_mezzanine_area: str = _str_field("Loft or mezzanine area")
    plot_area: str = _str_field("Plot area")
    gross_land_area: str = _str_field("Gross land area")
    net_plot_area: str = _str_field("Net plot area")
    road_widening_area: str = _str_field("Road-widening area")
    reservation_area: str = _str_field("Reservation area")
    encroached_area: str = _str_field("Encroached area")
    construction_area: str = _str_field("Construction area")
    factory_shed_area: str = _str_field("Factory shed area")
    open_storage_area: str = _str_field("Open storage area")
    area_per_title_document: str = _str_field("Area as per title document")
    area_per_approved_plan: str = _str_field("Area as per approved plan")
    area_per_rera: str = _str_field("Area as per RERA")
    area_per_municipal_record: str = _str_field("Area as per municipal record")
    area_per_property_particulars: str = _str_field("Area stated in the property particulars")
    area_measured_at_site: str = _str_field("Area measured at site, if available")
    area_adopted_for_valuation: str = _str_field("Area adopted for valuation")
    area_adopted_basis: str = _str_field("Basis/reason for the area adopted")
    variance_percentage: str = _str_field("Percentage variation between differing areas")
    variance_explanation: str = _str_field("Explanation for the area difference, where evidence exists")
    excess_or_deficient_area_treatment: str = _str_field(
        "Disclosed treatment of excess or deficient area"
    )


# --- Section 6: Demarcation and Boundaries ----------------------------------


class Boundaries(BaseModel):
    north: str = _str_field("Northern boundary")
    south: str = _str_field("Southern boundary")
    east: str = _str_field("Eastern boundary")
    west: str = _str_field("Western boundary")
    adjoining_unit: str = _str_field("Adjoining flat/unit (internal demarcation)")
    passage: str = _str_field("Passage (internal demarcation)")
    staircase: str = _str_field("Staircase (internal demarcation)")
    lift: str = _str_field("Lift (internal demarcation)")
    corridor: str = _str_field("Corridor (internal demarcation)")
    open_space: str = _str_field("Open space (internal demarcation)")
    road: str = _str_field("Road (internal demarcation)")
    external_wall: str = _str_field("External wall (internal demarcation)")
    source_discrepancy_note: str = _str_field(
        "Where title document and property particulars disagree on boundaries, both "
        "values and their source"
    )


# --- Section 7: Site and Building Particulars -------------------------------


class SiteParticulars(BaseModel):
    shape: str = _str_field("Shape of the land")
    frontage: str = _str_field("Frontage")
    depth: str = _str_field("Depth")
    topography: str = _str_field("Topography")
    ground_level: str = _str_field("Ground level")
    access_road: str = _str_field("Access road")
    road_width: str = _str_field("Road width")
    corner_or_intermediate_location: str = _str_field("Corner or intermediate location")
    compound_wall: str = _str_field("Compound wall")
    gate: str = _str_field("Gate")
    water_supply: str = _str_field("Water supply")
    electricity: str = _str_field("Electricity")
    drainage: str = _str_field("Drainage")
    sewerage: str = _str_field("Sewerage")
    encroachment: str = _str_field("Encroachment")
    flood_risk: str = _str_field("Flood risk")
    high_tension_line: str = _str_field("High-tension line")
    nala: str = _str_field("Nala")
    railway: str = _str_field("Railway")
    pipeline: str = _str_field("Pipeline")
    surrounding_development: str = _str_field("Surrounding development")
    accessibility: str = _str_field("Accessibility")
    locational_advantages: str = _str_field("Locational advantages")
    locational_disadvantages: str = _str_field("Locational disadvantages")


class BuildingParticulars(BaseModel):
    structure_type: str = _str_field("RCC framed / load-bearing / steel-frame / industrial shed")
    number_of_floors: str = _str_field("Number of floors")
    subject_floor: str = _str_field("Subject floor")
    approximate_age: str = _str_field("Approximate age")
    year_of_construction: str = _str_field("Year of construction")
    year_of_completion: str = _str_field("Year of completion")
    occupancy: str = _str_field("Occupancy")
    physical_condition: str = _str_field("Physical condition")
    maintenance: str = _str_field("Maintenance")
    construction_quality: str = _str_field("Construction quality")
    flooring: str = _str_field("Flooring")
    doors_and_windows: str = _str_field("Doors and windows")
    walls_and_ceiling: str = _str_field("Walls and ceiling")
    electrical_fittings: str = _str_field("Electrical fittings")
    plumbing: str = _str_field("Plumbing")
    sanitary_fittings: str = _str_field("Sanitary fittings")
    lifts: str = _str_field("Lifts")
    fire_fighting_system: str = _str_field("Fire-fighting system")
    parking: str = _str_field("Parking")
    common_amenities: str = _str_field("Common amenities")
    repairs_required: str = _str_field("Repairs required")
    structural_distress: str = _str_field("Structural distress")
    renovation: str = _str_field("Renovation")
    unauthorised_alteration: str = _str_field("Unauthorised alteration")
    merger_or_subdivision_of_units: str = _str_field("Merger or subdivision of units")


class SiteAndBuildingParticulars(BaseModel):
    site: SiteParticulars = Field(default_factory=SiteParticulars)
    building: BuildingParticulars = Field(default_factory=BuildingParticulars)
    plan_deviation_note: str = _str_field(
        "Discrepancy between the actual property and the sanctioned plan, and its "
        "valuation treatment"
    )


# --- Section 8: Land Use and Statutory Position -----------------------------


class StatutoryPosition(BaseModel):
    agricultural_or_non_agricultural_status: str = _str_field(
        "Agricultural or non-agricultural status"
    )
    use_classification: str = _str_field("Residential / commercial / industrial / institutional / mixed use")
    development_plan_zoning: str = _str_field("Development Plan zoning")
    reservation: str = _str_field("Reservation")
    road_widening: str = _str_field("Road widening")
    acquisition: str = _str_field("Acquisition")
    crz_forest_eco_sensitive_restrictions: str = _str_field(
        "CRZ / forest / eco-sensitive restrictions"
    )
    green_or_no_development_zone_restrictions: str = _str_field(
        "Green-zone or no-development-zone restrictions"
    )
    airport_or_defence_restrictions: str = _str_field("Airport or defence restrictions")
    heritage_restrictions: str = _str_field("Heritage restrictions")
    flood_line_restrictions: str = _str_field("Flood-line restrictions")
    applicable_development_control_regulations: str = _str_field(
        "Applicable Development Control Regulations"
    )
    permissible_fsi_or_far: str = _str_field("Permissible FSI or FAR")
    basic_fsi: str = _str_field("Basic FSI")
    premium_fsi: str = _str_field("Premium FSI")
    incentive_fsi: str = _str_field("Incentive FSI")
    fungible_fsi: str = _str_field("Fungible FSI")
    consumed_fsi: str = _str_field("Consumed FSI")
    balance_fsi: str = _str_field("Balance FSI")
    tdr: str = _str_field("TDR")
    setbacks: str = _str_field("Setbacks")
    height_restrictions: str = _str_field("Height restrictions")
    parking_requirements: str = _str_field("Parking requirements")
    fire_noc: str = _str_field("Fire NOC")
    rera_status: str = _str_field("RERA status")
    municipal_approval_status: str = _str_field("Municipal approval status")
    na_permission: str = _str_field("NA permission")
    layout_sanction: str = _str_field("Layout sanction")
    industrial_authority_permission: str = _str_field("Industrial-authority permission")
    commencement_and_occupation_status: str = _str_field(
        "Commencement and occupation status"
    )


# --- Section 9: Encumbrances and Litigation ---------------------------------


class EncumbranceItem(BaseModel):
    category: str = _str_field(
        "Mortgage / charge / lien / attachment / lis pendens / court case / "
        "arbitration / tenancy / encroachment / acquisition / reservation / "
        "government notice / municipal arrears / society dues / RERA complaint / "
        "SARFAESI action / transfer restriction / etc."
    )
    description: str = _str_field("Description of the encumbrance or litigation")
    source: str = _str_field("Document or record the encumbrance was identified from")


class EncumbrancesAndLitigation(BaseModel):
    items: list[EncumbranceItem] = Field(default_factory=list, description="Identified encumbrances/litigation")
    unquantified_material_effect_note: str = _str_field(
        "Disclosure where a material encumbrance's effect cannot be quantified from "
        "reliable evidence"
    )


# --- Sections 10-11: Purpose, Basis, Dates ----------------------------------


class PurposeAndBasis(BaseModel):
    purpose: str = _str_field(
        "Purpose of valuation (mortgage, loan, SARFAESI, insurance, stamp duty, etc.); "
        'defaults to "To ascertain the Present Market Value" when unstated'
    )
    basis: str = _str_field(
        "Basis of valuation: Market Value / Fair Value / Depreciated Replacement Cost / "
        "Liquidation Value / Realisable Value / Forced Sale Value"
    )
    valuation_date: str = _str_field("Valuation date (current date unless otherwise stated)")
    inspection_date: str = _str_field("Date of inspection stated in the property particulars")


# --- Section 12: Highest and Best Use ---------------------------------------


class HighestAndBestUse(BaseModel):
    physically_possible: str = _str_field("Whether the use is physically possible")
    legally_permissible: str = _str_field("Whether the use is legally permissible")
    financially_feasible: str = _str_field("Whether the use is financially feasible")
    maximally_productive: str = _str_field("Whether the use is maximally productive")
    existing_use: str = _str_field("Existing use")
    potential_use: str = _str_field("Potential use, where materially different")
    conclusion: str = _str_field("Concluded highest and best use")


# --- Section 13: Selection of Valuation Approach ----------------------------


class ValuationApproachSelection(BaseModel):
    primary_approach: str = _str_field(
        "Sales Comparison / Income / Cost-DRC / Development-Residual approach"
    )
    cross_check_approach: str = _str_field("Secondary approach used as a cross-check")
    reason_for_selection: str = _str_field("Reason for selecting the primary approach")
    reason_for_exclusion: str = _str_field("Reason for excluding other approaches")
    reliability_of_data: str = _str_field("Reliability of the available data")
    market_liquidity: str = _str_field("Market liquidity")
    relevance_to_purpose: str = _str_field("Relevance of the approach to the stated purpose")


# --- Section 14: Market Research, Tier 1 (official/government data) --------


class OfficialRateCitation(BaseModel):
    source: str = _str_field(
        'Official source name, e.g. "IGR Maharashtra e ASR (igreval)"'
    )
    rate: str = _str_field("Guideline/Ready Reckoner rate")
    unit: str = _str_field("Unit the rate is expressed in (e.g. Rs./sq.m)")
    access_date: str = _str_field("Date the source was accessed")
    remarks: str = _str_field("Remarks, e.g. treated as statutory reference, not Market Value")


# --- Section 15: Market Research, Tier 2 (live web research) ---------------


class MarketResearchSource(BaseModel):
    source_name: str = _str_field("Portal or source name")
    property_or_project: str = _str_field("Property or project referenced")
    locality: str = _str_field("Locality")
    area: str = _str_field("Area")
    area_basis: str = _str_field("Carpet / built-up / saleable")
    price_or_rate: str = _str_field("Price or rate")
    transaction_or_listing_date: str = _str_field("Transaction or listing date")
    date_accessed: str = _str_field("Date accessed")
    source_url: str = _str_field("Source URL")
    remarks: str = _str_field("Relevant remarks")


# --- Section 16: Comparable Evidence and Adjustments ------------------------


class ComparableEvidence(BaseModel):
    indicator_number: str = _str_field("Indicator number")
    location: str = _str_field("Property location")
    property_type: str = _str_field("Property type")
    area: str = _str_field("Area")
    area_basis: str = _str_field("Carpet / built-up / saleable")
    transaction_type: str = _str_field("Transaction or listing")
    transaction_or_listing_date: str = _str_field("Transaction or listing date")
    total_consideration: str = _str_field("Total consideration")
    unadjusted_unit_rate: str = _str_field("Unadjusted unit rate")
    source: str = _str_field("Source")
    time_adjustment: str = _str_field("Time adjustment")
    location_adjustment: str = _str_field("Location adjustment")
    size_adjustment: str = _str_field("Size adjustment")
    floor_adjustment: str = _str_field("Floor adjustment")
    age_or_condition_adjustment: str = _str_field("Age or condition adjustment")
    amenity_adjustment: str = _str_field("Amenity adjustment")
    legal_or_title_adjustment: str = _str_field("Legal or title adjustment")
    negotiation_adjustment: str = _str_field("Negotiation adjustment")
    total_adjustment: str = _str_field("Total adjustment")
    adjusted_rate: str = _str_field("Adjusted rate")


# --- Section 17: Valuation Calculation --------------------------------------


class CompositeRateCalculation(BaseModel):
    area_adopted: str = _str_field("Area adopted")
    area_basis: str = _str_field("Area basis")
    rate_adopted: str = _str_field("Rate adopted")
    supporting_evidence: str = _str_field("Supporting evidence for the rate")
    additions: str = _str_field("Additions")
    deductions: str = _str_field("Deductions")
    rounded_value: str = _str_field("Rounded value")


class LandAndBuildingCalculation(BaseModel):
    land_area: str = _str_field("Land area")
    adopted_land_rate: str = _str_field("Adopted land rate")
    gross_land_value: str = _str_field("Gross land value")
    deductions: str = _str_field("Deductions")
    net_land_value: str = _str_field("Net land value")
    built_up_area: str = _str_field("Built-up area")
    structure_type: str = _str_field("Structure type")
    age: str = _str_field("Age")
    useful_life: str = _str_field("Useful life")
    replacement_cost: str = _str_field("Replacement cost")
    source_of_replacement_cost: str = _str_field("Source of replacement cost")
    gross_replacement_cost: str = _str_field("Gross replacement cost")
    physical_depreciation: str = _str_field("Physical depreciation")
    functional_obsolescence: str = _str_field("Functional obsolescence")
    economic_obsolescence: str = _str_field("Economic obsolescence")
    depreciated_replacement_cost: str = _str_field("Depreciated replacement cost")


class IncomeApproachCalculation(BaseModel):
    actual_rent: str = _str_field("Actual rent")
    market_rent: str = _str_field("Market rent")
    gross_annual_rent: str = _str_field("Gross annual rent")
    vacancy: str = _str_field("Vacancy")
    taxes: str = _str_field("Taxes")
    maintenance: str = _str_field("Maintenance")
    insurance: str = _str_field("Insurance")
    repairs: str = _str_field("Repairs")
    management_expenses: str = _str_field("Management expenses")
    net_operating_income: str = _str_field("Net operating income")
    capitalisation_rate: str = _str_field("Capitalisation rate")
    capitalised_value: str = _str_field("Capitalised value")


class DevelopmentResidualCalculation(BaseModel):
    permissible_development_area: str = _str_field("Permissible development area")
    saleable_area: str = _str_field("Saleable area")
    sale_rate: str = _str_field("Sale rate")
    gross_development_value: str = _str_field("Gross development value")
    construction_cost: str = _str_field("Construction cost")
    professional_fees: str = _str_field("Professional fees")
    premium: str = _str_field("Premium")
    approval_cost: str = _str_field("Approval cost")
    finance_cost: str = _str_field("Finance cost")
    marketing_cost: str = _str_field("Marketing cost")
    developers_profit: str = _str_field("Developer's profit")
    time_period: str = _str_field("Time period")
    contingency: str = _str_field("Contingency")
    residual_land_value: str = _str_field("Residual land value")


class ValuationCalculation(BaseModel):
    composite_rate: CompositeRateCalculation = Field(default_factory=CompositeRateCalculation)
    land_and_building: LandAndBuildingCalculation = Field(
        default_factory=LandAndBuildingCalculation
    )
    income_approach: IncomeApproachCalculation = Field(
        default_factory=IncomeApproachCalculation
    )
    development_residual: DevelopmentResidualCalculation = Field(
        default_factory=DevelopmentResidualCalculation
    )


# --- Section 18: Reconciliation and Concluded Values ------------------------


class ReconciliationRow(BaseModel):
    approach: str = _str_field("Valuation approach")
    indicated_value: str = _str_field("Indicated value")
    weight: str = _str_field("Weight assigned")
    weighted_value: str = _str_field("Weighted value")


class ConcludedValues(BaseModel):
    reconciliation: list[ReconciliationRow] = Field(
        default_factory=list, description="Approach/indicated value/weight/weighted value table"
    )
    present_market_value: str = _str_field("Present Market Value, in figures")
    present_market_value_words: str = _str_field("Present Market Value, in words")
    realisable_value_percentage: str = Field(
        default="90", description="Percentage of Present Market Value used for Realisable Value"
    )
    realisable_value: str = _str_field("Realisable Value, in figures")
    realisable_value_words: str = _str_field("Realisable Value, in words")
    forced_sale_value_percentage: str = Field(
        default="80", description="Percentage of Present Market Value used for Forced Sale Value"
    )
    forced_sale_value: str = _str_field("Forced Sale Value, in figures")
    forced_sale_value_words: str = _str_field("Forced Sale Value, in words")


# --- Section 19: Discrepancies and Red Flags --------------------------------


class RedFlag(BaseModel):
    category: str = _str_field(
        "Area discrepancy / unauthorised construction / missing document / RERA "
        "mismatch / title-chain gap / encroachment / litigation / etc."
    )
    description: str = _str_field("Description of the discrepancy or red flag")
    treatment: str = _str_field("How the discrepancy was treated in the valuation")


# --- Top-level report data --------------------------------------------------


class ValuationReportData(BaseModel):
    """The full canonical schema: Stage 1 output, Stage 2 mapping input, Stage 3 injection input."""

    documents_referred_to: list[DocumentReference] = Field(default_factory=list)
    property_identification: PropertyIdentification = Field(
        default_factory=PropertyIdentification
    )
    ownership_and_title: OwnershipAndTitle = Field(default_factory=OwnershipAndTitle)
    area_reconciliation: AreaReconciliation = Field(default_factory=AreaReconciliation)
    boundaries: Boundaries = Field(default_factory=Boundaries)
    site_and_building_particulars: SiteAndBuildingParticulars = Field(
        default_factory=SiteAndBuildingParticulars
    )
    statutory_position: StatutoryPosition = Field(default_factory=StatutoryPosition)
    encumbrances_and_litigation: EncumbrancesAndLitigation = Field(
        default_factory=EncumbrancesAndLitigation
    )
    purpose_and_basis: PurposeAndBasis = Field(default_factory=PurposeAndBasis)
    highest_and_best_use: HighestAndBestUse = Field(default_factory=HighestAndBestUse)
    valuation_approach: ValuationApproachSelection = Field(
        default_factory=ValuationApproachSelection
    )
    applicable_standards: list[str] = Field(
        default_factory=list,
        description="Valuation standards actually applicable to this assignment (IVS, IBBI, RBI, etc.)",
    )
    official_rate_evidence: list[OfficialRateCitation] = Field(default_factory=list)
    market_research_sources: list[MarketResearchSource] = Field(default_factory=list)
    comparable_evidence: list[ComparableEvidence] = Field(default_factory=list)
    valuation_calculation: ValuationCalculation = Field(default_factory=ValuationCalculation)
    concluded_values: ConcludedValues = Field(default_factory=ConcludedValues)
    discrepancies_and_red_flags: list[RedFlag] = Field(default_factory=list)
    limiting_conditions_and_assumptions: list[str] = Field(
        default_factory=list,
        description="Disclosed limiting conditions and assumptions (docs/UPDATED_PROMPTS.md section 20)",
    )


def _nested_model(annotation: object) -> type[BaseModel] | None:
    """Return the BaseModel a field's type points to, whether direct or list[Model]."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    if typing.get_origin(annotation) is list:
        (arg,) = typing.get_args(annotation)
        if isinstance(arg, type) and issubclass(arg, BaseModel):
            return arg
    return None


def canonical_schema_field_list(
    model: type[BaseModel] = ValuationReportData, prefix: str = ""
) -> list[tuple[str, str]]:
    """Flatten the schema into (dotted_field_name, description) pairs.

    Feeds Stage 2's `{{canonical_schema_field_list}}` (docs/UPDATED_PROMPTS.md) — the
    mapping prompt needs a name+description per field, not the nested model shape.
    List-of-model fields are suffixed `[]` to signal a repeating structure (e.g. a
    comparable-evidence table) to the mapping prompt, per that same section.
    """
    pairs: list[tuple[str, str]] = []
    for name, field in model.model_fields.items():
        dotted = f"{prefix}{name}"
        nested = _nested_model(field.annotation)
        if nested is not None:
            is_list = typing.get_origin(field.annotation) is list
            pairs.extend(canonical_schema_field_list(nested, f"{dotted}{'[]' if is_list else ''}."))
        else:
            pairs.append((dotted, field.description or ""))
    return pairs
