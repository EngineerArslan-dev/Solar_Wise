"""
main.py
-------
CLI entry point for the Solar Sizing RAG system.

Usage:
    # 1. Ingest all documents in data/documents/ into the vector store
    python main.py ingest

    # 2. Ask a free-text question grounded in the knowledge base
    python main.py query "What DoD should I use for a lead-acid battery bank?"

    # 3. Run a full worked sizing example for a Pakistani city, combining
    #    live NASA POWER irradiance data + validated formulas + RAG explanation
    python main.py size --city Chakwal --daily-load-wh 14440 --voltage 48 \\
        --dod 0.9 --chemistry lifepo4 --days-autonomy 1

    # 3b. Same, but computing daily load from individual appliances instead
    #     of a pre-calculated total (edit data/sample_appliances.json first)
    python main.py size --city Chakwal --appliances-json data/sample_appliances.json \\
        --voltage 48 --dod 0.9 --chemistry lifepo4 --days-autonomy 1

    # 4. Just pull irradiance data for a city (no LLM call)
    python main.py irradiance --city Lahore

    # 5. Just pull a short-term forecast for a city (no LLM call)
    python main.py forecast --city Karachi --days 5

    # 6. Interactively build a load list from a terminal (local terminal only —
    #    see validation/load_calculator.py docstring for the Colab-reliable
    #    alternative of calling interactive_load_survey() directly in a cell)
    python main.py load-survey
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from config import PAKISTAN_CITIES
from data_ingestion.document_loader import load_documents
from data_ingestion.dataset_loader import load_equipment_datasets
from data_ingestion.weather_fetcher import (
    fetch_city_irradiance, summarize_irradiance, get_worst_month_psh
)
from data_ingestion.forecast_fetcher import fetch_forecast, summarize_forecast
from processing.chunker import chunk_documents
from vectorstore.vector_db import SolarKnowledgeBase
from validation.formula_validator import (
    size_array, size_inverter, size_battery_bank, size_charge_controller,
    apply_design_margin,
)
from validation.load_calculator import (
    load_appliances_from_json, calculate_daily_load, interactive_load_survey
)
from generation.rag_pipeline import answer_query

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main")


def cmd_ingest(args: argparse.Namespace) -> None:
    docs = load_documents()
    dataset_rows = load_equipment_datasets()
    all_docs = docs + dataset_rows

    if not all_docs:
        print("No documents or equipment datasets found. Add files to data/documents/ first.")
        return

    chunks = chunk_documents(all_docs)
    print(f"Loaded {len(docs)} documents + {len(dataset_rows)} equipment catalog rows "
          f"-> {len(chunks)} chunks.")

    kb = SolarKnowledgeBase()
    added = kb.add_chunks(chunks)
    print(f"Indexed {added} chunks into the vector store. "
          f"Total in collection: {kb.count()}")


def cmd_query(args: argparse.Namespace) -> None:
    kb = SolarKnowledgeBase()
    if kb.count() == 0:
        print("Warning: knowledge base is empty. Run 'python main.py ingest' first.")

    response = answer_query(args.question, kb, category_filter=args.category)
    print("\n" + "=" * 80)
    print("ANSWER")
    print("=" * 80)
    print(response.answer)
    print("\n" + "-" * 80)
    print(f"Retrieved {len(response.retrieved_chunks)} source chunks:")
    for c in response.retrieved_chunks:
        print(f"  - {c['title']} [{c['category']}] (distance={c['distance']:.3f})")


def cmd_irradiance(args: argparse.Namespace) -> None:
    raw = fetch_city_irradiance(args.city, start_year=args.start_year, end_year=args.end_year)
    summary = summarize_irradiance(raw)
    print(json.dumps(summary, indent=2))
    worst = get_worst_month_psh(summary)
    print(f"\nWorst-month PSH for {args.city}: {worst} kWh/m^2/day "
          f"(use this for conservative hybrid/off-grid sizing)")


def cmd_forecast(args: argparse.Namespace) -> None:
    raw = fetch_forecast(args.city, forecast_days=args.days)
    for day in summarize_forecast(raw):
        print(day)


def _resolve_daily_load_wh(args: argparse.Namespace) -> float:
    """
    Determines the daily load in Wh, either from a pre-calculated total
    (--daily-load-wh) or by summing individual appliances from a JSON
    file (--appliances-json) and applying a design margin.

    Exactly one of the two input modes must be provided.
    """
    if args.appliances_json and args.daily_load_wh is not None:
        print("Error: provide either --daily-load-wh OR --appliances-json, not both.")
        sys.exit(1)

    if args.appliances_json:
        appliances = load_appliances_from_json(args.appliances_json)
        load_result = calculate_daily_load(appliances)

        print("\n" + "=" * 80)
        print("APPLIANCE LOAD BREAKDOWN")
        print("=" * 80)
        for name, wh in load_result.assumptions["appliance_breakdown_wh_per_day"].items():
            print(f"  {name}: {wh} Wh/day")
        for w in load_result.warnings:
            print(f"  ⚠ {w}")
        print(f"\nRaw appliance total: {load_result.value} Wh/day")

        margin_result = apply_design_margin(load_result.value, margin_fraction=args.margin)
        print(f"With {args.margin:.0%} design margin applied: {margin_result.value} Wh/day")
        for w in margin_result.warnings:
            print(f"  ⚠ {w}")

        return margin_result.value

    if args.daily_load_wh is not None:
        return args.daily_load_wh

    print("Error: provide either --daily-load-wh or --appliances-json.")
    sys.exit(1)


def cmd_load_survey(args: argparse.Namespace) -> None:
    """
    Interactive terminal-based load survey. Works end-to-end on a local
    terminal. In Colab, running this via `!python main.py load-survey`
    will likely NOT prompt reliably (subprocess stdin limitation) — call
    interactive_load_survey() directly in a notebook cell instead:

        from validation.load_calculator import interactive_load_survey
        result = interactive_load_survey()
    """
    result = interactive_load_survey()
    print(f"\nTotal daily load: {result.value} Wh/day")
    print("Use this value with: python main.py size --daily-load-wh <value> ...")


def cmd_size(args: argparse.Namespace) -> None:
    """Full worked example: live irradiance data -> validated formulas -> RAG narration."""

    daily_load_wh = _resolve_daily_load_wh(args)

    # Step 1: get worst-month PSH for the chosen city — skip the live NASA
    # POWER fetch entirely if the caller already supplied --psh manually.
    if args.psh is not None:
        psh = args.psh
        print(f"Using manually supplied PSH: {psh} kWh/m^2/day (skipped live NASA POWER fetch)")
    else:
        raw = fetch_city_irradiance(args.city, start_year=2018, end_year=2023)
        summary = summarize_irradiance(raw)
        psh = get_worst_month_psh(summary)
        if psh is None:
            print("Could not determine PSH from NASA POWER data; pass --psh manually.")
            sys.exit(1)
        print(f"Using worst-month PSH for {args.city}: {psh} kWh/m^2/day")

    # Step 2: run validated formulas
    array_result = size_array(daily_load_wh, psh, derate_factor=args.derate_factor)
    inverter_result = size_inverter(
        array_result.value, args.simultaneous_load_w, dc_ac_ratio=args.dc_ac_ratio
    )
    battery_result = size_battery_bank(
        daily_load_wh, args.days_autonomy, args.voltage, args.dod, args.chemistry
    )
    controller_result = size_charge_controller(array_result.value, args.voltage)

    calculated_results = {
        "Array size": array_result,
        "Inverter size": inverter_result,
        "Battery bank": battery_result,
        "Charge controller": controller_result,
    }

    print("\n" + "=" * 80)
    print("VALIDATED CALCULATION RESULTS")
    print("=" * 80)
    for name, result in calculated_results.items():
        print(f"\n{name}: {result.value} {result.unit}")
        print(f"  Formula: {result.formula}")
        for w in result.warnings:
            print(f"  ⚠ {w}")

    # Step 3: RAG-grounded narration/explanation (requires ANTHROPIC_API_KEY)
    if args.explain:
        kb = SolarKnowledgeBase()
        query = (
            f"Explain and justify this solar sizing result for {args.city}, Pakistan, "
            f"citing relevant standards and any Pakistani regulatory considerations "
            f"(e.g., net metering) that apply."
        )
        response = answer_query(query, kb, calculated_results=calculated_results)
        print("\n" + "=" * 80)
        print("RAG-GENERATED EXPLANATION")
        print("=" * 80)
        print(response.answer)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solar Sizing RAG System")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingest documents into the vector store")
    p_ingest.set_defaults(func=cmd_ingest)

    p_query = sub.add_parser("query", help="Ask a question against the knowledge base")
    p_query.add_argument("question", type=str)
    p_query.add_argument("--category", type=str, default=None,
                          help="Restrict retrieval to one category, e.g. pk_regulation_tariff")
    p_query.set_defaults(func=cmd_query)

    p_irr = sub.add_parser("irradiance", help="Fetch historical irradiance for a PK city")
    p_irr.add_argument("--city", type=str, required=True, choices=list(PAKISTAN_CITIES.keys()))
    p_irr.add_argument("--start-year", type=int, default=2018)
    p_irr.add_argument("--end-year", type=int, default=2023)
    p_irr.set_defaults(func=cmd_irradiance)

    p_fc = sub.add_parser("forecast", help="Fetch a short-term solar forecast for a PK city")
    p_fc.add_argument("--city", type=str, required=True, choices=list(PAKISTAN_CITIES.keys()))
    p_fc.add_argument("--days", type=int, default=7)
    p_fc.set_defaults(func=cmd_forecast)

    p_load = sub.add_parser(
        "load-survey",
        help="Interactively calculate daily load from appliance inputs (local terminal only)",
    )
    p_load.set_defaults(func=cmd_load_survey)

    p_size = sub.add_parser("size", help="Run a full worked sizing example")
    p_size.add_argument("--city", type=str, required=True, choices=list(PAKISTAN_CITIES.keys()))
    p_size.add_argument(
        "--daily-load-wh", type=float, default=None,
        help="Pre-calculated total daily load in Wh. Mutually exclusive with --appliances-json.",
    )
    p_size.add_argument(
        "--appliances-json", type=str, default=None,
        help="Path to a JSON file of appliances (name/power_w/hours_per_day/quantity); "
             "see data/sample_appliances.json for the expected format. The total is "
             "computed automatically and a design margin is applied. Mutually exclusive "
             "with --daily-load-wh.",
    )
    p_size.add_argument(
        "--margin", type=float, default=0.25,
        help="Design margin applied on top of the appliance-computed total "
             "(only used with --appliances-json). Default 0.25 (25%%).",
    )
    p_size.add_argument("--simultaneous-load-w", type=float, default=2400.0)
    p_size.add_argument("--voltage", type=float, default=48.0)
    p_size.add_argument("--dod", type=float, default=0.9)
    p_size.add_argument("--chemistry", type=str, default="lifepo4")
    p_size.add_argument("--days-autonomy", type=float, default=1.0)
    p_size.add_argument("--derate-factor", type=float, default=0.80)
    p_size.add_argument("--dc-ac-ratio", type=float, default=1.10)
    p_size.add_argument("--psh", type=float, default=None,
                         help="Override PSH manually instead of fetching from NASA POWER")
    p_size.add_argument("--explain", action="store_true",
                         help="Also generate a RAG-grounded explanation (requires ANTHROPIC_API_KEY)")
    p_size.set_defaults(func=cmd_size)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
