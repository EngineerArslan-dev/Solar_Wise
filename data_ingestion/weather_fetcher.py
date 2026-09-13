"""
weather_fetcher.py
-------------------
Pulls historical solar irradiance and weather data for major Pakistani
cities from NASA POWER (Prediction Of Worldwide Energy Resources) —
a free, no-API-key-required source that PVGIS and NREL tools also draw
on for solar-resource assessment. This gives the RAG system authoritative
NUMERIC data (not just text) to ground sizing calculations, distinct from
the textual standards/methodology documents.

Docs: https://power.larc.nasa.gov/docs/services/api/

Key parameters pulled:
    ALLSKY_SFC_SW_DWN  -> All-sky surface shortwave downward irradiance
                          (kWh/m^2/day) == "peak sun hours" numerically
    CLRSKY_SFC_SW_DWN  -> Clear-sky irradiance (theoretical max, useful
                          as an upper bound / sanity check)
    T2M                -> Temperature at 2m (affects panel derating)
    WS2M               -> Wind speed at 2m (affects cooling/derating)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional

import requests

from config import CACHE_DIR, PAKISTAN_CITIES

logger = logging.getLogger(__name__)

NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"

# Parameters requested from the API in one call
POWER_PARAMETERS = ",".join([
    "ALLSKY_SFC_SW_DWN",
    "CLRSKY_SFC_SW_DWN",
    "T2M",
    "WS2M",
])


def _cache_path(city: str, start: int, end: int) -> Path:
    return CACHE_DIR / f"nasa_power_{city.lower()}_{start}_{end}.json"


def fetch_city_irradiance(
    city: str,
    start_year: int = 2015,
    end_year: int = 2023,
    use_cache: bool = True,
    timeout: int = 30,
) -> Dict:
    """
    Fetch monthly-average irradiance/weather data for a Pakistani city.

    Returns the raw NASA POWER JSON response (dict). Use
    `summarize_irradiance()` below to turn this into peak-sun-hour figures
    ready for the sizing formulas.

    Raises:
        KeyError if `city` is not in config.PAKISTAN_CITIES.
        requests.RequestException on network/API failure.
    """
    if city not in PAKISTAN_CITIES:
        raise KeyError(
            f"'{city}' not in config.PAKISTAN_CITIES. "
            f"Available: {list(PAKISTAN_CITIES.keys())}"
        )

    cache_file = _cache_path(city, start_year, end_year)
    if use_cache and cache_file.exists():
        logger.info("Loading cached NASA POWER data for %s", city)
        return json.loads(cache_file.read_text())

    coords = PAKISTAN_CITIES[city]
    params = {
        "parameters": POWER_PARAMETERS,
        "community": "RE",  # Renewable Energy community preset
        "longitude": coords["lon"],
        "latitude": coords["lat"],
        "start": start_year,
        "end": end_year,
        "format": "JSON",
    }

    logger.info("Fetching NASA POWER data for %s (%s-%s)...", city, start_year, end_year)
    resp = requests.get(NASA_POWER_BASE_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    cache_file.write_text(json.dumps(data))
    return data


def summarize_irradiance(raw_power_response: Dict) -> Dict[str, Dict[str, float]]:
    """
    Convert raw NASA POWER JSON into a clean monthly summary:

        {
          "JAN": {"psh": 4.1, "clearsky_psh": 5.0, "temp_c": 12.3, "wind_ms": 2.1},
          ...
          "ANN": {...}   # annual average
        }

    "psh" (peak sun hours) is numerically identical to ALLSKY_SFC_SW_DWN
    in kWh/m^2/day, per standard PV engineering convention.
    """
    try:
        params = raw_power_response["properties"]["parameter"]
    except KeyError as e:
        raise ValueError("Unexpected NASA POWER response structure.") from e

    month_keys = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                  "JUL", "AUG", "SEP", "OCT", "NOV", "DEC", "ANN"]

    summary: Dict[str, Dict[str, float]] = {}
    allsky = params.get("ALLSKY_SFC_SW_DWN", {})
    clrsky = params.get("CLRSKY_SFC_SW_DWN", {})
    temp = params.get("T2M", {})
    wind = params.get("WS2M", {})

    # NASA POWER multi-year monthly-average keys look like "202301"; when
    # requesting a year range it also returns a long-term-average block
    # keyed by month abbreviation directly in some endpoints. We normalize
    # by averaging any year-month keys that share the same month suffix.
    def _monthly_average(param_dict: Dict[str, float]) -> Dict[str, float]:
        buckets: Dict[str, list] = {m: [] for m in month_keys}
        for key, value in param_dict.items():
            if value in (-999, -999.0):  # NASA POWER fill value for missing data
                continue
            # keys are like "201501".."201512" plus "201513" (annual) in some responses
            month_num = key[-2:]
            month_map = {
                "01": "JAN", "02": "FEB", "03": "MAR", "04": "APR",
                "05": "MAY", "06": "JUN", "07": "JUL", "08": "AUG",
                "09": "SEP", "10": "OCT", "11": "NOV", "12": "DEC",
                "13": "ANN",
            }
            month_label = month_map.get(month_num)
            if month_label:
                buckets[month_label].append(value)
        return {m: (sum(v) / len(v) if v else float("nan")) for m, v in buckets.items()}

    allsky_avg = _monthly_average(allsky)
    clrsky_avg = _monthly_average(clrsky)
    temp_avg = _monthly_average(temp)
    wind_avg = _monthly_average(wind)

    for m in month_keys:
        summary[m] = {
            "psh": round(allsky_avg.get(m, float("nan")), 2),
            "clearsky_psh": round(clrsky_avg.get(m, float("nan")), 2),
            "temp_c": round(temp_avg.get(m, float("nan")), 1),
            "wind_ms": round(wind_avg.get(m, float("nan")), 1),
        }

    return summary


def get_worst_month_psh(summary: Dict[str, Dict[str, float]]) -> Optional[float]:
    """Return the lowest monthly PSH (excluding the 'ANN' annual-average
    key) — this is the conservative figure to use for off-grid/hybrid
    battery-backed sizing, per standard practice."""
    monthly = {m: v["psh"] for m, v in summary.items() if m != "ANN"}
    valid = {m: v for m, v in monthly.items() if v == v}  # drop NaNs
    if not valid:
        return None
    return min(valid.values())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raw = fetch_city_irradiance("Chakwal", start_year=2018, end_year=2022)
    result = summarize_irradiance(raw)
    print(json.dumps(result, indent=2))
    print("Worst-month PSH:", get_worst_month_psh(result))
