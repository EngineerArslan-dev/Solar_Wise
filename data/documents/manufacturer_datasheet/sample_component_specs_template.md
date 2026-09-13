# Sample Component Datasheets (Illustrative Template)

*These are generic, illustrative typical-spec examples for testing the
RAG pipeline's retrieval of component-level data — they do NOT represent
any specific real manufacturer's product or proprietary datasheet.
Replace with actual datasheets (PDF) for the components you specify on
real projects; those should be sourced directly from the manufacturer.*

## Sample: 550W Monocrystalline PERC Panel (typical class specification)

| Parameter | Typical Value |
|---|---|
| Rated Power (Pmax) | 550 W |
| Open Circuit Voltage (Voc) | 49.5 V |
| Short Circuit Current (Isc) | 14.0 A |
| Voltage at Pmax (Vmp) | 41.5 V |
| Current at Pmax (Imp) | 13.3 A |
| Module Efficiency | ~21.3% |
| Temperature Coefficient (Pmax) | -0.35%/°C |
| Operating Temperature Range | -40°C to +85°C |
| Dimensions (typical) | 2278 × 1134 × 35 mm |
| Weight (typical) | ~27.5 kg |

## Sample: 5kW Hybrid Inverter (typical class specification)

| Parameter | Typical Value |
|---|---|
| Rated AC Output Power | 5000 W |
| Max PV Input Power | 6500 W (DC:AC ratio ~1.3) |
| Max PV Input Voltage | 500 V |
| MPPT Voltage Range | 90-450 V |
| Number of MPPT Trackers | 2 |
| Battery Voltage Range | 40-60 V (nominal 48V) |
| Max Charge Current | 120 A |
| Surge Capacity | 200% for 10 seconds |
| Communication | RS485 / WiFi monitoring |
| Standards Compliance (typical) | IEC 62109-1/-2, anti-islanding per IEC 62116 |

## Sample: LiFePO4 Battery Module (typical class specification)

| Parameter | Typical Value |
|---|---|
| Nominal Voltage | 51.2 V (16S configuration) |
| Nominal Capacity | 100 Ah (5.12 kWh per module) |
| Recommended DoD | 90% |
| Cycle Life (to 80% capacity) | ~6000 cycles at 90% DoD |
| Charge Temperature Range | 0°C to 50°C |
| Discharge Temperature Range | -20°C to 55°C |
| Communication | CAN/RS485 (BMS) |
| Max Continuous Discharge Current | 100 A |

## How to extend this folder

Replace each sample above with the actual manufacturer datasheet PDF for
components you're specifying, organized as one file per component/model
(e.g., `jinko_tiger_neo_550w.pdf`, `growatt_sph5000_hybrid.pdf`). Keeping
real datasheets here lets the RAG system answer component-specific
questions ("what's the max charge current on the battery I'm speccing
for this project?") with a real citation instead of a generic class-level
assumption like the placeholders above.
