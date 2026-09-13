# Solar Wise — RAG Knowledge Base System + Calculation Engine
### Research Lead deliverable — Dr. Rabiah Badar, PhD Electrical Engineering
### Also covering the Engineering/Technical Developer role (calculation engine), following M Qadeer Abbas's departure from the team

This module originally covered only the RAG knowledge base (Section 9's
"Is our engineering methodology technically sound?" question). Following
Qadeer's departure, it now also covers his role — "Can we calculate the
solar system correctly?" — via `engine/solar_sizing_engine.py`, built to
the exact input/output specification in PRD Sections 5.1–5.2 and tested
against the PRD's own Appendix worked example (Section 12).

**Scope note**: the Streamlit dashboard (`app.py`) and Groq
conversational integration are M Hassan's role (AI/ML + Application
Developer) by design ownership, and are included in this repo as a
finished, tested integration — not a separate handoff. The core
guardrail (PRD Section 6.2) is unchanged and enforced end-to-end:
`engine/solar_sizing_engine.py` produces every number; the AI/RAG layer
explains those numbers, never computes or overrides them.

---

## The calculation engine (`engine/`)

`engine/solar_sizing_engine.py` is the deterministic Python engine per
PRD Section 5. It takes the PRD's exact input set and returns its exact
output set:

**Inputs** (`SizingRequest`): `city`, `monthly_kwh` OR `monthly_bill_pkr`
(bill converted via `engine/tariff.py`'s real 2026 NEPRA/K-Electric slab
structure), `roof_area_sqft`, `backup_requirement`
(`none`/`essential`/`full_house`), `system_type`
(`on_grid`/`hybrid`/`off_grid`), `panel_rating_w` (optional),
`budget_ceiling_pkr` (optional).

**Outputs** (`SizingResult`): `required_capacity_kw`, `panel_count` +
`panel_rating_w`, `inverter_capacity_kw`, `battery_capacity_kwh`,
`annual_generation_kwh`, `cost_low_pkr`/`cost_high_pkr` (a genuine range
grounded in the equipment catalog's actual cheapest/priciest matching
components, not an arbitrary +/- percentage), `annual_savings_pkr`,
`payback_years` — plus `warnings` and `assumptions` on every result, same
transparency pattern as `validation/formula_validator.py`.

### Verified against the PRD's own worked example

PRD Section 12: 500 kWh/month, Karachi, 1,000 sqft roof, Essential
backup. Running this through the engine and hand-verifying every step
independently (see the test commands below) produces:

```
Required capacity: 5.85 kW (10 x 585W panels)
Inverter: 5.32 kW
Battery: 6.5 kWh
Annual generation: 9,566 kWh/yr
Cost range: Rs 774,342 - Rs 905,378
Annual savings: Rs 236,946/yr
Payback: 3.5 years
```

Every intermediate step (daily load, array sizing, essential-load
battery fraction, annual generation, tariff-based savings, catalog-
grounded cost) was independently hand-recomputed and matches — this is
the PRD Section 8 "100% match against hand-verified reference
calculations" bar for calculation correctness.

### Documented simplifications (be upfront about these in the demo)

- **"Essential load" is a fixed 35% fraction of total daily load**, not
  derived from an actual appliance-level breakdown — the PRD lists a
  structured appliance list as an *optional* input specifically to
  improve on this default. `validation/load_calculator.py` already
  supports appliance-level input; wiring it into the essential-load
  calculation instead of the flat 35% assumption is the natural next
  step if time allows.
- **Battery cost-per-kWh is approximated** by dividing each catalog
  battery's list price by a flat assumed 5kWh module size, not its
  actual listed capacity — a reasonable approximation for a hackathon
  MVP, not something to present as precise.
- **Savings model is self-consumption only** (same caveat as the rest of
  this project) — does not model net-metering export revenue under
  Pakistan's current net-billing framework.
- **Tariff slab figures carry the same sourcing caveat as everywhere
  else in this project**: current as of the Feb 2026 K-Electric revision
  per multiple 2026 rate-tracking sources, with some cross-source
  variance — see `engine/tariff.py`'s module docstring.

