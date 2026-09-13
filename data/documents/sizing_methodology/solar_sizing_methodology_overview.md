# Solar PV System Sizing Methodology — Reference Overview

*Compiled as a starter reference document for the Solar Sizing RAG knowledge
base. This is original summary content written for this project, not a
reproduction of any single textbook or vendor guide. Replace or supplement
with your own sourced methodology papers as needed.*

## 1. Load Assessment (Energy Demand)

The starting point of any sizing exercise is determining daily energy
demand in watt-hours (Wh/day):

- List every load (lighting, appliances, HVAC, electronics, motors).
- For each load: `Daily_Wh = Rated_Power_W × Hours_Used_Per_Day`.
- Sum all loads for total daily demand.
- Apply a design margin of 10-40% (commonly 20-25%) to account for
  estimation error, inefficiencies, and headroom for future load growth.
- For existing buildings, utility bill history (kWh/month) is often more
  reliable than appliance-by-appliance estimation.

## 2. Solar Resource Assessment

- **Peak Sun Hours (PSH)**: the number of hours per day at which solar
  irradiance would need to average 1000 W/m² to deliver the same total
  daily energy as the actual, variable irradiance curve. Numerically
  equal to daily global horizontal irradiance in kWh/m²/day.
- Data sources: NASA POWER, PVGIS, national meteorological services,
  or ground-station pyranometer records where available.
- For autonomous/hybrid systems, size against the **worst month's** PSH,
  not the annual average, for conservative reliability.

## 3. Array Sizing

```
Array_Size_W = Daily_Load_Wh / (PSH × System_Derate_Factor)
```

The derate factor bundles combined system losses: wiring (2-3%),
inverter conversion (4-8%), soiling (2-5%), temperature derating
(10-15% in hot climates), and mismatch losses (~2%). Combined factors
of 0.75-0.85 are typical starting assumptions, refined with local data
where available.

## 4. Inverter Sizing

- Continuous AC rating should cover the largest realistic *simultaneous*
  load, not the sum of all connected loads.
- DC-to-AC ratio (array W ÷ inverter W) commonly falls between 0.9 and
  1.3 depending on design philosophy and clipping tolerance.
- Must tolerate surge/starting current of inductive loads (motors,
  compressors), which can reach 3-7× running wattage briefly.

## 5. Battery Sizing (Off-grid / Hybrid Systems)

```
Battery_Capacity_Ah = (Daily_Load_Wh × Days_Autonomy) / (System_Voltage_V × DoD)
```

- **Days of autonomy**: typically 1-3 days for grid-backup hybrid
  systems, 3-5+ days for remote/true off-grid installations.
- **Depth of Discharge (DoD)**: lithium/LiFePO4 chemistries typically
  tolerate 80-90% DoD; lead-acid/AGM/gel chemistries are usually
  limited to 40-60% to preserve cycle life.

## 6. Charge Controller Sizing

```
Controller_Rating_A = (Array_W / System_Voltage_V) × Safety_Factor
```

A safety factor of ~1.25 is common practice, accounting for brief
irradiance enhancement above STC-rated output (e.g., edge-of-cloud
effects).

## 7. Balance of System

- Conductor sizing to keep voltage drop under ~3% over typical run
  lengths.
- Overcurrent protection sized to relevant local/national electrical
  code requirements.
- Structural mounting rated for local wind/snow/seismic loads.

## Suggested Extensions to This Document

- Add citations to specific national standards you're designing against
  (see the `standard/` category).
- Add worked numeric examples specific to your typical project types
  (residential, commercial rooftop, agricultural pumping, etc.).
- Record any deviations from these defaults that your organization has
  adopted, with the engineering rationale, so the RAG system can surface
  your own house conventions rather than only generic ones.
