# Pakistan Solar Irradiance — Published Reference Figures

*This document compiles irradiance figures from published academic and
government sources as example/reference data, so the knowledge base has
real numbers to retrieve even before you run a live data pull. For
authoritative, current, location-precise data, run:*

```bash
python main.py irradiance --city <CityName> --start-year 2018 --end-year 2023
```

*which pulls directly from NASA POWER for the exact coordinates in
`config.PAKISTAN_CITIES`. Treat the figures below as broad,
literature-sourced context — not a substitute for that live pull when
precision matters for a client deliverable.*

## National overview

Pakistan's annual cumulative solar radiation ranges roughly from 6,300
to 7,500 MJ/m² per site, according to comparative measurement studies
across Pakistani meteorological stations, with Quetta recording among
the highest annual totals of the locations studied (NREL's 10km-resolution
solar map of Pakistan; academic measurement/prediction comparison
studies). Monthly global radiation peaks in the May-June period across
essentially all stations studied.

## City-level figures reported in the literature

| City | Reported figure | Source context |
|---|---|---|
| Lahore | Daily radiation ranging roughly 3.6-7.65 kWh/m² across months (1980s multi-year study) | Nasir & Raza, "Wind and solar energy in Pakistan," *Energy*, 1993 |
| Karachi | Daily radiation ranging roughly 3.39-6.31 kWh/m² across months (same study) | Nasir & Raza, 1993 |
| Quetta | Daily radiation ranging roughly 2.4-6.35 kWh/m² across months; highest annual cumulative total among stations in a separate NREL-map-based study | Nasir & Raza, 1993; NREL Pakistan solar map |
| Peshawar | Daily radiation ranging roughly 2.8-6.27 kWh/m² across months | Nasir & Raza, 1993 |
| Islamabad | Approximately 5.89 kWh/m²/day average daily horizontal irradiance reported in a university PV system design study | NUST Islamabad 8.79 MW feasibility study (published PV design paper) |
| Lahore, Bahawalpur, Karachi, Mardan, Chiniot, Faisalabad, Multan, Quetta, Islamabad, Gujrat | Annual irradiance figures ranging roughly 1,806-2,287 kWh/m²/year across these cities | ASTESJ published solar/net-metering study, Table 1 |
| General central/southern Pakistan | Commonly cited working range of ~5-6 kWh/m²/day for Islamabad, Karachi, Quetta, and Lahore | Industry solar-installer reference material |

## Interpreting these figures for sizing

- These are **historical, multi-year averages** from varied study
  periods (some from the 1980s, some more recent) — not a substitute for
  a current-period, location-precise pull.
- The wide monthly range within each city (e.g., Lahore's ~3.6 to ~7.65
  kWh/m²/day) is exactly why conservative sizing methodology uses the
  **worst month**, not the annual average, for autonomy-critical designs.
- Where these older literature figures and a fresh NASA POWER pull
  disagree meaningfully, treat the NASA POWER pull as authoritative for
  actual project sizing — it draws on a more consistent, continuously
  updated satellite-derived dataset (NASA's CERES/GEWEX SRB records, per
  NASA POWER's own methodology documentation) rather than a single
  historical measurement campaign.

## NASA POWER dataset methodology (for context)

NASA POWER's solar parameters are derived from NASA's GEWEX SRB archive
(1984-2000), the CERES SYN1deg archive (2001 to near-real-time), and
NASA's CERES FLASHFlux project for the most recent ~7 days. This gives
a continuously updated, globally consistent basis for comparing
irradiance across any two Pakistani cities on equal footing — one
advantage over stitching together disparate historical studies like
those tabulated above.

## How to extend this document

- After running a live NASA POWER pull for your target cities, paste
  the resulting worst-month PSH figures here as a running log, so future
  queries against this knowledge base can cite your own project history
  alongside the literature baseline.
- Add PVGIS-sourced figures if you cross-check against that dataset as
  well, noting any material divergence for the same coordinates.