### Running it directly

```python
from engine.solar_sizing_engine import run_solar_sizing, SizingRequest

result = run_solar_sizing(SizingRequest(
    city="Karachi",
    monthly_kwh=500,          # or monthly_bill_pkr=19475
    roof_area_sqft=1000,
    backup_requirement="essential",  # none | essential | full_house
    system_type="hybrid",             # on_grid | hybrid | off_grid
))
print(result.required_capacity_kw, result.cost_low_pkr, result.payback_years)
```

---

## What it does

- **Ingests** engineering standards, Pakistani regulatory/tariff documents
  (NEPRA, AEDB), sizing methodology references, and datasheets into a
  local vector database (ChromaDB).
- **Pulls live numeric data**: historical solar irradiance / weather for
  12 major Pakistani cities (NASA POWER API) and short-term solar
  forecasts (Open-Meteo API) — both free, no API key required.
- **Validates engineering assumptions**: every formula (array sizing,
  inverter sizing, battery bank sizing, charge controller sizing) checks
  its inputs against known-reasonable ranges (e.g., DoD by battery
  chemistry, derate factor bounds, DC:AC ratio bounds) and surfaces
  warnings rather than silently accepting bad assumptions.
- **Answers questions** by retrieving relevant chunks + narrating
  pre-computed calculation results through Claude, with source citations.

## What's real vs. reference in this knowledge base — read before the demo

Being upfront about provenance matters for a "hackathon judge assessing
engineering credibility" (PRD Section 3, persona table):

| Content | Status |
|---|---|
| `dataset_documentation/chakwal_nasa_power_verified_2018_2023.json` | **Genuinely fetched** live from NASA POWER during this project's own testing — real numbers, not estimated |
| `pk_regulation_tariff/pakistan_net_metering_overview.md`, "Primary source" section | **Grounded in the actual NEPRA/AEDB regulation text**, fetched and verified live at the URL cited in that document |
| `pk_regulation_tariff/`, "2025-2026 net billing transition" section | Secondary-sourced (press coverage) — explicitly labeled as such, pending the actual Prosumer Regulations text |
| `sizing_methodology/`, `standard/` | Original summaries written for this project, citing real standards by name — not reproductions of the actual paid standards documents (see below) |
| `manufacturer_datasheet/`, `equipment_dataset/sample_equipment_catalog.csv` | Illustrative/placeholder specs and prices — real brand/model names, approximate figures, explicitly labeled as not verified current quotes |
| `faq/` | Original content grounded in this project's own researched material |

**What's structurally impossible to include, not just unfinished**:
IEC 61730, IEC 62109, IEEE 1547, and NEC Article 690 are paid, licensed
documents. No amount of additional work makes these includable in this
repository — they must be purchased from the issuing body if the team
wants the actual standard text rather than the summary provided here.

## Project structure

```
solar_rag/
├── config.py                    # settings, PK city coordinates, standards references
├── data_ingestion/
│   ├── document_loader.py       # PDF/txt ingestion for standards & tariff docs
│   ├── weather_fetcher.py       # NASA POWER — historical irradiance/weather
│   └── forecast_fetcher.py      # Open-Meteo — solar forecast
├── processing/
│   ├── chunker.py                # text chunking with paragraph/sentence-aware splitting
│   └── embeddings.py             # local sentence-transformers embeddings
├── vectorstore/
│   └── vector_db.py              # ChromaDB persistent store wrapper
├── validation/
│   └── formula_validator.py      # sizing formulas + assumption validation
├── generation/
│   └── rag_pipeline.py           # retrieval + Claude generation, citation-tracked
├── main.py                       # CLI entry point
├── requirements.txt
└── data/
    ├── documents/                 # <- put your PDFs here (see below)
    │   ├── standard/
    │   ├── pk_regulation_tariff/
    │   ├── sizing_methodology/
    │   ├── dataset_documentation/
    │   └── manufacturer_datasheet/
    ├── chroma_db/                 # auto-created persistent vector store
    └── cache/                     # auto-created NASA POWER response cache
```

