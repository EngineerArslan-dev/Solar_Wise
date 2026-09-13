"""
app.py
------
Streamlit UI for Solar Wise — wired directly to the tested,
PRD-verified calculation engine (engine/solar_sizing_engine.py).

This version (redesign):
- Single scrollable landing page — no sidebar, no tabs. Details,
  Recommendation, Irradiance reference, and Knowledge Base are all
  sections on the same page, in that order.
- Dark / vibrant "neon on black" visual theme (CSS only — no change
  to app logic or the calculation engine).
- Adds real charts: a donut of the system mix (panels / inverter /
  battery), a cost-vs-savings bar chart, a payback-timeline chart,
  and an estimated seasonal monthly-generation curve derived from the
  engine's annual_generation_kwh figure.
- Calls run_solar_sizing() for every number shown — the UI never
  computes engineering numbers itself. Chart data is either the
  engine's own numbers or (clearly labeled) a seasonal illustrative
  split of the engine's annual total; it is never a substitute for
  the engine's figures.
- Uses Groq (generation/groq_pipeline.py) for the AI explanation
  panel, matching the PRD's stated stack (Section 7.1), not Anthropic.

Run locally:
    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import os
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import PAKISTAN_CITIES, DOC_CATEGORIES
from data_ingestion.document_loader import load_documents
from data_ingestion.dataset_loader import load_equipment_datasets
from data_ingestion.weather_fetcher import (
    fetch_city_irradiance, summarize_irradiance, get_worst_month_psh
)
from data_ingestion.forecast_fetcher import fetch_forecast, summarize_forecast
from processing.chunker import chunk_documents
from vectorstore.vector_db import SolarKnowledgeBase
from engine.solar_sizing_engine import run_solar_sizing, SizingRequest, to_calculated_results

st.set_page_config(page_title="Solar Wise", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------------------
# Theme — near-black base with neon cyan / magenta / amber accents.
# No sidebar is used anywhere in this app, so no sidebar CSS is needed.
# ---------------------------------------------------------------------------
NEON_CYAN = "#00E5FF"
NEON_MAGENTA = "#FF2E9A"
NEON_AMBER = "#FFC93C"
NEON_PURPLE = "#8B5CF6"
BG_BLACK = "#05050A"
CARD_BG = "#101018"

CUSTOM_CSS = f"""
<style>
:root {{
    --sw-cyan: {NEON_CYAN};
    --sw-magenta: {NEON_MAGENTA};
    --sw-amber: {NEON_AMBER};
    --sw-purple: {NEON_PURPLE};
    --sw-bg: {BG_BLACK};
    --sw-card: {CARD_BG};
}}

/* Kill the sidebar entirely */
[data-testid="stSidebar"], [data-testid="collapsedControl"] {{
    display: none !important;
}}

