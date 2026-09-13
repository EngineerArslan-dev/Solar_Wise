"""
app.py
------
Streamlit UI for Solar Wise — wired directly to the tested,
PRD-verified calculation engine (engine/solar_sizing_engine.py). This
version:

  - Collects the exact PRD Section 5.1 input set (consumption or bill,
    city, roof area, backup requirement, system type, optional panel
    rating and budget ceiling).
  - Calls run_solar_sizing() for every number shown — the UI never
    computes anything itself.
  - Uses Groq (generation/groq_pipeline.py) for the AI explanation
    panel, matching the PRD's stated stack (Section 7.1), not Anthropic.
  - Adds a custom visual theme (CSS only — no change to app logic) so
    the dashboard reads as a finished product rather than a default
    Streamlit form, per the PRD's "stylish and attractive" UI goal.

Run locally:
    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import os
import pandas as pd
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

st.set_page_config(page_title="Solar Wise", page_icon="☀️", layout="wide")

# ---------------------------------------------------------------------------
# Theme — sun-warm amber/orange on a deep teal/navy base, applied purely via
# CSS on Streamlit's stable data-testid hooks. No app logic lives here.
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
:root {
    --sw-navy: #0B2E33;
    --sw-navy-light: #123C42;
    --sw-teal: #0F6B63;
    --sw-amber: #F5A623;
    --sw-orange: #FF7A33;
    --sw-cream: #FFF8EE;
    --sw-text: #17282B;
}

.stApp {
    background: linear-gradient(180deg, #FFFDF9 0%, #FFF8EE 100%);
}

/* ---- Hero header ---- */
.sw-hero {
    background: linear-gradient(120deg, var(--sw-navy) 0%, var(--sw-teal) 65%, #178A6E 100%);
    border-radius: 18px;
    padding: 2.1rem 2.4rem;
    margin-bottom: 1.6rem;
    box-shadow: 0 10px 30px rgba(11, 46, 51, 0.25);
    position: relative;
    overflow: hidden;
}
.sw-hero::after {
    content: "";
    position: absolute;
    top: -60px; right: -60px;
    width: 220px; height: 220px;
    background: radial-gradient(circle, rgba(245,166,35,0.45) 0%, rgba(245,166,35,0) 70%);
    border-radius: 50%;
}
.sw-hero h1 {
    color: #FFFFFF;
    font-size: 2.2rem;
    margin-bottom: 0.35rem;
    font-weight: 800;
    letter-spacing: -0.02em;
}
.sw-hero p {
    color: #DFF3EE;
    font-size: 1.02rem;
    max-width: 640px;
    margin-bottom: 0;
}
.sw-hero .sw-badge {
    display: inline-block;
    background: rgba(245, 166, 35, 0.18);
    color: var(--sw-amber);
    border: 1px solid rgba(245, 166, 35, 0.45);
    padding: 0.2rem 0.75rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    margin-bottom: 0.9rem;
}

/* ---- Section cards ---- */
.sw-card {
    background: #FFFFFF;
    border: 1px solid #EFE3CE;
    border-radius: 14px;
    padding: 1.25rem 1.4rem;
    box-shadow: 0 4px 16px rgba(23, 40, 43, 0.05);
    margin-bottom: 1rem;
}
.sw-card h4 {
    margin-top: 0;
    color: var(--sw-navy);
}

/* ---- Tabs ---- */
[data-testid="stTabs"] button[role="tab"] {
    font-weight: 600;
    color: #6b6156;
    padding-top: 0.55rem;
    padding-bottom: 0.55rem;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: var(--sw-navy);
    border-bottom: 3px solid var(--sw-amber);
}

/* ---- Buttons ---- */
[data-testid="stButton"] > button, [data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(90deg, var(--sw-amber) 0%, var(--sw-orange) 100%);
    color: #23150a;
    font-weight: 700;
    border: none;
    border-radius: 10px;
    padding: 0.55rem 1.3rem;
    box-shadow: 0 4px 14px rgba(255, 122, 51, 0.35);
    transition: transform 0.08s ease-in-out;
}
[data-testid="stButton"] > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-1px);
    color: #23150a;
}
[data-testid="stButton"] > button p { color: #23150a; font-weight: 700; }

/* Secondary buttons keep a lighter look */
[data-testid="stButton"] > button[kind="secondary"] {
    background: #FFFFFF;
    color: var(--sw-navy);
    border: 1.5px solid var(--sw-teal);
    box-shadow: none;
}
[data-testid="stButton"] > button[kind="secondary"] p { color: var(--sw-navy); }

/* ---- Metrics ---- */
[data-testid="stMetric"] {
    background: linear-gradient(160deg, #FFFFFF 0%, #FFF6E6 100%);
    border: 1px solid #F1DFB8;
    border-radius: 12px;
    padding: 0.85rem 1rem 0.7rem 1rem;
    box-shadow: 0 3px 10px rgba(245, 166, 35, 0.12);
}
[data-testid="stMetricLabel"] {
    color: #7a6b53;
    font-weight: 600;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
[data-testid="stMetricValue"] {
    color: var(--sw-navy);
    font-weight: 800;
}

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--sw-navy) 0%, #0E3A40 100%);
}
[data-testid="stSidebar"] * {
    color: #EAF6F2 !important;
}
[data-testid="stSidebar"] input {
    color: var(--sw-text) !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.15);
}

/* ---- Disclaimer strip ---- */
.sw-disclaimer {
    background: rgba(245, 166, 35, 0.14);
    border-left: 4px solid var(--sw-amber);
    border-radius: 8px;
    padding: 0.6rem 0.9rem;
    font-size: 0.85rem;
    color: #6b4b16;
}

/* ---- Section subheaders with a small rule ---- */
.sw-subhead {
    color: var(--sw-navy);
    font-weight: 700;
    font-size: 1.15rem;
    border-bottom: 2px solid #F1DFB8;
    padding-bottom: 0.35rem;
    margin-bottom: 0.9rem;
}
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


def subhead(text: str) -> None:
    st.markdown(f'<div class="sw-subhead">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — AI provider key (Groq, per PRD Section 7.1)
# ---------------------------------------------------------------------------
st.sidebar.markdown("### ⚡ AI Explanation (Groq)")
st.sidebar.caption(
    "Only needed for the 'Explain with AI' button and the Knowledge Base "
    "Q&A panel. Leave blank to still see all engineering numbers — they "
    "never depend on this."
)
groq_key_input = st.sidebar.text_input("GROQ_API_KEY", type="password")
if groq_key_input:
    os.environ["GROQ_API_KEY"] = groq_key_input

st.sidebar.divider()
st.sidebar.markdown("### 🇵🇰 About Solar Wise")
st.sidebar.caption(
    "A Pakistan-focused planning assistant: deterministic Python "
    "engineering calculations, a curated RAG knowledge base, and "
    "grounded AI explanation — never an AI guess at your system size."
)
st.sidebar.divider()
st.sidebar.markdown(
    '<span style="font-size:0.82rem; opacity:0.85;">Solar Wise is a planning aid, '
    "not certified engineering advice. It does not replace a site survey "
    "or final electrical sign-off.</span>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="sw-hero">
        <div class="sw-badge">PAKISTAN · SOLAR PLANNING ASSISTANT</div>
        <h1>☀️ Solar Wise</h1>
        <p>Turn your electricity usage into a solar system plan, estimated cost,
        and payback — using deterministic engineering calculations, a curated
        knowledge base, and grounded AI explanation. Not a calculator. Not a
        chatbot. Both, working together.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_details, tab_recommendation, tab_irradiance, tab_kb = st.tabs(
    ["📋  Your Details", "🔆  Recommendation", "🌤️  Irradiance Data", "📚  Knowledge Base"]
)

# ---------------------------------------------------------------------------
# TAB 1 — PRD Section 5.1 input set
# ---------------------------------------------------------------------------
with tab_details:
    subhead("Tell us about your electricity usage and site")

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

    st.markdown(
        '<div class="sw-disclaimer">➡️ Go to <b>Recommendation</b> to calculate your system.</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# TAB 2 — Recommendation (calls the real engine — never computes here)
# ---------------------------------------------------------------------------
with tab_recommendation:
    subhead("Your recommended solar system")

    if "sizing_request" not in st.session_state:
        st.warning("Fill in **Your Details** first.")
    else:
        if st.button("☀️ Calculate My System", type="primary"):
            try:
                result = run_solar_sizing(st.session_state.sizing_request)
                st.session_state.sizing_result = result
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not calculate a recommendation: {exc}")

        if "sizing_result" in st.session_state:
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

            with st.expander("Show calculation assumptions"):
                st.json(r.assumptions)

            st.divider()
            subhead("🤖 Explain with AI")
            st.caption(
                "Generates a RAG-grounded explanation citing the ingested "
                "standards/regulation documents (Knowledge Base tab). Never "
                "recomputes or overrides the numbers above — only explains them."
            )
            if st.button("Explain This Recommendation"):
                if not os.environ.get("GROQ_API_KEY"):
                    st.error("Enter your GROQ_API_KEY in the sidebar first.")
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
# TAB 3 -- Irradiance reference tool (unchanged -- still useful standalone)
# ---------------------------------------------------------------------------
with tab_irradiance:
    subhead("Historical Irradiance Reference")
    st.caption(
        "Standalone reference tool — the Recommendation tab already uses "
        "appropriate PSH values automatically. Use this to inspect the "
        "underlying data or check a different city/year range."
    )

    col_a, col_b, col_c = st.columns(3)
    ref_city = col_a.selectbox("City", list(PAKISTAN_CITIES.keys()), key="ref_city")
    start_year = col_b.number_input("Start year", min_value=1984, max_value=2025, value=2018)
    end_year = col_c.number_input("End year", min_value=1985, max_value=2026, value=2023)

    if st.button("Fetch Irradiance Data (NASA POWER)", type="primary"):
        try:
            with st.spinner(f"Fetching NASA POWER data for {ref_city}..."):
                raw = fetch_city_irradiance(ref_city, start_year=int(start_year), end_year=int(end_year))
                summary = summarize_irradiance(raw)

            months = [m for m in summary if m != "ANN"]
            psh_series = pd.Series({m: summary[m]["psh"] for m in months}, name="PSH (kWh/m2/day)")
            st.line_chart(psh_series)

            worst = get_worst_month_psh(summary)
            st.success(f"Worst-month PSH: **{worst} kWh/m2/day**")
            st.dataframe(pd.DataFrame(summary).T, use_container_width=True)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to fetch irradiance data: {exc}")

    st.divider()
    subhead("Short-term Forecast")
    forecast_days = st.slider("Forecast days", 1, 16, 7)
    if st.button("Fetch Forecast (Open-Meteo)"):
        try:
            with st.spinner(f"Fetching forecast for {ref_city}..."):
                raw_fc = fetch_forecast(ref_city, forecast_days=int(forecast_days))
                forecast_rows = summarize_forecast(raw_fc)
            st.dataframe(pd.DataFrame(forecast_rows), use_container_width=True)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to fetch forecast: {exc}")

# ---------------------------------------------------------------------------
# TAB 4 -- Knowledge base management
# ---------------------------------------------------------------------------
with tab_kb:
    subhead("Knowledge Base")

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
    subhead("Ask a Question")
    question = st.text_input("Question", placeholder="What DoD is appropriate for a lead-acid battery?")
    category_filter = st.selectbox("Restrict to category (optional)", ["(all)"] + DOC_CATEGORIES)

    if st.button("Ask"):
        if not os.environ.get("GROQ_API_KEY"):
            st.error("Enter your GROQ_API_KEY in the sidebar first.")
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
