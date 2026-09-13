"""
formula_validator.py
---------------------
This module is the engineering "source of truth" for the RAG system.
Every sizing formula is implemented as a pure, unit-tested function with:
  1. A docstring stating the formula, its source/convention, and units.
  2. Input validation against known-reasonable engineering ranges, so
     the system flags (rather than silently accepts) an assumption that
     would be unusual in practice — e.g., a lead-acid DoD of 95%, or a
     derate factor outside 0.65-0.90.

This separates "what an LLM said" from "what a deterministic, reviewable
calculation produced." The RAG pipeline (generation/rag_pipeline.py)
calls these functions directly for any numeric result rather than asking
the LLM to do arithmetic — the LLM's role is retrieval-grounded
explanation and standards citation, not computation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class CalculationResult:
    value: float
    unit: str
    formula: str
    warnings: List[str] = field(default_factory=list)
    assumptions: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Reasonable-range constants used for validation warnings (not hard limits —
# the calculation still proceeds; the caller/LLM is expected to surface the
# warning to the user rather than silently ignore it)
# ---------------------------------------------------------------------------
DERATE_FACTOR_RANGE = (0.65, 0.90)          # combined system losses
DOD_RANGES = {
    "lithium": (0.80, 0.95),
    "lifepo4": (0.80, 0.95),
    "lead_acid": (0.40, 0.60),
    "agm": (0.40, 0.60),
    "gel": (0.40, 0.60),
}
DAYS_AUTONOMY_RANGE = (1, 5)                 # 1 = grid-backup, 5 = deep off-grid
INVERTER_OVERSIZE_RATIO_RANGE = (0.90, 1.30)  # inverter-to-array DC:AC ratio


def validate_derate_factor(derate_factor: float) -> List[str]:
    warnings = []
    lo, hi = DERATE_FACTOR_RANGE
    if not (lo <= derate_factor <= hi):
        warnings.append(
            f"Derate factor {derate_factor:.2f} is outside the typical "
            f"{lo}-{hi} range used in system-loss modeling (wiring, "
            f"inverter, soiling, temperature, mismatch losses combined). "
            f"Double-check the loss breakdown."
        )
    return warnings


def validate_dod(battery_chemistry: str, dod: float) -> List[str]:
    warnings = []
    key = battery_chemistry.lower().replace(" ", "_")
    if key not in DOD_RANGES:
        warnings.append(
            f"Unknown battery chemistry '{battery_chemistry}' — no DoD "
            f"reference range available; verify against the manufacturer datasheet."
        )
        return warnings
    lo, hi = DOD_RANGES[key]
    if not (lo <= dod <= hi):
        warnings.append(
            f"DoD {dod:.0%} is outside the typical {lo:.0%}-{hi:.0%} range "
            f"for {battery_chemistry} batteries. Exceeding the safe DoD "
            f"materially shortens cycle life."
        )
    return warnings


def validate_days_autonomy(days: float) -> List[str]:
    warnings = []
    lo, hi = DAYS_AUTONOMY_RANGE
    if days < lo:
        warnings.append(
            f"{days} day(s) of autonomy is below typical minimums even for "
            f"grid-backup hybrid systems (usually >= {lo})."
        )
    elif days > hi:
        warnings.append(
            f"{days} days of autonomy exceeds typical off-grid design practice "
            f"(usually <= {hi}); this substantially increases battery cost — "
            f"confirm this is intentional for a remote/critical-load site."
        )
    return warnings


def validate_inverter_ratio(ratio: float) -> List[str]:
    warnings = []
    lo, hi = INVERTER_OVERSIZE_RATIO_RANGE
    if not (lo <= ratio <= hi):
        warnings.append(
            f"Inverter-to-array DC:AC ratio of {ratio:.2f} is outside the "
            f"common {lo}-{hi} design range. Ratios below {lo} risk inverter "
            f"clipping losses in strong sun; ratios above {hi} mean an "
            f"oversized (costlier) inverter relative to the array."
        )
    return warnings


# ---------------------------------------------------------------------------
# Core sizing formulas
# ---------------------------------------------------------------------------

def size_array(daily_load_wh: float, psh: float, derate_factor: float = 0.80) -> CalculationResult:
    """
    Array sizing formula (standard PV design convention, e.g. NREL/IEEE
    sizing guides):

        Array_W = Daily_Load_Wh / (PSH * Derate_Factor)

    Args:
        daily_load_wh: total daily energy demand including design margin, in Wh.
        psh: peak sun hours for the design month (use the WORST month for
             autonomous/hybrid systems per conservative design practice).
        derate_factor: combined system losses (wiring, inverter, soiling,
             temperature, mismatch) as a fraction retained (e.g. 0.80 = 20% loss).
    """
    warnings = validate_derate_factor(derate_factor)
    if psh <= 0:
        raise ValueError("PSH must be positive.")
    if daily_load_wh <= 0:
        raise ValueError("daily_load_wh must be positive.")

    array_w = daily_load_wh / (psh * derate_factor)

    return CalculationResult(
        value=round(array_w, 1),
        unit="W (DC, STC-rated)",
        formula="Array_W = Daily_Load_Wh / (PSH * Derate_Factor)",
        warnings=warnings,
        assumptions={"daily_load_wh": daily_load_wh, "psh": psh, "derate_factor": derate_factor},
    )


def size_inverter(array_w: float, simultaneous_load_w: float,
                   dc_ac_ratio: float = 1.10) -> CalculationResult:
    """
    Inverter continuous-power sizing.

        Inverter_W = max(array_w / dc_ac_ratio_implied_check, simultaneous_load_w)

    In practice we size the inverter primarily to array capacity within a
    sane DC:AC ratio band, then confirm it also covers the worst-case
    simultaneous AC load (evening peak, etc.) — whichever requirement is
    larger governs.

    Args:
        array_w: DC array rating in W.
        simultaneous_load_w: the largest realistic simultaneous AC load, in W
             (NOT the sum of all loads — the loads actually expected to run together).
        dc_ac_ratio: array_W / inverter_W target ratio.
    """
    if dc_ac_ratio <= 0:
        raise ValueError("dc_ac_ratio must be positive.")

    inverter_from_ratio = array_w / dc_ac_ratio
    inverter_w = max(inverter_from_ratio, simultaneous_load_w)

    actual_ratio = array_w / inverter_w if inverter_w else float("nan")
    warnings = validate_inverter_ratio(actual_ratio)

    if simultaneous_load_w > inverter_from_ratio:
        warnings.append(
            "Sizing was governed by the simultaneous AC load requirement, "
            "not the array DC:AC ratio target — confirm surge/startup current "
            "of motor loads is also within the inverter's surge rating."
        )

    return CalculationResult(
        value=round(inverter_w, 1),
        unit="W (AC continuous)",
        formula="Inverter_W = max(Array_W / DC_AC_Ratio, Simultaneous_Load_W)",
        warnings=warnings,
        assumptions={
            "array_w": array_w,
            "simultaneous_load_w": simultaneous_load_w,
            "dc_ac_ratio_target": dc_ac_ratio,
            "actual_ratio": round(actual_ratio, 2),
        },
    )


def size_battery_bank(
    daily_load_wh: float,
    days_autonomy: float,
    system_voltage_v: float,
    dod: float,
    battery_chemistry: str = "lifepo4",
) -> CalculationResult:
    """
    Battery bank sizing (standard off-grid/hybrid convention):

        Battery_Ah = (Daily_Load_Wh * Days_Autonomy) / (System_Voltage_V * DoD)

    Args:
        daily_load_wh: total daily energy demand, in Wh.
        days_autonomy: number of no-sun days the bank must cover.
        system_voltage_v: nominal DC bus voltage (e.g., 12/24/48V).
        dod: depth of discharge as a fraction (e.g., 0.90 for 90%).
        battery_chemistry: used only for DoD-range validation warnings.
    """
    warnings = validate_dod(battery_chemistry, dod)
    warnings += validate_days_autonomy(days_autonomy)

    if system_voltage_v <= 0 or dod <= 0:
        raise ValueError("system_voltage_v and dod must be positive.")

    battery_ah = (daily_load_wh * days_autonomy) / (system_voltage_v * dod)
    battery_kwh_nominal = (battery_ah * system_voltage_v) / 1000.0

    return CalculationResult(
        value=round(battery_ah, 1),
        unit=f"Ah @ {system_voltage_v}V (nominal capacity ≈ {battery_kwh_nominal:.1f} kWh)",
        formula="Battery_Ah = (Daily_Load_Wh * Days_Autonomy) / (System_Voltage_V * DoD)",
        warnings=warnings,
        assumptions={
            "daily_load_wh": daily_load_wh,
            "days_autonomy": days_autonomy,
            "system_voltage_v": system_voltage_v,
            "dod": dod,
            "battery_chemistry": battery_chemistry,
        },
    )


def size_charge_controller(array_w: float, system_voltage_v: float,
                            safety_factor: float = 1.25) -> CalculationResult:
    """
    Charge controller (MPPT/PWM) current rating.

        Controller_A = (Array_W / System_Voltage_V) * Safety_Factor

    The 1.25 safety factor is the common NEC-690-aligned convention
    accounting for irradiance enhancement (edge-of-cloud effect) that can
    briefly push array output above STC rating.
    """
    if system_voltage_v <= 0:
        raise ValueError("system_voltage_v must be positive.")

    max_current = array_w / system_voltage_v
    controller_a = max_current * safety_factor

    warnings = []
    if safety_factor < 1.20:
        warnings.append(
            "Safety factor below 1.20 provides little margin for irradiance "
            "enhancement above STC conditions; 1.25 is the common convention."
        )

    return CalculationResult(
        value=round(controller_a, 1),
        unit="A",
        formula="Controller_A = (Array_W / System_Voltage_V) * Safety_Factor",
        warnings=warnings,
        assumptions={
            "array_w": array_w,
            "system_voltage_v": system_voltage_v,
            "safety_factor": safety_factor,
        },
    )


def apply_design_margin(base_load_wh: float, margin_fraction: float = 0.25) -> CalculationResult:
    """
    Applies a design safety margin to a raw daily load estimate to absorb
    estimation error and headroom for future load growth.

        Adjusted_Load_Wh = Base_Load_Wh * (1 + margin_fraction)
    """
    warnings = []
    if not (0.10 <= margin_fraction <= 0.40):
        warnings.append(
            f"Design margin of {margin_fraction:.0%} is outside the typical "
            f"10%-40% range used in load estimation."
        )

    adjusted = base_load_wh * (1 + margin_fraction)
    return CalculationResult(
        value=round(adjusted, 1),
        unit="Wh/day",
        formula="Adjusted_Load_Wh = Base_Load_Wh * (1 + Margin_Fraction)",
        warnings=warnings,
        assumptions={"base_load_wh": base_load_wh, "margin_fraction": margin_fraction},
    )