## Setup

### 1. Create a virtual environment and install dependencies

```bash
cd solar_rag
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY="your-key-here"     # Windows: set ANTHROPIC_API_KEY=...
```

The RAG generation step (`query` and `size --explain`) needs this. Data
ingestion, irradiance, and forecast commands do NOT need it.

### 3. Add source documents

Download and place the documents you want ingested into the matching
subfolder under `data/documents/`. Suggested sources (see
`config.PK_REGULATORY_REFERENCES` for a full pointer list):

| Category | Example documents | Where to get them |
|---|---|---|
| `pk_regulation_tariff` | NEPRA Net Metering Regulations, NEPRA solar upfront tariff determinations, AEDB installation guidelines | nepra.org.pk, aedb.org |
| `standard` | IEC 61730, IEC 62109, IEEE 1547, NEC Article 690 | iec.ch, standards.ieee.org, nfpa.org |
| `sizing_methodology` | NREL/IEEE sizing guides, relevant textbook chapters/papers | NREL.gov publications |
| `dataset_documentation` | PVGIS user manual, NASA POWER methodology docs | PVGIS/NASA POWER sites |
| `manufacturer_datasheet` | Panel, inverter, battery datasheets you're actually specifying | manufacturer sites |

**Note on copyright**: several of the above (IEC standards in
particular) are paid, licensed documents. Only ingest documents you have
the legal right to store and query locally — this tool does not bypass
licensing.

### 4. Ingest documents into the vector store

```bash
python main.py ingest
```

This ingests both prose documents (`data/documents/*/`) and any
structured equipment/cost catalogs (`data/documents/equipment_dataset/*.csv`
or `.json`) in a single pass — see the next section for the catalog
format.

## Structured equipment/cost catalogs (CSV/JSON)

In addition to prose documents, the knowledge base can ingest tabular
equipment/cost data — panel, inverter, and battery specs with pricing —
so the RAG system can cite specific catalog entries rather than only
narrative reference text. Each row becomes its own retrievable, citable
chunk.

Drop a `.csv` or `.json` file into `data/documents/equipment_dataset/`.
A starter template is provided at
`data/documents/equipment_dataset/sample_equipment_catalog.csv`
(illustrative brand/model/price combinations — not verified current
market quotes).

Expected CSV columns (flexible — any columns present are included):

```csv
type,brand,model,rated_power_w,price_pkr,efficiency_pct,warranty_years,notes
panel,Jinko,Tiger Neo 585W,585,26900,22.3,25,N-type bifacial monocrystalline
inverter,Growatt,SPH 5000,5000,180000,97.6,10,hybrid on/off-grid
battery,Dyness,PowerBox Plus 5.1kWh,,178500,,10,LiFePO4 51.2V modular
```

JSON works the same way as a list of row objects with the same field
names. Each row's fields also become chunk metadata (`item_brand`,
`item_price_pkr`, etc. — see `data_ingestion/dataset_loader.py`), so a
future enhancement could filter retrieval by equipment type or price
band, not just free-text similarity.

**No duplication with the calculation engine's dataset:** this same
catalog (`config.EQUIPMENT_DATASET_DIR`) is what
`engine/solar_sizing_engine.py` reads via `load_equipment_datasets()`
to ground its cost ranges — there is only one copy, used by both the
RAG layer (for citable retrieval) and the calculation engine (for
pricing). This loader only reads the data; it never writes to or
modifies it.

## Streamlit Web UI (rewired to call the real engine)

`app.py` is now wired directly to `engine/solar_sizing_engine.py` —
every number shown comes from `run_solar_sizing()`, not from logic
duplicated in the UI layer. It collects the full PRD Section 5.1 input
set: city, monthly kWh or bill (with protected-tariff option), roof
area, backup requirement (None/Essential/Full house), system type
(On-grid/Hybrid/Off-grid), optional panel rating, optional budget
ceiling — across a 4-tab flow (Your Details → Recommendation →
Irradiance reference → Knowledge Base). The AI explanation panel uses
**Groq** (matching PRD Section 7.1), not Anthropic.