.stApp {{
    background: radial-gradient(circle at 10% 0%, #10061f 0%, #05050A 45%, #05050A 100%);
    color: #EDEDF5;
}}

section.main > div {{
    padding-top: 1.2rem;
}}

/* ---- Hero header ---- */
.sw-hero {{
    background: linear-gradient(120deg, #1a0b2e 0%, #2d0f3f 45%, #14031f 100%);
    border: 1px solid rgba(0, 229, 255, 0.25);
    border-radius: 20px;
    padding: 2.4rem 2.6rem;
    margin-bottom: 1.8rem;
    box-shadow: 0 0 40px rgba(139, 92, 246, 0.25), inset 0 0 60px rgba(0,229,255,0.04);
    position: relative;
    overflow: hidden;
}}
.sw-hero::after {{
    content: "";
    position: absolute;
    top: -80px; right: -80px;
    width: 260px; height: 260px;
    background: radial-gradient(circle, rgba(255,201,60,0.35) 0%, rgba(255,201,60,0) 70%);
    border-radius: 50%;
}}
.sw-hero::before {{
    content: "";
    position: absolute;
    bottom: -100px; left: -60px;
    width: 260px; height: 260px;
    background: radial-gradient(circle, rgba(255,46,154,0.28) 0%, rgba(255,46,154,0) 70%);
    border-radius: 50%;
}}
.sw-hero h1 {{
    color: #FFFFFF;
    font-size: 2.4rem;
    margin-bottom: 0.4rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, var(--sw-cyan), var(--sw-amber) 60%, var(--sw-magenta));
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.sw-hero p {{
    color: #C9C6DA;
    font-size: 1.02rem;
    max-width: 680px;
    margin-bottom: 0;
}}
.sw-hero .sw-badge {{
    display: inline-block;
    background: rgba(0, 229, 255, 0.10);
    color: var(--sw-cyan);
    border: 1px solid rgba(0, 229, 255, 0.45);
    padding: 0.25rem 0.85rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    margin-bottom: 1rem;
}}

/* ---- Section headers ---- */
.sw-subhead {{
    color: #FFFFFF;
    font-weight: 800;
    font-size: 1.35rem;
    padding-bottom: 0.5rem;
    margin: 2rem 0 1rem 0;
    border-bottom: 2px solid transparent;
    border-image: linear-gradient(90deg, var(--sw-cyan), var(--sw-magenta)) 1;
}}
.sw-subhead .sw-step {{
    color: var(--sw-amber);
    margin-right: 0.5rem;
}}
.sw-section-caption {{
    color: #9C98B5;
    font-size: 0.9rem;
    margin-top: -0.6rem;
    margin-bottom: 1rem;
}}

/* ---- Cards ---- */
.sw-card {{
    background: var(--sw-card);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.3rem 1.5rem;
    box-shadow: 0 8px 24px rgba(0,0,0,0.45);
    margin-bottom: 1.2rem;
}}
.sw-card h4 {{
    margin-top: 0;
    color: var(--sw-cyan);
}}

/* ---- Inputs ---- */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-baseweb="input"] {{
    background-color: #191926 !important;
    color: #F2F2FA !important;
    border: 1px solid rgba(0,229,255,0.25) !important;
    border-radius: 10px !important;
}}
label, .stMarkdown p, .stCaption, [data-testid="stWidgetLabel"] p {{
    color: #D8D6E8 !important;
}}
[data-testid="stRadio"] label {{
    color: #EDEDF5 !important;
}}

/* ---- Buttons ---- */
[data-testid="stButton"] > button, [data-testid="stFormSubmitButton"] > button {{
    background: linear-gradient(90deg, var(--sw-magenta) 0%, var(--sw-amber) 100%);
    color: #14031f;
    font-weight: 800;
    border: none;
    border-radius: 10px;
    padding: 0.6rem 1.4rem;
    box-shadow: 0 4px 20px rgba(255, 46, 154, 0.35);
    transition: transform 0.08s ease-in-out;
}}
[data-testid="stButton"] > button:hover, [data-testid="stFormSubmitButton"] > button:hover {{
    transform: translateY(-2px);
    color: #14031f;
}}
[data-testid="stButton"] > button p {{ color: #14031f; font-weight: 800; }}

/* ---- Metrics ---- */
[data-testid="stMetric"] {{
    background: linear-gradient(160deg, #14101f 0%, #1c1330 100%);
    border: 1px solid rgba(139, 92, 246, 0.35);
    border-radius: 14px;
    padding: 0.9rem 1rem 0.75rem 1rem;
    box-shadow: 0 0 18px rgba(139, 92, 246, 0.18);
}}
[data-testid="stMetricLabel"] {{
    color: #B9B4D6;
    font-weight: 700;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
[data-testid="stMetricValue"] {{
    color: var(--sw-cyan);
    font-weight: 800;
}}

/* ---- Disclaimer strip ---- */
.sw-disclaimer {{
    background: rgba(255, 201, 60, 0.08);
    border-left: 4px solid var(--sw-amber);
    border-radius: 8px;
    padding: 0.7rem 1rem;
    font-size: 0.88rem;
    color: #F0DFA8;
}}

hr {{
    border-color: rgba(255,255,255,0.08) !important;
}}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "kb" not in st.session_state:
    st.session_state.kb = None  # lazily initialized — loading Chroma has real startup cost


def get_kb() -> SolarKnowledgeBase:
    if st.session_state.kb is None:
        with st.spinner("Loading knowledge base..."):
            st.session_state.kb = SolarKnowledgeBase()
    return st.session_state.kb


def subhead(step: str, text: str) -> None:
    st.markdown(
        f'<div class="sw-subhead"><span class="sw-step">{step}</span>{text}</div>',
        unsafe_allow_html=True,
    )


def _resolve_groq_key() -> str:
    """
    Resolve GROQ_API_KEY from Streamlit secrets (st.secrets — the
    intended source when deployed on Streamlit Community Cloud, set via
    the app's Settings > Secrets panel) or a plain environment variable
    (local runs, e.g. `export GROQ_API_KEY=...` or a .env file loaded
    before launch). Never collected via a UI text field — the key must
    live in one of these two places, not typed into the app.
    """
    key = os.environ.get("GROQ_API_KEY", "")
    if key:
        return key
    try:
        key = st.secrets.get("GROQ_API_KEY", "")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001 — no secrets.toml present locally is expected
        key = ""
    if key:
        os.environ["GROQ_API_KEY"] = key  # so generation/groq_pipeline.py picks it up unchanged
    return key


GROQ_KEY_CONFIGURED = bool(_resolve_groq_key())

# Neon plotly template used by every chart on the page
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#EDEDF5", family="sans-serif"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="sw-hero">
        <div class="sw-badge">PAKISTAN · SOLAR PLANNING ASSISTANT</div>
        <h1>⚡ Solar Wise</h1>
        <p>Turn your electricity usage into a solar system plan, estimated cost,
        and payback — using deterministic engineering calculations, a curated
        knowledge base, and grounded AI explanation, all on one page.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not GROQ_KEY_CONFIGURED:
    st.markdown(
        '<div class="sw-disclaimer">⚠️ Groq AI explanation is not configured for this '
        "deployment. All engineering numbers below still work — only the 'Explain with "
        "AI' and 'Ask' features need a <code>GROQ_API_KEY</code> environment variable "
        "or Streamlit secret.</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# SECTION 1 — PRD Section 5.1 input set
# ---------------------------------------------------------------------------
subhead("1", "Tell us about your electricity usage and site")

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="sw-card">', unsafe_allow_html=True)
    st.markdown("**📍 Location & usage**")
    city = st.selectbox(
        "City", list(PAKISTAN_CITIES.keys()),
        index=list(PAKISTAN_CITIES.keys()).index("Karachi"),
    )
    input_mode = st.radio(
        "How do you know your usage?",
        ["Monthly units (kWh)", "Monthly bill (PKR)"],
        horizontal=True,
    )
    if input_mode == "Monthly units (kWh)":
        monthly_kwh = st.number_input("Monthly consumption (kWh)", min_value=1.0, value=500.0)
        monthly_bill_pkr = None
    else:
        monthly_bill_pkr = st.number_input("Monthly bill (PKR)", min_value=1.0, value=19475.0)
        monthly_kwh = None
    protected_tariff = st.checkbox(
        "I'm on the 'protected' tariff (consistently under 200 units/month)",
        value=False,
    )
    roof_area_sqft = st.number_input(
        "Rooftop area available (sq ft)", min_value=0.0, value=1000.0,
        help="Used to check the recommended array physically fits your roof.",
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="sw-card">', unsafe_allow_html=True)
    st.markdown("**🔋 System preferences**")
    backup_label_to_value = {
        "None (grid-tied savings only)": "none",
        "Essential loads (lights, fans, fridge, router)": "essential",
        "Full house": "full_house",
    }
    backup_label = st.selectbox("Backup requirement", list(backup_label_to_value.keys()), index=1)
    backup_requirement = backup_label_to_value[backup_label]

    system_label_to_value = {
        "On-grid (no battery, grid-tied only)": "on_grid",
        "Hybrid (grid-tied + battery backup)": "hybrid",
        "Off-grid (battery-only, no grid)": "off_grid",
    }
    system_label = st.selectbox("System type", list(system_label_to_value.keys()), index=1)
    system_type = system_label_to_value[system_label]

    panel_rating_input = st.selectbox(
        "Preferred panel rating (W)", ["Default (most common)", 550, 585, 590],
    )
    panel_rating_w = None if panel_rating_input == "Default (most common)" else float(panel_rating_input)

    has_budget = st.checkbox("I have a fixed budget ceiling")
    budget_ceiling_pkr = (
        st.number_input("Budget ceiling (PKR)", min_value=1.0, value=500000.0)
        if has_budget else None
    )
    st.markdown('</div>', unsafe_allow_html=True)

if system_type == "on_grid" and backup_requirement != "none":
    st.warning(
        "On-grid systems provide no outage backup. If backup during "
        "load-shedding matters to you, choose Hybrid or Off-grid instead."
    )

st.session_state.sizing_request = SizingRequest(
    city=city,
    monthly_kwh=monthly_kwh,
    monthly_bill_pkr=monthly_bill_pkr,
    protected_tariff=protected_tariff,
    roof_area_sqft=roof_area_sqft if roof_area_sqft > 0 else None,
    backup_requirement=backup_requirement,
    system_type=system_type,
    panel_rating_w=panel_rating_w,
    budget_ceiling_pkr=budget_ceiling_pkr,
)

calc_clicked = st.button("☀️ Calculate My System", type="primary")

# ---------------------------------------------------------------------------
# SECTION 2 — Recommendation (calls the real engine — never computes here)
# ---------------------------------------------------------------------------
subhead("2", "Your recommended solar system")

if calc_clicked:
    try:
        st.session_state.sizing_result = run_solar_sizing(st.session_state.sizing_request)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not calculate a recommendation: {exc}")

if "sizing_result" not in st.session_state:
    st.info("Fill in your details above and click **Calculate My System**.")
else:
    r = st.session_state.sizing_result

    if r.budget_constrained:
        st.warning(
            "Your budget ceiling is below the full recommendation's cost — "
            "the system below has been scaled down to fit, and will not "
            "fully offset your target load."
        )

    cols = st.columns(4)
    cols[0].metric("Required capacity", f"{r.required_capacity_kw} kW")
    cols[1].metric("Panels", f"{r.panel_count} x {r.panel_rating_w:.0f}W")
    cols[2].metric("Inverter", f"{r.inverter_capacity_kw} kW")
    cols[3].metric("Battery", f"{r.battery_capacity_kwh} kWh" if r.battery_capacity_kwh else "None")

    cols2 = st.columns(4)
    cols2[0].metric("Annual generation", f"{r.annual_generation_kwh:,.0f} kWh/yr")
    cols2[1].metric("Est. cost", f"Rs {r.cost_low_pkr:,.0f}-{r.cost_high_pkr:,.0f}")
    cols2[2].metric("Annual savings", f"Rs {r.annual_savings_pkr:,.0f}")
    cols2[3].metric(
        "Payback",
        f"{r.payback_years} yrs" if r.payback_years != float("inf") else "-",
    )

    for w in r.warnings:
        st.warning(w)

    # ---- Charts -------------------------------------------------------
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown('<div class="sw-card">', unsafe_allow_html=True)
        st.markdown("**System mix**")
        battery_kwh = r.battery_capacity_kwh or 0
        donut = go.Figure(
            data=[go.Pie(
                labels=["Panel array (kW)", "Inverter (kW)", "Battery (kWh)"],
                values=[r.required_capacity_kw, r.inverter_capacity_kw, battery_kwh],
                hole=0.55,
                marker=dict(colors=[NEON_CYAN, NEON_MAGENTA, NEON_AMBER]),
                textfont=dict(color="#05050A", size=13),
            )]
        )
        donut.update_layout(**PLOTLY_LAYOUT, showlegend=True, height=320)
        st.plotly_chart(donut, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with chart_col2:
        st.markdown('<div class="sw-card">', unsafe_allow_html=True)
        st.markdown("**Cost vs. annual savings**")
        bars = go.Figure(
            data=[
                go.Bar(
                    x=["Low cost", "High cost", "Annual savings"],
                    y=[r.cost_low_pkr, r.cost_high_pkr, r.annual_savings_pkr],
                    marker=dict(color=[NEON_PURPLE, NEON_MAGENTA, NEON_CYAN]),
                    text=[f"Rs {v:,.0f}" for v in [r.cost_low_pkr, r.cost_high_pkr, r.annual_savings_pkr]],
                    textposition="outside",
                )
            ]
        )
        bars.update_layout(**PLOTLY_LAYOUT, height=320, yaxis=dict(gridcolor="rgba(255,255,255,0.08)"))
        st.plotly_chart(bars, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sw-card">', unsafe_allow_html=True)
    st.markdown("**Estimated seasonal generation** (illustrative monthly split of the engine's annual total — Pakistan's solar output peaks in summer, dips in winter)")
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    # Simple seasonal weighting (summer-peaked) normalized to sum to 1.0
    raw_weights = [0.070, 0.075, 0.088, 0.095, 0.100, 0.098, 0.090, 0.088, 0.086, 0.080, 0.070, 0.060]
    weight_sum = sum(raw_weights)
    monthly_kwh_est = [r.annual_generation_kwh * (w / weight_sum) for w in raw_weights]
    seasonal = go.Figure(
        data=[go.Scatter(
            x=months, y=monthly_kwh_est, mode="lines+markers", fill="tozeroy",
            line=dict(color=NEON_CYAN, width=3),
            fillcolor="rgba(0,229,255,0.15)",
            marker=dict(color=NEON_AMBER, size=7),
        )]
    )
    seasonal.update_layout(
        **PLOTLY_LAYOUT, height=300,
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(title="kWh/month", gridcolor="rgba(255,255,255,0.08)"),
    )
    st.plotly_chart(seasonal, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Show calculation assumptions"):
        st.json(r.assumptions)

    st.divider()
    st.markdown("**🤖 Explain with AI**")
    st.caption(
        "Generates a RAG-grounded explanation citing the ingested "
        "standards/regulation documents (Knowledge Base section below). "
        "Never recomputes or overrides the numbers above — only explains them."
    )
    if st.button("Explain This Recommendation"):
        if not GROQ_KEY_CONFIGURED:
            st.error(
                "AI explanation isn't configured for this deployment. "
                "Set GROQ_API_KEY in Streamlit Cloud Secrets to enable it."
            )
        else:
            from generation.groq_pipeline import answer_query_groq
            kb = get_kb()
            query = (
                f"Explain and justify this solar sizing recommendation for "
                f"{r.assumptions.get('monthly_kwh', '?')} kWh/month in "
                f"{st.session_state.sizing_request.city}, Pakistan, citing "
                f"relevant standards and any Pakistani regulatory "
                f"considerations (e.g., net metering) that apply."
            )
            with st.spinner("Generating explanation..."):
                try:
                    response = answer_query_groq(
                        query, kb, calculated_results=to_calculated_results(r)
                    )
                    st.markdown(response.answer)
                    with st.expander(f"Sources ({len(response.retrieved_chunks)} chunks retrieved)"):
                        for c in response.retrieved_chunks:
                            st.write(f"- **{c['title']}** [{c['category']}] (distance={c['distance']:.3f})")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Generation failed: {exc}")
                    st.info(
                        "The engineering numbers above are unaffected -- "
                        "only the AI explanation failed to generate."
                    )

# ---------------------------------------------------------------------------
# SECTION 3 — Irradiance reference tool
# ---------------------------------------------------------------------------
subhead("3", "Historical irradiance reference")
st.markdown(
    '<div class="sw-section-caption">Standalone reference tool — the recommendation '
    "above already uses appropriate solar-hour values automatically. Use this to "
    "inspect the underlying data or check a different city/year range.</div>",
    unsafe_allow_html=True,
)

st.markdown('<div class="sw-card">', unsafe_allow_html=True)
col_a, col_b, col_c = st.columns(3)
ref_city = col_a.selectbox("City", list(PAKISTAN_CITIES.keys()), key="ref_city")
start_year = col_b.number_input("Start year", min_value=1984, max_value=2025, value=2018)
end_year = col_c.number_input("End year", min_value=1985, max_value=2026, value=2023)

if st.button("Fetch Irradiance Data (NASA POWER)", type="primary"):
    try:
        with st.spinner(f"Fetching NASA POWER data for {ref_city}..."):
            raw = fetch_city_irradiance(ref_city, start_year=int(start_year), end_year=int(end_year))
            summary = summarize_irradiance(raw)
        months_keys = [m for m in summary if m != "ANN"]
        psh_values = [summary[m]["psh"] for m in months_keys]
        psh_fig = go.Figure(
            data=[go.Bar(
                x=months_keys, y=psh_values,
                marker=dict(color=NEON_AMBER),
            )]
        )
        psh_fig.update_layout(
            **PLOTLY_LAYOUT, height=300,
            yaxis=dict(title="PSH (kWh/m²/day)", gridcolor="rgba(255,255,255,0.08)"),
        )
        st.plotly_chart(psh_fig, use_container_width=True)
        worst = get_worst_month_psh(summary)
        st.success(f"Worst-month PSH: **{worst} kWh/m2/day**")
        st.dataframe(pd.DataFrame(summary).T, use_container_width=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to fetch irradiance data: {exc}")

st.divider()
st.markdown("**Short-term forecast**")
forecast_days = st.slider("Forecast days", 1, 16, 7)
if st.button("Fetch Forecast (Open-Meteo)"):
    try:
        with st.spinner(f"Fetching forecast for {ref_city}..."):
            raw_fc = fetch_forecast(ref_city, forecast_days=int(forecast_days))
            forecast_rows = summarize_forecast(raw_fc)
        st.dataframe(pd.DataFrame(forecast_rows), use_container_width=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to fetch forecast: {exc}")
st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SECTION 4 — Knowledge base management
# ---------------------------------------------------------------------------
subhead("4", "Knowledge base")

st.markdown('<div class="sw-card">', unsafe_allow_html=True)
kb = get_kb()
st.metric("Chunks currently indexed", kb.count())

if st.button("Re-ingest documents + equipment dataset", type="primary"):
    with st.spinner("Loading and chunking..."):
        docs = load_documents()
        rows = load_equipment_datasets()
        chunks = chunk_documents(docs + rows)
    if not docs and not rows:
        st.warning("No documents or equipment data found in data/documents/.")
    else:
        with st.spinner(f"Indexing {len(chunks)} chunks..."):
            added = kb.add_chunks(chunks)
        st.success(
            f"Indexed {added} chunks from {len(docs)} documents + "
            f"{len(rows)} equipment catalog rows."
        )
        st.rerun()

st.divider()
st.markdown("**Ask a question**")
question = st.text_input("Question", placeholder="What DoD is appropriate for a lead-acid battery?")
category_filter = st.selectbox("Restrict to category (optional)", ["(all)"] + DOC_CATEGORIES)

if st.button("Ask"):
    if not GROQ_KEY_CONFIGURED:
        st.error(
            "AI explanation isn't configured for this deployment. "
            "Set GROQ_API_KEY in Streamlit Cloud Secrets to enable it."
        )
    elif not question.strip():
        st.error("Enter a question first.")
    else:
        from generation.groq_pipeline import answer_query_groq
        cat = None if category_filter == "(all)" else category_filter
        with st.spinner("Retrieving and generating..."):
            try:
                response = answer_query_groq(question, kb, category_filter=cat)
                st.markdown(response.answer)
                with st.expander(f"Sources ({len(response.retrieved_chunks)} chunks retrieved)"):
                    for c in response.retrieved_chunks:
                        st.write(f"- **{c['title']}** [{c['category']}] (distance={c['distance']:.3f})")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Query failed: {exc}")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    '<p style="text-align:center; color:#6b6680; font-size:0.82rem; margin-top:2rem;">'
    "Solar Wise is a planning aid, not certified engineering advice. It does not "
    "replace a site survey or final electrical sign-off.</p>",
    unsafe_allow_html=True,
)
