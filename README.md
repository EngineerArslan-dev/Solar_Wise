<!--
  Paste this in place of the existing "## Streamlit Web UI (rewired to call
  the real engine)" section in README.md. It replaces only that section —
  everything else in the README (setup, ingestion, CLI usage, etc.) is
  unaffected by the UI redesign.
-->

## Streamlit Web UI

`app.py` is wired directly to `engine/solar_sizing_engine.py` — every
number shown comes from `run_solar_sizing()`, not from logic duplicated
in the UI layer. It collects the full PRD Section 5.1 input set: city,
monthly kWh or bill (with protected-tariff option), roof area, backup
requirement (None/Essential/Full house), system type
(On-grid/Hybrid/Off-grid), optional panel rating, optional budget
ceiling.

**Layout:** a single scrollable page, no sidebar and no tabs. Four
numbered sections run top to bottom — Your Details → Recommendation →
Irradiance Reference → Knowledge Base — so the full input-to-explanation
flow is visible without clicking between views. The visual theme is a
dark, high-contrast "black/neon" design (cyan, magenta, and amber
accents), with native charts: a donut of the panel/inverter/battery
mix, a cost-vs-savings bar chart, and an illustrative seasonal
generation curve (all rendered from the engine's own output — the UI
never invents numbers to plot).

The AI explanation panel uses **Groq** (matching PRD Section 7.1), not
Anthropic.

### Running it locally (simplest)

```
pip install -r requirements.txt
streamlit run app.py
```

This opens the app in your browser at `http://localhost:8501`. There is
no sidebar and no in-app field for the Groq key — set `GROQ_API_KEY` as
an environment variable (`export GROQ_API_KEY=...`) or, when deployed
on Streamlit Community Cloud, under the app's **Settings → Secrets**
panel. A status banner at the top of the page shows whether it's
configured. All engineering numbers (sizing, cost, savings, payback,
charts) work without it — only the "Explain with AI" and "Ask" features
need it.

**New dependency:** the chart library `plotly` was added to
`requirements.txt` for this UI — re-run `pip install -r requirements.txt`
if you're updating an existing environment.