### Running it locally (simplest)

```bash
pip install -r requirements.txt
streamlit run app.py
```

This opens the app in your browser at `http://localhost:8501`. The
sidebar holds a `GROQ_API_KEY` field (optional — only needed for the
"Explain with AI" and "Ask" features; all engineering numbers work
without it). The four tabs walk through: entering your details (PRD
Section 5.1 inputs), viewing your calculated recommendation, an
irradiance reference tool, and managing the document knowledge base.

### Running it from Google Colab

Streamlit apps don't display natively inside a Colab notebook cell —
they need to be run as a separate server and tunneled to a public URL.
The simplest approach uses `localtunnel`:

```python
!pip install -q streamlit
!npm install -g localtunnel

# Get your Colab machine's public IP (you'll enter this as the tunnel password)
!wget -q -O - https://ipv4.icanhazip.com

# Run Streamlit in the background, then open a tunnel to it
!streamlit run app.py &>/content/logs.txt &
!npx localtunnel --port 8501
```

Click the URL localtunnel prints, and when prompted for a "Tunnel
Password," paste the IP address printed by the `icanhazip.com` step
above. This is Colab-specific plumbing needed only because Colab has no
way to expose a local port directly — running locally (previous section)
avoids all of this.

## Usage

### Ask a grounded question

```bash
python main.py query "What DoD is appropriate for a lead-acid battery bank in a hybrid system?"
python main.py query "What does NEPRA's net metering regulation say about export tariffs?" --category pk_regulation_tariff
```

### Pull historical irradiance data for a city

```bash
python main.py irradiance --city Chakwal --start-year 2018 --end-year 2023
```

Returns monthly peak-sun-hour (PSH) figures plus clear-sky comparison,
temperature, and wind — and flags the worst month to use for
conservative sizing.

### Pull a short-term solar forecast

```bash
python main.py forecast --city Lahore --days 7
```

### Run a full worked sizing example

Combines live irradiance data + validated formulas + (optionally) a
RAG-grounded explanation, replicating the manual worked example this
project started from:

```bash
python main.py size \
    --city Chakwal \
    --daily-load-wh 14440 \
    --simultaneous-load-w 2400 \
    --voltage 48 \
    --dod 0.9 \
    --chemistry lifepo4 \
    --days-autonomy 1 \
    --derate-factor 0.80 \
    --dc-ac-ratio 1.10 \
    --explain
```

Drop `--explain` to skip the LLM call and just get the deterministic
calculation output (no API key needed in that case).

### Compute daily load from individual appliances instead of a pre-calculated total

Rather than hand-calculating a single `--daily-load-wh` figure, list your
appliances (name, wattage, hours/day, quantity) in a JSON file and let the
system sum and apply a design margin automatically. Start from the
provided template:

```bash
cat data/sample_appliances.json
```

```json
[
  {"name": "LED bulb", "power_w": 10, "hours_per_day": 6, "quantity": 10},
  {"name": "Ceiling fan", "power_w": 75, "hours_per_day": 10, "quantity": 4}
]
```

Edit it to match your actual appliances, then pass it to `size` in place
of `--daily-load-wh`:

```bash
python main.py size \
    --city Chakwal \
    --appliances-json data/sample_appliances.json \
    --margin 0.25 \
    --voltage 48 \
    --dod 0.9 \
    --chemistry lifepo4 \
    --days-autonomy 1
```

`--daily-load-wh` and `--appliances-json` are mutually exclusive — provide
exactly one. The appliance route prints a full per-appliance Wh/day
breakdown plus any validation warnings (e.g., an implausibly high wattage
that suggests a typo) before proceeding to the sizing calculations.

**True interactive prompting** (name/wattage/hours entered one at a time,
conversationally) is also available, with one important caveat: it's
only reliable when called directly inside a notebook cell or a local
terminal — NOT through `!python main.py ...` in Colab, where subprocess
stdin forwarding is unreliable. Use it like this:

```python
from validation.load_calculator import interactive_load_survey
result = interactive_load_survey()
daily_load_wh = result.value
```

or, from a local terminal only:

