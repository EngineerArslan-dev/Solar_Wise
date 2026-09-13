# Pakistan Distributed Generation & Net Metering — Regulatory Overview

*Compiled September 2026. Sections marked "primary source" are grounded
directly in the actual NEPRA/AEDB Net Metering Reference Guide, fetched
and verified live at the URL below — not secondary reporting. Tariff
rate figures under "2025-2026 net billing transition" remain sourced
from press coverage (see that section's own note) since the primary
2015 regulation predates that policy shift.*

**Get the actual primary-source document** (confirmed live and working
as of this writing):
`https://www.ppib.gov.pk/Netmetering/NetMeteringReferenceGuideforDISCOs150118-1.pdf`
This is AEDB's official Net Metering Reference Guide for DISCOs,
including the full text of NEPRA's original 2015 regulation (SRO
892(I)/2015) as published in the Gazette of Pakistan. Download it
directly and place it in this folder alongside this summary — it is the
authoritative source this summary is built from.

## Primary source: the 2015 regulation's actual framework

**Scope and definitions**: the regulation (NEPRA's Alternative &
Renewable Energy Distributed Generation and Net Metering Regulations,
2015) covers solar and wind Distributed Generation Facilities up to 1
MW, connected to a DISCO's 3-phase 400V or 11kV service.

**Fast-track threshold at 250 kW**: for connections up to 250 kW, the
regulation and subsequent Ministry of Energy directives waive the
technical feasibility study, the electrical inspector's NOC, and the
formal load-flow study requirement — these apply only above 250 kW
(above 500 kW, load-flow study must specifically use PSSE software;
between 250 kW and 500 kW, FDRANA is acceptable).

**Application timeline** (as specified in the regulation itself, not
just informally targeted): acknowledgment within 5 working days, initial
technical review within 20 working days, agreement execution within 10
working days of a successful review, NEPRA generation license issuance
within 7 working days of DISCO submission, Connection Charge Estimate
issuance within 7 working days of the agreement, and installation within
30 days of payment.

**Agreement term**: 3 years, automatically renewable for further 3-year
terms by mutual agreement.

**Billing mechanism** (primary-source detail): net energy is settled
per billing cycle. If imports exceed exports, the customer is billed at
the applicable tariff for the net kWh. If exports exceed imports, the
surplus credits the next billing cycle — and if a full quarter (3
billing cycles) passes with exports still exceeding imports, the DISCO
must pay out the net surplus at the **off-peak rate specifically**, not
the full applicable tariff. This off-peak-rate detail is easy to miss
and matters for payback calculations under the original 2015 framework.

**Technical/interconnection standards actually cited** (primary
source): grid-connected inverters must comply with UL 1741, and the
regulation additionally references IEEE 1547-2003, IEC 61215 (crystalline
PV modules), IEC 61646 (thin-film PV modules), and IEC 61727 for voltage/
frequency/power-factor/harmonics/islanding trip parameters. For systems
above 10kW, IEC 61000-6 and EN 62109-1/2 apply as additional EMC/safety
requirements. Voltage and frequency variation tolerance is specified as
±5% and ±1% of nominal, respectively.

**Enforcement**: violation of the regulations carries a penalty of up
to Rs 100 million under the underlying Regulation of Generation,
Transmission and Distribution of Electric Power Act, 1997.

## 2025-2026 net billing transition (secondary-source, dates approximate)

Pakistan's framework has since moved away from the 2015 regulation's
one-to-one net-energy-billing model described above, toward a "net
billing" mechanism under new Prosumer Regulations, where surplus export
is credited at a separate, generally lower reference rate than the
retail import tariff. Reported implementation milestones place this
shift in late 2025 through early 2026, though exact dates and rate
figures (variously reported between roughly Rs 11-27/kWh depending on
source and date) have not been independently verified against a primary
document the way the 2015 framework above has been — treat this
section's specifics as directional pending access to the actual
Prosumer Regulations text, which should replace this section once
sourced.

**Transition treatment**: multiple secondary sources indicate consumers
under existing 2015-framework agreements continue under their original
3-year terms, while new applicants fall under the new net-billing
framework — consistent with the primary regulation's own Section 7/8
provisions on agreement terms and termination.

## Why this matters for sizing decisions

The shift from one-to-one net metering to net billing changes the
economic case for **oversizing** an array to maximize export revenue —
self-consumption becomes relatively more valuable than exporting,
compared to the 2015-era regime. This is worth explicitly flagging to
clients: a sizing strategy optimized for old net-metering economics may
not be optimal under the current framework.

## How to extend this folder

- Download the actual PDF from the URL above and place it here —
  strongly recommended, since it's the primary source this summary is
  built from and contains full application forms/schedules not
  reproduced here.
- Source and add the actual current Prosumer Regulations
  notification/SRO text from nepra.org.pk once available, to replace
  the secondary-sourced section above with primary-source grounding.
- Add the specific DISCO's current published net-billing/reference
  rate — region- and time-specific, should not be hardcoded into
  general reference material.
