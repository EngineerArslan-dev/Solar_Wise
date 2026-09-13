"""
forecast_fetcher.py
--------------------
Pulls short-term (up to 16-day) solar radiation and weather forecasts
for Pakistani cities using the Open-Meteo API (free, no API key required).

This complements weather_fetcher.py: NASA POWER gives long-term historical
averages for *design* sizing, while this module gives near-term forecasts
useful for operational decisions (e.g., "should the hybrid inverter
prioritize battery charging or grid draw over the next 3 days?").

Docs: https://open-meteo.com/en/docs
"""

from __future__ import annotations

import logging
from typing import Dict, List

import requests

from config import PAKISTAN_CITIES

logger = logging.getLogger(__name__)

OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

DAILY_VARIABLES = ",".join([
    "shortwave_radiation_sum",   # MJ/m^2 -> convertible to kWh/m^2 (PSH)
    "temperature_2m_max",
    "temperature_2m_min",
    "cloudcover_mean",
    "precipitation_sum",
])


def fetch_forecast(city: str, forecast_days: int = 7, timeout: int = 20) -> Dict:
    """
    Fetch a daily solar/weather forecast for a Pakistani city.

    Returns raw Open-Meteo JSON. Use `summarize_forecast()` to convert
    shortwave radiation sums (MJ/m^2/day) into peak-sun-hour equivalents
    (kWh/m^2/day) for direct use in the sizing formulas.
    """
    if city not in PAKISTAN_CITIES:
        raise KeyError(f"'{city}' not in config.PAKISTAN_CITIES.")

    coords = PAKISTAN_CITIES[city]
    params = {
        "latitude": coords["lat"],
        "longitude": coords["lon"],
        "daily": DAILY_VARIABLES,
        "forecast_days": min(forecast_days, 16),
        "timezone": "Asia/Karachi",
    }

    logger.info("Fetching %d-day forecast for %s...", forecast_days, city)
    resp = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def summarize_forecast(raw_forecast: Dict) -> List[Dict]:
    """
    Convert raw Open-Meteo response into a list of per-day dicts:

        [{"date": "2026-09-13", "psh_equivalent": 5.8, "temp_max_c": 34.2,
          "temp_min_c": 24.1, "cloudcover_pct": 22, "precip_mm": 0.0}, ...]

    Conversion: 1 MJ/m^2 = 0.2778 kWh/m^2 (since 1 kWh = 3.6 MJ).
    """
    try:
        daily = raw_forecast["daily"]
    except KeyError as e:
        raise ValueError("Unexpected Open-Meteo response structure.") from e

    MJ_TO_KWH = 1.0 / 3.6
    results = []
    for i, date in enumerate(daily["time"]):
        radiation_mj = daily["shortwave_radiation_sum"][i]
        results.append({
            "date": date,
            "psh_equivalent": round(radiation_mj * MJ_TO_KWH, 2) if radiation_mj is not None else None,
            "temp_max_c": daily["temperature_2m_max"][i],
            "temp_min_c": daily["temperature_2m_min"][i],
            "cloudcover_pct": daily["cloudcover_mean"][i],
            "precip_mm": daily["precipitation_sum"][i],
        })
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raw = fetch_forecast("Lahore", forecast_days=5)
    for day in summarize_forecast(raw):
        print(day)