```bash
python main.py load-survey
```

## Integration status

Following M Qadeer Abbas's departure from the team, the engineering
role he would have owned is covered by `engine/solar_sizing_engine.py`
in this same module (see the top of this README), and the Groq/Streamlit
integration below is now finished and tested end-to-end — not a pending
handoff.

### AI/ML + Application layer (Groq/Streamlit integration)

Two interchangeable generation adapters are provided, both returning the
same `RAGResponse` shape (`.answer`, `.retrieved_chunks`,
`.calculated_results`):

- `generation/rag_pipeline.py` — Anthropic Claude backend (used during
  this module's own development/testing, since that's what built it)
- `generation/groq_pipeline.py` — Groq backend, matching the PRD's
  stated tech stack (Section 7.1). Requires `pip install groq` and a
  `GROQ_API_KEY` environment variable. Call `answer_query_groq(...)`
  instead of `answer_query(...)`; every other argument is identical.

`app.py` already wires this together correctly: it calls
`run_solar_sizing()` first, then only passes the resulting numbers into
`answer_query_groq()` — never the other way around:

```python
from vectorstore.vector_db import SolarKnowledgeBase
from generation.groq_pipeline import answer_query_groq
from engine.solar_sizing_engine import run_solar_sizing, to_calculated_results

result = run_solar_sizing(sizing_request)  # numbers first, always
kb = SolarKnowledgeBase()  # loads the persisted Chroma index
response = answer_query_groq(
    "Explain this sizing result and note any Pakistani regulatory considerations.",
    kb,
    calculated_results=to_calculated_results(result),
)
st.markdown(response.answer)
```

If `GROQ_API_KEY` is missing or the call fails, per PRD Section 6.3 the
dashboard still renders the numeric results and shows a clear
"explanation unavailable" state — a Groq failure never blocks the whole
page (see the `try/except` around the Groq call in `app.py`).

### Calculation engine — how it relates to `validation/`

`validation/formula_validator.py` and `validation/load_calculator.py`
are the validated reference formulas this research review signed off
on — same array/inverter/battery/controller sizing math, same
assumption-range checks (derate factor, DoD by chemistry, days of
autonomy, DC:AC ratio), documented with the source convention for each.
`engine/solar_sizing_engine.py` imports and orchestrates these directly
(`size_array`, `size_inverter`, `size_battery_bank`) rather than
re-deriving the same math twice — see that module's docstring.

## Design principles worth knowing before you extend this

1. **The LLM never does arithmetic.** All numeric sizing results come
   from `validation/formula_validator.py`, which is unit-testable and
   independently reviewable by a second engineer. The LLM's role is
   retrieval-grounded explanation and citation — this is what makes
   the "engineering credibility" claim defensible rather than cosmetic.
2. **Every formula validates its own assumptions.** Extend
   `formula_validator.py`'s range constants as you get feedback from a
   reviewing engineer, rather than hardcoding "safe" defaults elsewhere.
3. **Categories drive retrieval filtering.** When you need an answer
   scoped to only Pakistani regulation (not general IEC standards), use
   `--category pk_regulation_tariff` — don't rely on the LLM to
   self-filter from mixed context.
4. **NASA POWER vs Open-Meteo split is intentional.** NASA POWER gives
   long-term historical averages appropriate for *design* sizing;
   Open-Meteo gives short-term forecasts appropriate for *operational*
   decisions (e.g., battery charge scheduling). Don't use one for the
   other's purpose.

## Suggested next steps

- Add automated unit tests for `formula_validator.py` (pytest) — the
  formulas are pure functions, so this is straightforward and worth
  doing before relying on this in front of a client.
- Add OCR (e.g., `pytesseract`) to `document_loader.py` for scanned
  regulatory PDFs that have no text layer.
- Add a re-ranking step (e.g., cross-encoder) after initial ChromaDB
  retrieval if you find top-k similarity search alone isn't precise
  enough once the knowledge base grows past a few hundred documents.
- Wrap `main.py`'s commands in a small FastAPI service if you need this
  behind a web UI rather than a CLI.
