"""
config.py
---------
Central configuration for the Solar Sizing RAG system.

All paths, model names, and reference constants live here so the rest
of the codebase never hardcodes them.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"          # drop PDFs/txt of standards, tariffs here
CHROMA_DB_DIR = DATA_DIR / "chroma_db"          # persistent vector store
CACHE_DIR = DATA_DIR / "cache"                  # cached weather/irradiance pulls

for p in (DOCUMENTS_DIR, CHROMA_DB_DIR, CACHE_DIR):
    p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# API keys (set these as environment variables — never hardcode secrets)
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# ---------------------------------------------------------------------------
# Embedding / retrieval settings
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # local, no API key needed
CHUNK_SIZE = 900            # characters per chunk
CHUNK_OVERLAP = 150         # characters of overlap between chunks
TOP_K_RETRIEVAL = 6         # number of chunks retrieved per query
COLLECTION_NAME = "solar_sizing_kb"

# ---------------------------------------------------------------------------
# Document category tags used as Chroma metadata (lets you filter retrieval,
# e.g. "only search NEPRA tariff documents" or "only search IEC standards")
# ---------------------------------------------------------------------------
DOC_CATEGORIES = [
    "sizing_methodology",     # textbooks, IEEE/NREL sizing guides
    "standard",               # IEC 61730, IEC 62109, NEC 690, IEEE 1547, etc.
    "pk_regulation_tariff",   # NEPRA net-metering regs, tariff determinations, AEDB guidelines
    "dataset_documentation",  # PVGIS/NASA POWER/NSRDB methodology docs
    "manufacturer_datasheet", # panel/inverter/battery datasheets (narrative/PDF form)
    "equipment_dataset",      # structured CSV/JSON equipment+cost catalog rows
    "faq",                    # common user questions, per PRD Section 4/5.2/5.3
    "other",
]

# Directory scanned for structured equipment/cost catalogs (.csv/.json).
# Defaults to a subfolder of DOCUMENTS_DIR so it ships with the same zip,
# but can be repointed at Qadeer's actual engine dataset file/folder to
# avoid maintaining two copies of the same catalog — see
# data_ingestion/dataset_loader.py and the README's integration notes.
EQUIPMENT_DATASET_DIR = DOCUMENTS_DIR / "equipment_dataset"

# ---------------------------------------------------------------------------
# Pakistan reference data
# ---------------------------------------------------------------------------
# Major cities with lat/lon, used by weather_fetcher.py and forecast_fetcher.py
PAKISTAN_CITIES = {
    "Islamabad":  {"lat": 33.6844, "lon": 73.0479},
    "Lahore":     {"lat": 31.5497, "lon": 74.3436},
    "Karachi":    {"lat": 24.8607, "lon": 67.0011},
    "Faisalabad": {"lat": 31.4504, "lon": 73.1350},
    "Multan":     {"lat": 30.1575, "lon": 71.5249},
    "Peshawar":   {"lat": 34.0151, "lon": 71.5249},
    "Quetta":     {"lat": 30.1798, "lon": 66.9750},
    "Chakwal":    {"lat": 32.9328, "lon": 72.8630},
    "Hyderabad":  {"lat": 25.3960, "lon": 68.3578},
    "Sialkot":    {"lat": 32.4945, "lon": 74.5229},
    "Rawalpindi": {"lat": 33.5651, "lon": 73.0169},
    "Sukkur":     {"lat": 27.7052, "lon": 68.8574},
}

# Known Pakistani regulatory / standards references worth ingesting.
# NOTE: these are pointers for YOU to download the actual PDFs (respecting
# each source's terms of use) into DOCUMENTS_DIR — the loader will not
# scrape copyrighted PDFs automatically. Listed here so nothing is missed.
PK_REGULATORY_REFERENCES = [
    {
        "name": "NEPRA Net Metering Regulations (as amended)",
        "issuer": "NEPRA",
        "topic": "Distributed generation / net metering tariff rules",
        "url_hint": "https://nepra.org.pk  (search: Net Metering Regulations)",
        "category": "pk_regulation_tariff",
    },
    {
        "name": "NEPRA Generation Tariff Determinations (Solar PV, upfront tariff)",
        "issuer": "NEPRA",
        "topic": "Upfront tariff for small-scale solar PV generation",
        "url_hint": "https://nepra.org.pk  (search: upfront solar tariff determination)",
        "category": "pk_regulation_tariff",
    },
    {
        "name": "AEDB Guidelines for Net Metering / Solar Installations",
        "issuer": "Alternative Energy Development Board (AEDB)",
        "topic": "Installation, interconnection, and application guidelines",
        "url_hint": "https://www.aedb.org",
        "category": "pk_regulation_tariff",
    },
    {
        "name": "IEC 61730 — PV Module Safety Qualification",
        "issuer": "IEC",
        "topic": "Module safety/construction standard",
        "url_hint": "iec.ch (paid standard)",
        "category": "standard",
    },
    {
        "name": "IEC 62109 — Safety of Power Converters for PV Systems",
        "issuer": "IEC",
        "topic": "Inverter safety standard",
        "url_hint": "iec.ch (paid standard)",
        "category": "standard",
    },
    {
        "name": "IEEE 1547 — Interconnection of DER with Grid",
        "issuer": "IEEE",
        "topic": "Grid interconnection standard for distributed energy resources",
        "url_hint": "standards.ieee.org",
        "category": "standard",
    },
    {
        "name": "NEC Article 690 — Solar PV Systems",
        "issuer": "NFPA",
        "topic": "US electrical code for PV systems (referenced globally as best practice)",
        "url_hint": "nfpa.org",
        "category": "standard",
    },
]
