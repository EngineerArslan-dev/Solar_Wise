"""
document_loader.py
-------------------
Loads reference documents (engineering standards, NEPRA tariff/regulation
PDFs, sizing-methodology textbooks/papers, datasheet PDFs) from
config.DOCUMENTS_DIR and returns them as plain-text records ready for
chunking.

Supported formats: .pdf, .txt, .md

Expected folder convention (not enforced, but recommended so metadata
tagging is accurate):

    data/documents/
        standards/            -> IEC, IEEE, NEC docs
        pk_regulation_tariff/ -> NEPRA / AEDB PDFs
        sizing_methodology/   -> textbooks, NREL/IEEE sizing guides
        dataset_documentation/-> PVGIS / NASA POWER / NSRDB manuals
        manufacturer_datasheet/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from config import DOCUMENTS_DIR, DOC_CATEGORIES, EQUIPMENT_DATASET_DIR

logger = logging.getLogger(__name__)


@dataclass
class RawDocument:
    """A single ingested document before chunking."""
    doc_id: str
    text: str
    source_path: str
    category: str
    title: str = ""
    metadata: dict = field(default_factory=dict)


def _infer_category(path: Path) -> str:
    """Infer document category from its parent folder name, falling back
    to 'other' if it doesn't match a known category."""
    parent_name = path.parent.name
    if parent_name in DOC_CATEGORIES:
        return parent_name
    return "other"


def _load_pdf(path: Path) -> str:
    """Extract text from a PDF using pypdf. Raises informatively if the
    PDF is scanned/image-only (no extractable text layer)."""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ImportError(
            "pypdf is required to load PDF documents. Install with: pip install pypdf"
        ) from e

    reader = PdfReader(str(path))
    pages_text = []
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages_text.append(text)
        else:
            logger.warning(
                "No extractable text on page %d of %s (likely scanned image — "
                "consider OCR before ingesting).", page_num + 1, path.name
            )
    return "\n".join(pages_text)


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _load_json_as_text(path: Path) -> str:
    """Generic JSON loader for reference data files that aren't equipment
    catalog rows (see data_ingestion/dataset_loader.py for that case) —
    just pretty-prints the structure so it's searchable text. Good for
    things like the verified NASA POWER data snapshot in
    dataset_documentation/, which is a single nested object, not a list
    of rows."""
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(data, indent=2)


def load_documents(root_dir: Path = DOCUMENTS_DIR) -> List[RawDocument]:
    """
    Walk root_dir recursively, load every supported file, and return a
    list of RawDocument records.
    """
    supported_ext = {
        ".pdf": _load_pdf,
        ".txt": _load_text,
        ".md": _load_text,
        ".json": _load_json_as_text,
    }
    documents: List[RawDocument] = []

    if not root_dir.exists():
        logger.warning("Documents directory %s does not exist.", root_dir)
        return documents

    files = [p for p in root_dir.rglob("*") if p.is_file() and p.suffix.lower() in supported_ext]

    # equipment_dataset/*.json is handled row-by-row by dataset_loader.py
    # (structured catalog rows) — skip it here to avoid double-ingesting
    # the same file as both a generic text dump and individual rows.
    # .csv is unaffected since it's not in supported_ext above, but .json
    # would otherwise be picked up by both loaders.
    try:
        equipment_dir_resolved = EQUIPMENT_DATASET_DIR.resolve()
        files = [
            p for p in files
            if not (p.suffix.lower() == ".json" and equipment_dir_resolved in p.resolve().parents)
        ]
    except OSError:
        pass  # if EQUIPMENT_DATASET_DIR doesn't exist yet, nothing to exclude

    if not files:
        logger.warning(
            "No documents found in %s. Add PDFs/txt files (standards, NEPRA "
            "tariff docs, sizing guides) before running ingestion.", root_dir
        )

    for path in files:
        loader_fn = supported_ext[path.suffix.lower()]
        try:
            text = loader_fn(path)
        except Exception as exc:  # noqa: BLE001 - we want to skip bad files, not crash ingestion
            logger.error("Failed to load %s: %s", path, exc)
            continue

        if not text.strip():
            logger.warning("Skipping %s — no extractable text.", path)
            continue

        doc = RawDocument(
            doc_id=str(path.relative_to(root_dir)),
            text=text,
            source_path=str(path),
            category=_infer_category(path),
            title=path.stem.replace("_", " "),
        )
        documents.append(doc)
        logger.info("Loaded %s (%d chars, category=%s)", path.name, len(text), doc.category)

    return documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    docs = load_documents()
    print(f"Loaded {len(docs)} documents.")
    for d in docs:
        print(f"  - {d.doc_id} [{d.category}] ({len(d.text)} chars)")
