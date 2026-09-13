"""
load_calculator.py
-------------------
Computes total daily energy demand (Wh/day) from individual appliance
inputs (wattage, hours of use per day, quantity) instead of requiring
the user to pre-calculate a single total daily-load figure by hand.

Three ways to use this module, in order of reliability inside Colab:

  1. JSON file (RECOMMENDED for Colab): edit a JSON file listing your
     appliances directly in the Files sidebar, then load it with
     load_appliances_from_json() + calculate_daily_load(). This avoids
     any interactive-input reliability issues entirely.

  2. Direct notebook cell call: call interactive_load_survey() from a
     normal Python code cell (NOT via `!python main.py ...`). Jupyter/
     Colab's kernel handles input() natively and reliably when the
     function runs in-process.

  3. Local terminal use: `python main.py load-survey` works interactively
     end-to-end on a local machine/terminal, since there's no subprocess
     stdin boundary to cross. Not recommended through Colab's `!` magic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from validation.formula_validator import CalculationResult


@dataclass
class Appliance:
    name: str
    power_w: float
    hours_per_day: float
    quantity: int = 1

    def daily_wh(self) -> float:
        return self.power_w * self.hours_per_day * self.quantity


def _validate_appliance(appliance: Appliance) -> List[str]:
    warnings = []
    if appliance.power_w <= 0:
        warnings.append(f"'{appliance.name}': power_w must be positive.")
    if not (0 < appliance.hours_per_day <= 24):
        warnings.append(
            f"'{appliance.name}': hours_per_day should be between 0 and 24 "
            f"(got {appliance.hours_per_day})."
        )
    if appliance.quantity <= 0:
        warnings.append(f"'{appliance.name}': quantity must be positive.")
    if appliance.power_w > 10000:
        warnings.append(
            f"'{appliance.name}': {appliance.power_w}W is unusually high for a "
            f"single residential/commercial appliance — confirm this isn't a typo "
            f"(e.g. kW entered where W was expected)."
        )
    return warnings


def calculate_daily_load(appliances: List[Appliance]) -> CalculationResult:
    """
    Sums Wh/day across all appliances:

        Daily_Load_Wh = sum(Power_W * Hours_Per_Day * Quantity)

    Returns a CalculationResult with a per-appliance breakdown in
    `assumptions["appliance_breakdown_wh_per_day"]`, so the RAG
    explanation layer (or you) can see exactly which appliance drove
    the total, not just the final number.
    """
    if not appliances:
        raise ValueError("At least one appliance is required.")

    warnings: List[str] = []
    breakdown = {}
    total_wh = 0.0
    for a in appliances:
        warnings.extend(_validate_appliance(a))
        wh = a.daily_wh()
        breakdown[a.name] = round(wh, 1)
        total_wh += wh

    return CalculationResult(
        value=round(total_wh, 1),
        unit="Wh/day",
        formula="Daily_Load_Wh = sum(Power_W * Hours_Per_Day * Quantity)",
        warnings=warnings,
        assumptions={"appliance_breakdown_wh_per_day": breakdown},
    )


def load_appliances_from_json(path: Path) -> List[Appliance]:
    """
    Expects a JSON file structured as a list of objects:

        [
          {"name": "LED bulb", "power_w": 10, "hours_per_day": 6, "quantity": 10},
          {"name": "Ceiling fan", "power_w": 75, "hours_per_day": 10, "quantity": 4}
        ]

    "quantity" is optional and defaults to 1 if omitted.
    """
    data = json.loads(Path(path).read_text())
    if not isinstance(data, list):
        raise ValueError("Appliances JSON must be a list of appliance objects.")

    return [
        Appliance(
            name=item["name"],
            power_w=float(item["power_w"]),
            hours_per_day=float(item["hours_per_day"]),
            quantity=int(item.get("quantity", 1)),
        )
        for item in data
    ]


def interactive_load_survey() -> CalculationResult:
    """
    Prompts for appliances one at a time (name, wattage, hours/day,
    quantity) until the user types 'done' as the name. Returns the
    total via calculate_daily_load().

    Call this directly in a Jupyter/Colab notebook cell for reliable
    input() behavior:

        from validation.load_calculator import interactive_load_survey
        result = interactive_load_survey()
        daily_load_wh = result.value
    """
    appliances: List[Appliance] = []
    print("Enter each appliance's details. Type 'done' as the appliance name to finish.\n")

    while True:
        name = input("Appliance name (or 'done' to finish): ").strip()
        if name.lower() == "done":
            break
        if not name:
            print("Name cannot be empty, try again.")
            continue
        try:
            power_w = float(input(f"  Power rating of '{name}' in Watts: ").strip())
            hours_per_day = float(input(f"  Hours per day '{name}' is used: ").strip())
            qty_raw = input(f"  Quantity of '{name}' (press Enter for 1): ").strip()
            quantity = int(qty_raw) if qty_raw else 1
        except ValueError:
            print("  Invalid number entered — please re-enter this appliance.\n")
            continue

        appliances.append(
            Appliance(name=name, power_w=power_w, hours_per_day=hours_per_day, quantity=quantity)
        )
        print(
            f"  Added: {name} -> {power_w}W x {hours_per_day}h x {quantity} "
            f"= {power_w * hours_per_day * quantity:.1f} Wh/day\n"
        )

    if not appliances:
        raise ValueError("No appliances entered.")

    result = calculate_daily_load(appliances)

    print("\n--- Load Summary ---")
    for name, wh in result.assumptions["appliance_breakdown_wh_per_day"].items():
        print(f"  {name}: {wh} Wh/day")
    print(f"TOTAL: {result.value} Wh/day")
    for w in result.warnings:
        print(f"  ⚠ {w}")

    return result


if __name__ == "__main__":
    interactive_load_survey()
