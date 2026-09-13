"""
dataset_loader.py
------------------
Loads structured equipment/cost catalogs (CSV or JSON — panels,
inverters, batteries, controllers, with specs and pricing) and converts
each row into a retrievable text chunk, so the RAG system can cite
specific catalog entries ("the Jinko Tiger Neo 585W costs approximately
Rs X") rather than only the narrative-style reference documents in
manufacturer_datasheet/.

This is deliberately kept separate from document_loader.py: prose
documents (PDF/txt/md) and structured tabular rows need fundamentally
different parsing, even though both end up as RawDocument objects
feeding the same chunker/embedder/vector-store pipeline.

Expected format — CSV:
    type,brand,model,rated_power_w,price_pkr,efficiency_pct,warranty_years,notes
    panel,Jinko,Tiger Neo 585W,585,26900,22.3,25,N-type bifacial
    inverter,Growatt,SPH 5000,5000,180000,97.6,10,hybrid on/off-grid
    battery,Dyness,PowerBox Plus 5.1kWh,,178500,,10,LiFePO4 51.2V

Expected format — JSON: a list of objects with the same field names.

Column names are flexible — any columns present are included in the
generated text and as chunk metadata (metadata values must be
str/int/float/bool; the vector store silently drops anything else, so
avoid nested objects in dataset rows).

IMPORTANT — avoiding duplication with Qadeer's engine dataset: if the
team already maintains a canonical equipment/cost CSV/JSON for the
Python calculation engine (PRD Section 4: "Static equipment/cost
dataset (CSV/JSON)"), point EQUIPMENT_DATASET_DIR (config.py) at that
same file/folder rather than maintaining a second copy here. This
loader only reads the data — it never writes to or modifies it.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Dict, List

from config import EQUIPMENT_DATASET_DIR
from data_ingestion.document_loader import RawDocument

logger = logging.getLogger(__name__)

# Columns that, when present, anchor the generated sentence's subject
# (e.g. "Jinko Tiger Neo 585W (panel):"). Everything else is appended as
# "field: value" pairs in the order the source file provides them.
_ANCHOR_FIELDS = ["type", "brand", "model"]


def _row_to_text(row: Dict) -> str:
    """Convert one catalog row into a natural-language sentence plus a
    structured field listing, so it reads well both to a human and to
    an embedding model."""
    brand = str(row.get("brand", "")).strip()
    model = str(row.get("model", "")).strip()
    item_type = str(row.get("type", "")).strip()

    subject_bits = [b for b in (brand, model) if b]
    subject = " ".join(subject_bits) if subject_bits else "This catalog item"
    type_suffix = f" ({item_type})" if item_type else ""

    lines = [f"{subject}{type_suffix}."]
    for key, value in row.items():
        if key in _ANCHOR_FIELDS:
            continue
        if value in (None, "", "nan"):
            continue
        lines.append(f"{key.replace('_', ' ')}: {value}")

    return " ".join(lines)


def _row_to_metadata(row: Dict) -> Dict:
    """Keep only primitive-typed, non-empty fields — the vector store
    drops non-primitives silently, and an empty string isn't a useful
    metadata value for filtering, so both are excluded here."""
    metadata = {}
    for key, value in row.items():
        if isinstance(value, (str, int, float, bool)) and value != "":
            metadata[f"item_{key}"] = value
    return metadata


def _load_csv(path: Path) -> List[Dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_json(path: Path) -> List[Dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path.name}: expected a JSON list of row objects.")
    return data


def load_equipment_datasets(root_dir: Path = EQUIPMENT_DATASET_DIR) -> List[RawDocument]:
    """
    Scan root_dir for .csv and .json equipment catalogs and return one
    RawDocument per row, tagged with category="equipment_dataset" and
    per-row metadata (item_brand, item_model, item_price_pkr, etc.) so
    retrieval can be filtered or the answer can cite specific fields.
    """
    documents: List[RawDocument] = []

    if not root_dir.exists():
        logger.info("No equipment dataset directory at %s — skipping.", root_dir)
        return documents

    files = [p for p in root_dir.iterdir() if p.is_file() and p.suffix.lower() in (".csv", ".json")]
    if not files:
        logger.info("No .csv/.json equipment catalogs found in %s.", root_dir)
        return documents

    for path in files:
        try:
            rows = _load_csv(path) if path.suffix.lower() == ".csv" else _load_json(path)
        except Exception as exc:  # noqa: BLE001 — skip a bad file, don't abort ingestion
            logger.error("Failed to load equipment dataset %s: %s", path, exc)
            continue

        for i, row in enumerate(rows):
            text = _row_to_text(row)
            title_bits = [str(row.get("brand", "")), str(row.get("model", ""))]
            title = " ".join(b for b in title_bits if b).strip() or f"{path.stem} row {i}"

            documents.append(RawDocument(
                doc_id=f"{path.name}::row{i}",
                text=text,
                source_path=str(path),
                category="equipment_dataset",
                title=title,
                metadata=_row_to_metadata(row),
            ))

        logger.info("Loaded %d rows from %s", len(rows), path.name)

    return documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    docs = load_equipment_datasets()
    print(f"Loaded {len(docs)} equipment catalog rows.")
    for d in docs[:5]:
        print(f"  - {d.title}: {d.text}")
