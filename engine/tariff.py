"""
tariff.py
---------
Pakistani residential electricity tariff slabs, used to convert a
monthly bill (PKR) to estimated consumption (kWh) when the user gives a
bill rather than a known unit count — required by the PRD (Section 5.1:
"Bill is converted to kWh via tariff slabs if consumption is not
given").

SOURCING AND HONEST LIMITS: figures below are compiled from current
(2026) NEPRA/K-Electric rate reporting, dated to the S.R.O. 279(I)/2026
schedule (effective 12 Feb 2026) and K-Electric's February 2026 revision
specifically, since the PRD's own worked example uses Karachi.
Cross-source reporting shows some variance (a few rupees per unit)
between outlets summarizing the same official schedule, and rates are
revised further via monthly Fuel Price/Quarterly Tariff Adjustments on
top of the base slab rate. Treat these as a reasonable planning
approximation, not the exact figure on any specific bill — the PRD's
own risk register (Section 10.1) explicitly anticipates this ("data
staleness... mitigated by clear 'as of' labeling").

Billing is NON-TELESCOPIC: Pakistani residential domestic tariffs bill
the ENTIRE month's consumption at the rate of the highest slab reached,
not a graduated/telescoping rate per band (confirmed across multiple
2026 sources) — except for "protected" consumers (verified average
consumption <=200 units over 6 consecutive months), who get the benefit
of the previous slab's rate on their first 100 units.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

TARIFF_AS_OF = "S.R.O. 279(I)/2026 (12 Feb 2026), K-Electric-specific revision — verify against current DISCO schedule"

# (upper bound of slab in kWh, rate in PKR/kWh) — ordered ascending.
# Non-telescopic: a consumer using N units pays N * rate(slab containing N).
UNPROTECTED_SLABS: List[Tuple[int, float]] = [
    (100, 23.59),
    (200, 25.10),
    (300, 27.04),
    (400, 36.46),
    (500, 38.95),
    (600, 42.50),
    (700, 45.20),
    (float("inf"), 47.69),
]

# Protected consumers get the previous slab's rate on their first 100
# units — only valid up to 200 units total; above that, protected status
# doesn't apply and UNPROTECTED_SLABS governs instead.
PROTECTED_SLABS: List[Tuple[int, float]] = [
    (100, 7.74),
    (200, 13.48),
]


@dataclass
class TariffEstimate:
    kwh: float
    marginal_rate_pkr_per_kwh: float
    protected: bool
    warnings: List[str]


def _slab_rate(units: float, slabs: List[Tuple[int, float]]) -> float:
    for upper, rate in slabs:
        if units <= upper:
            return rate
    return slabs[-1][1]


def kwh_to_bill(monthly_kwh: float, protected: bool = False) -> float:
    """Non-telescopic: entire consumption billed at the reached slab's rate."""
    slabs = PROTECTED_SLABS if (protected and monthly_kwh <= 200) else UNPROTECTED_SLABS
    rate = _slab_rate(monthly_kwh, slabs)
    return monthly_kwh * rate


def bill_to_kwh(monthly_bill_pkr: float, protected: bool = False) -> TariffEstimate:
    """
    Inverts kwh_to_bill(): since billing is non-telescopic (bill = units *
    rate(slab reached)), for each candidate slab we solve
    units = bill / slab_rate and check whether that units value actually
    falls within the slab's own boundaries (self-consistency check) —
    the correct slab is the one where this holds.
    """
    warnings: List[str] = []
    slabs = PROTECTED_SLABS if protected else UNPROTECTED_SLABS
    lower = 0.0

    for upper, rate in slabs:
        candidate_units = monthly_bill_pkr / rate
        if lower < candidate_units <= upper:
            return TariffEstimate(
                kwh=round(candidate_units, 1),
                marginal_rate_pkr_per_kwh=rate,
                protected=protected,
                warnings=warnings,
            )
        lower = upper

    # Bill doesn't cleanly match any slab (can happen with FCA/QTA
    # adjustments or taxes folded into the entered bill) — fall back to
    # the highest slab's rate as a reasonable estimate and flag it.
    fallback_rate = slabs[-1][1]
    warnings.append(
        "Bill amount didn't cleanly match a single tariff slab (likely "
        "includes taxes/FCA/fixed charges beyond the base per-unit rate) "
        "— estimated using the highest slab's rate. For accuracy, enter "
        "monthly kWh directly from the bill if available."
    )
    return TariffEstimate(
        kwh=round(monthly_bill_pkr / fallback_rate, 1),
        marginal_rate_pkr_per_kwh=fallback_rate,
        protected=protected,
        warnings=warnings,
    )


def marginal_rate(monthly_kwh: float, protected: bool = False) -> float:
    """The per-unit rate that applies to this consumption level — used as
    the default tariff for savings calculations unless the user overrides it."""
    slabs = PROTECTED_SLABS if (protected and monthly_kwh <= 200) else UNPROTECTED_SLABS
    return _slab_rate(monthly_kwh, slabs)
