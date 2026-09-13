# Equipment Dataset Folder

Drop `.csv` or `.json` equipment/cost catalog files here. Each row
becomes a separately retrievable, citable chunk in the RAG knowledge
base — this is the structured counterpart to the narrative documents in
`manufacturer_datasheet/`.

## About `sample_equipment_catalog.csv`

This is placeholder/illustrative data for testing the ingestion
pipeline — the brand/model combinations are real products, but the
prices are approximate figures for demonstration, **not verified
current market quotes**. Do not present these specific numbers to a
user as authoritative pricing.

## Replacing this with the real catalog

If Qadeer's Python calculation engine already maintains a canonical
equipment/cost dataset (per PRD Section 4), the better path is usually
to point `config.EQUIPMENT_DATASET_DIR` at that same file/folder rather
than copying it here — see `data_ingestion/dataset_loader.py`'s module
docstring for the expected column format. Keeping one source of truth
avoids the engine and the RAG knowledge base silently drifting out of
sync as prices are updated.

## Expected columns

Flexible — any columns present are included. Commonly useful ones:
`type` (panel/inverter/battery/controller), `brand`, `model`,
`rated_power_w`, `price_pkr`, `efficiency_pct`, `warranty_years`,
`notes`.
