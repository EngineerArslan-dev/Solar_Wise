"""
solar_sizing_engine.py
------------------------
The deterministic Python calculation engine — Solar Wise PRD Section 9's
"Can we calculate the solar system correctly?" responsibility, originally
assigned to the Engineering/Technical Developer role.

This module owns the top-level orchestration (PRD Section 5.1 inputs ->
Section 5.2 outputs). It does NOT reimplement the underlying physics —
it calls the already-tested formulas in validation/formula_validator.py
and validation/load_calculator.py, and combines them with:
  - bill<->kWh conversion (engine/tariff.py)
  - on-grid / hybrid / off-grid branching
  - backup-requirement-driven battery sizing
  - roof-area fit validation
  - budget-constrained scenario solving
  - equipment-catalog-grounded cost RANGES (not a single point estimate)
  - annual generation and payback

Every numeric result traces back to a formula or a real catalog row —
nothing here is LLM-generated, per the PRD's core guardrail (Section
6.2): the AI layer explains this engine's output, never computes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from config import PAKISTAN_CITIES
from engine.tariff import bill_to_kwh, marginal_rate
from validation.formula_validator import (
    size_array, size_inverter, size_battery_bank, size_charge_controller,
)
from data_ingestion.dataset_loader import load_equipment_datasets

# ---------------------------------------------------------------------------
# Reference constants (each documented with its source/derivation)
# ---------------------------------------------------------------------------

# Derived directly from this project's own equipment catalog, not assumed:
# Jinko Tiger Neo 585W panel, 2278mm x 1134mm = 2.583 m^2 = 27.8 sqft.
# 27.8 sqft / 585 W = 0.0475 sqft per watt of array capacity.
PANEL_SQFT_PER_WATT = 0.0475

# Worst-month PSH (sizing) and annual-average PSH (generation estimate)
# reference values. Chakwal's are genuinely live-fetched (see
# data/documents/dataset_documentation/chakwal_nasa_power_verified_2018_2023.json).
# Others are literature-compiled reference figures — see
# data/documents/dataset_documentation/pakistan_irradiance_reference_data.md.
# Live NASA POWER fetch (data_ingestion/weather_fetcher.py) is authoritative
# when network access is available; these are the offline-safe fallback.
CITY_PSH_REFERENCE = {
    "Karachi":     {"worst_month": 3.4, "annual_avg": 5.6},
    "Lahore":      {"worst_month": 3.6, "annual_avg": 5.5},
    "Islamabad":   {"worst_month": 3.0, "annual_avg": 5.3},
    "Chakwal":     {"worst_month": 2.95, "annual_avg": 5.02},  # live-fetched, verified
    "Multan":      {"worst_month": 3.5, "annual_avg": 5.6},
    "Peshawar":    {"worst_month": 2.8, "annual_avg": 5.2},
    "Quetta":      {"worst_month": 2.4, "annual_avg": 5.8},
    "Faisalabad":  {"worst_month": 3.5, "annual_avg": 5.5},
    "Rawalpindi":  {"worst_month": 3.0, "annual_avg": 5.3},
    "Hyderabad":   {"worst_month": 3.4, "annual_avg": 5.6},
    "Sialkot":     {"worst_month": 3.5, "annual_avg": 5.4},
    "Sukkur":      {"worst_month": 3.4, "annual_avg": 5.7},
}

DEFAULT_PANEL_RATING_W = 585  # most common rating in the equipment catalog
DEFAULT_DERATE_FACTOR = 0.80
DEFAULT_DC_AC_RATIO = 1.10
DEFAULT_VOLTAGE = 48
DEFAULT_DOD = 0.90
DEFAULT_CHEMISTRY = "lifepo4"
DEFAULT_BOS_COST_PKR = 50000
DEFAULT_LABOR_PCT = 0.15

# Backup requirement -> (fraction of full daily load to back up, days of autonomy)
# "essential" fraction is a documented planning assumption (lighting, fans,
# fridge, router — not heavy loads like AC/pumps), adjustable via the
# essential_load_fraction parameter if a real appliance breakdown is available.
BACKUP_REQUIREMENT_MAP = {
    "none": {"load_fraction": 0.0, "days_autonomy": 0},
    "essential": {"load_fraction": 0.35, "days_autonomy": 1},
    "full_house": {"load_fraction": 1.0, "days_autonomy": 1},
}


@dataclass
class SizingRequest:
    city: str
    monthly_kwh: Optional[float] = None
    monthly_bill_pkr: Optional[float] = None
    protected_tariff: bool = False
    roof_area_sqft: Optional[float] = None
    backup_requirement: str = "essential"  # none | essential | full_house
    system_type: str = "hybrid"  # on_grid | hybrid | off_grid
    panel_rating_w: Optional[float] = None
    budget_ceiling_pkr: Optional[float] = None
    days_autonomy_override: Optional[int] = None
    grid_tariff_override: Optional[float] = None


@dataclass
class SizingResult:
    required_capacity_kw: float
    panel_count: int
    panel_rating_w: float
    inverter_capacity_kw: float
    battery_capacity_kwh: float
    annual_generation_kwh: float
    cost_low_pkr: float
    cost_high_pkr: float
    annual_savings_pkr: float
    payback_years: float
    warnings: List[str] = field(default_factory=list)
    assumptions: Dict = field(default_factory=dict)
    budget_constrained: bool = False


def _resolve_monthly_kwh(req: SizingRequest) -> tuple[float, List[str]]:
    warnings = []
    if req.monthly_kwh is not None and req.monthly_bill_pkr is not None:
        warnings.append("Both monthly_kwh and monthly_bill_pkr given — using monthly_kwh directly.")
        return req.monthly_kwh, warnings
    if req.monthly_kwh is not None:
        return req.monthly_kwh, warnings
    if req.monthly_bill_pkr is not None:
        estimate = bill_to_kwh(req.monthly_bill_pkr, protected=req.protected_tariff)
        warnings.extend(estimate.warnings)
        return estimate.kwh, warnings
    raise ValueError("Provide either monthly_kwh or monthly_bill_pkr.")


def _resolve_psh(city: str) -> tuple[float, float, List[str]]:
    warnings = []
    if city not in CITY_PSH_REFERENCE:
        warnings.append(f"No PSH reference for '{city}' — using national-average fallback values.")
        return 3.2, 5.4, warnings
    ref = CITY_PSH_REFERENCE[city]
    if city != "Chakwal":
        warnings.append(
            f"PSH for {city} is a literature-compiled reference value, not a live "
            f"NASA POWER fetch — run data_ingestion/weather_fetcher.py for current, "
            f"location-precise figures when network access is available."
        )
    return ref["worst_month"], ref["annual_avg"], warnings


def _catalog_by_type(catalog_rows) -> Dict[str, List[Dict]]:
    by_type: Dict[str, List[Dict]] = {"panel": [], "inverter": [], "battery": [], "controller": []}
    for row in catalog_rows:
        t = row.metadata.get("item_type")
        if t in by_type:
            by_type[t].append(row.metadata)
    return by_type


def _cost_bounds(array_w: float, inverter_w: float, battery_kwh: float,
                  catalog_by_type: Dict) -> tuple[float, float, List[str]]:
    """Cost range grounded in the actual equipment catalog's cheapest and
    priciest matching entries, not an arbitrary +/- percentage band."""
    warnings = []

    def _price_per_watt(items, key="item_price_pkr", power_key="item_rated_power_w"):
        prices = []
        for item in items:
            try:
                price = float(item.get(key, 0))
                power = float(item.get(power_key, 0))
                if power > 0:
                    prices.append(price / power)
            except (TypeError, ValueError):
                continue
        return prices

    panel_ppw = _price_per_watt(catalog_by_type["panel"])
    inverter_ppw = _price_per_watt(catalog_by_type["inverter"])
    battery_prices = [
        float(b.get("item_price_pkr", 0)) for b in catalog_by_type["battery"]
        if b.get("item_price_pkr")
    ]

    if not panel_ppw or not inverter_ppw:
        warnings.append("Equipment catalog missing panel/inverter pricing — using fallback per-watt estimates.")
        panel_ppw = panel_ppw or [40]
        inverter_ppw = inverter_ppw or [25]

    panel_cost_low = array_w * min(panel_ppw)
    panel_cost_high = array_w * max(panel_ppw)
    inverter_cost_low = inverter_w * min(inverter_ppw)
    inverter_cost_high = inverter_w * max(inverter_ppw)

    if battery_kwh > 0 and battery_prices:
        # Catalog battery prices are per-unit (e.g. ~5kWh module) — scale
        # by nominal module size (~5kWh) to approximate cost per kWh needed.
        battery_cost_low = battery_kwh * (min(battery_prices) / 5.0)
        battery_cost_high = battery_kwh * (max(battery_prices) / 5.0)
    elif battery_kwh > 0:
        warnings.append("No battery pricing in catalog — using fallback Rs 35,000/kWh estimate.")
        battery_cost_low = battery_cost_high = battery_kwh * 35000
    else:
        battery_cost_low = battery_cost_high = 0.0

    hardware_low = panel_cost_low + inverter_cost_low + battery_cost_low + DEFAULT_BOS_COST_PKR
    hardware_high = panel_cost_high + inverter_cost_high + battery_cost_high + DEFAULT_BOS_COST_PKR

    cost_low = hardware_low * (1 + DEFAULT_LABOR_PCT)
    cost_high = hardware_high * (1 + DEFAULT_LABOR_PCT)

    return cost_low, cost_high, warnings


def run_solar_sizing(req: SizingRequest) -> SizingResult:
    warnings: List[str] = []
    assumptions: Dict = {}

    # 1. Resolve daily load
    monthly_kwh, w = _resolve_monthly_kwh(req)
    warnings.extend(w)
    daily_load_wh = (monthly_kwh * 1000) / 30
    assumptions["monthly_kwh"] = monthly_kwh
    assumptions["daily_load_wh"] = round(daily_load_wh, 1)

    # 2. Resolve irradiance
    worst_psh, annual_psh, w = _resolve_psh(req.city)
    warnings.extend(w)

    # 3. Backup requirement -> battery target load + days autonomy
    if req.system_type == "on_grid" and req.backup_requirement != "none":
        warnings.append(
            "On-grid systems provide no outage backup — battery sizing "
            "skipped despite a backup requirement being requested. "
            "Select 'hybrid' or 'off_grid' for backup capability."
        )
        backup_cfg = BACKUP_REQUIREMENT_MAP["none"]
    else:
        backup_cfg = BACKUP_REQUIREMENT_MAP.get(req.backup_requirement, BACKUP_REQUIREMENT_MAP["essential"])

    days_autonomy = req.days_autonomy_override or backup_cfg["days_autonomy"]
    if req.system_type == "off_grid" and days_autonomy < 2:
        days_autonomy = max(days_autonomy, 2)
        warnings.append("Off-grid systems default to a minimum 2 days of autonomy for reliability.")

    backup_load_wh = daily_load_wh * backup_cfg["load_fraction"]
    assumptions["backup_load_fraction"] = backup_cfg["load_fraction"]
    assumptions["days_autonomy"] = days_autonomy
    assumptions["worst_month_psh"] = worst_psh
    assumptions["annual_avg_psh"] = annual_psh
    assumptions["battery_voltage_v"] = DEFAULT_VOLTAGE
    assumptions["battery_dod"] = DEFAULT_DOD
    assumptions["derate_factor"] = DEFAULT_DERATE_FACTOR

    # 4. Array sizing (always sized to the FULL daily load — the panels
    # offset consumption regardless of backup requirement; only the
    # battery target scales with backup requirement)
    array_result = size_array(daily_load_wh, worst_psh, derate_factor=DEFAULT_DERATE_FACTOR)
    array_w = array_result.value
    warnings.extend(array_result.warnings)

    # 5. Roof area check — cap the array if it doesn't physically fit
    panel_rating_w = req.panel_rating_w or DEFAULT_PANEL_RATING_W
    required_sqft = array_w * PANEL_SQFT_PER_WATT
    if req.roof_area_sqft is not None and required_sqft > req.roof_area_sqft:
        max_array_w = req.roof_area_sqft / PANEL_SQFT_PER_WATT
        warnings.append(
            f"Recommended array ({round(array_w)}W, needing ~{round(required_sqft)} sqft) "
            f"exceeds the available roof area ({req.roof_area_sqft} sqft). Capped to "
            f"~{round(max_array_w)}W — this system will not fully offset the target load."
        )
        array_w = max_array_w

    panel_count = max(1, round(array_w / panel_rating_w))
    array_w = panel_count * panel_rating_w  # snap to whole-panel increments

    # 6. Inverter sizing
    inverter_result = size_inverter(array_w, simultaneous_load_w=array_w * 0.5, dc_ac_ratio=DEFAULT_DC_AC_RATIO)
    inverter_w = inverter_result.value
    warnings.extend(inverter_result.warnings)

    # 7. Battery sizing (system-type + backup-requirement driven)
    if req.system_type == "on_grid" or backup_cfg["days_autonomy"] == 0:
        battery_kwh = 0.0
    else:
        battery_result = size_battery_bank(
            backup_load_wh, days_autonomy, DEFAULT_VOLTAGE, DEFAULT_DOD, DEFAULT_CHEMISTRY
        )
        battery_kwh = (battery_result.value * DEFAULT_VOLTAGE) / 1000
        warnings.extend(battery_result.warnings)

    # 8. Cost range from the actual equipment catalog
    catalog_rows = load_equipment_datasets()
    catalog_by_type = _catalog_by_type(catalog_rows)
    cost_low, cost_high, w = _cost_bounds(array_w, inverter_w, battery_kwh, catalog_by_type)
    warnings.extend(w)

    # 9. Budget-constrained scenario — bisection search on a scale factor,
    # since cost is monotonic in scale but includes a FIXED BOS cost floor
    # (Rs 50,000 regardless of system size), so a single-shot proportional
    # scale-down undershoots: the fixed cost becomes a larger fraction of
    # the smaller system's total. Bisection converges correctly regardless.
    budget_constrained = False
    if req.budget_ceiling_pkr is not None and cost_low > req.budget_ceiling_pkr:
        budget_constrained = True
        original_array_w, original_inverter_w, original_battery_kwh = array_w, inverter_w, battery_kwh

        lo, hi = 0.0, 1.0
        for _ in range(40):  # ample precision for a monotonic 1D search
            mid = (lo + hi) / 2
            trial_cost_low, _, _ = _cost_bounds(
                original_array_w * mid, original_inverter_w * mid, original_battery_kwh * mid,
                catalog_by_type,
            )
            if trial_cost_low <= req.budget_ceiling_pkr:
                lo = mid
            else:
                hi = mid
        scale = lo

        warnings.append(
            f"Budget ceiling (Rs {req.budget_ceiling_pkr:,.0f}) is below the lowest-cost "
            f"estimate (Rs {cost_low:,.0f}) for the full recommendation. Scaling the system "
            f"down by ~{round((1 - scale) * 100)}% to fit — this covers a smaller share of "
            f"the target load, not the full daily consumption."
        )
        array_w = original_array_w * scale
        inverter_w = original_inverter_w * scale
        battery_kwh = original_battery_kwh * scale
        panel_count = max(1, round(array_w / panel_rating_w))
        array_w = panel_count * panel_rating_w
        cost_low, cost_high, _ = _cost_bounds(array_w, inverter_w, battery_kwh, catalog_by_type)

        # Rounding panel_count can push cost back slightly over budget —
        # step down one panel at a time until it's genuinely back in range.
        while cost_low > req.budget_ceiling_pkr and panel_count > 1:
            panel_count -= 1
            array_w = panel_count * panel_rating_w
            scale_adj = array_w / (original_array_w if original_array_w > 0 else 1)
            inverter_w = original_inverter_w * scale_adj
            battery_kwh = original_battery_kwh * scale_adj
            cost_low, cost_high, _ = _cost_bounds(array_w, inverter_w, battery_kwh, catalog_by_type)

    # 10. Annual generation (uses ANNUAL AVERAGE psh, not worst-month)
    annual_generation_kwh = (array_w / 1000) * annual_psh * 365 * DEFAULT_DERATE_FACTOR

    # 11. Annual savings — self-consumption model (see cost/payback caveats
    # documented throughout this project's README: does not model net-
    # metering export revenue, which is credited at a separate rate under
    # Pakistan's current net-billing framework)
    tariff = req.grid_tariff_override or marginal_rate(monthly_kwh, protected=req.protected_tariff)
    daily_generation_kwh = annual_generation_kwh / 365
    self_consumed_daily_kwh = min(daily_generation_kwh, daily_load_wh / 1000)
    annual_savings_pkr = self_consumed_daily_kwh * tariff * 365
    assumptions["tariff_pkr_per_kwh"] = tariff

    # 12. Payback (midpoint of cost range)
    cost_mid = (cost_low + cost_high) / 2
    payback_years = cost_mid / annual_savings_pkr if annual_savings_pkr > 0 else float("inf")

    return SizingResult(
        required_capacity_kw=round(array_w / 1000, 2),
        panel_count=panel_count,
        panel_rating_w=panel_rating_w,
        inverter_capacity_kw=round(inverter_w / 1000, 2),
        battery_capacity_kwh=round(battery_kwh, 1),
        annual_generation_kwh=round(annual_generation_kwh, 0),
        cost_low_pkr=round(cost_low, 0),
        cost_high_pkr=round(cost_high, 0),
        annual_savings_pkr=round(annual_savings_pkr, 0),
        payback_years=round(payback_years, 1) if payback_years != float("inf") else payback_years,
        warnings=warnings,
        assumptions=assumptions,
        budget_constrained=budget_constrained,
    )


def to_calculated_results(result: SizingResult):
    """
    Bridges SizingResult into the same CalculationResult-shaped dict the
    RAG generation layer expects (generation/rag_pipeline.py and
    generation/groq_pipeline.py's `calculated_results` parameter) — so
    Hassan's integration can pass this engine's output straight into the
    AI explanation layer without reconciling two different shapes:

        result = run_solar_sizing(request)
        response = answer_query_groq(
            "Explain this sizing result.", kb,
            calculated_results=to_calculated_results(result),
        )
    """
    from validation.formula_validator import CalculationResult

    shared_warnings = result.warnings
    return {
        "Required PV capacity": CalculationResult(
            value=result.required_capacity_kw, unit="kW",
            formula="Array_W = Daily_Load_Wh / (worst-month PSH x derate factor)",
            warnings=shared_warnings, assumptions=result.assumptions,
        ),
        "Panel configuration": CalculationResult(
            value=result.panel_count, unit=f"panels x {result.panel_rating_w}W",
            formula="panel_count = round(Array_W / panel_rating_w)",
            warnings=[], assumptions={},
        ),
        "Inverter capacity": CalculationResult(
            value=result.inverter_capacity_kw, unit="kW",
            formula="Inverter_W = max(Array_W / DC:AC ratio, simultaneous load)",
            warnings=[], assumptions={},
        ),
        "Battery capacity": CalculationResult(
            value=result.battery_capacity_kwh, unit="kWh",
            formula="Battery_Ah = (backup_load_Wh x days_autonomy) / (voltage x DoD)",
            warnings=[], assumptions={},
        ),
        "Annual generation": CalculationResult(
            value=result.annual_generation_kwh, unit="kWh/yr",
            formula="Array_kW x annual-average PSH x 365 x derate factor",
            warnings=[], assumptions={},
        ),
        "Estimated system cost": CalculationResult(
            value=f"{result.cost_low_pkr:,.0f}-{result.cost_high_pkr:,.0f}", unit="PKR (range)",
            formula="Catalog-grounded: cheapest-to-priciest matching panel/inverter/battery + BOS + labor",
            warnings=[], assumptions={"budget_constrained": result.budget_constrained},
        ),
        "Annual savings": CalculationResult(
            value=result.annual_savings_pkr, unit="PKR/yr",
            formula="min(daily generation, daily load) x tariff x 365 (self-consumption only)",
            warnings=[], assumptions={"tariff_pkr_per_kwh": result.assumptions.get("tariff_pkr_per_kwh")},
        ),
        "Payback period": CalculationResult(
            value=result.payback_years, unit="years",
            formula="cost (midpoint of range) / annual savings",
            warnings=[], assumptions={},
        ),
    }
