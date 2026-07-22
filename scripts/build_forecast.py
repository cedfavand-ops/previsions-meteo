"""
Script principal du pipeline.

Étapes :
1. Récupère la dernière prévision AROME HD disponible (run 12z si le
   script est déclenché après ingestion de ce run, cf. README) pour la
   station.
2. Récupère les observations récentes de la station perso (temp/humidité)
   et de la station voisine (vent).
3. Calcule un biais glissant et recalibre température, humidité et vent.
   La pluie reste la prévision AROME brute (non recalibrée).
4. Calcule TN (min. sur la nuit à venir) et TX (max. du lendemain).
5. Associe un pictogramme (catégorie sémantique) à chaque heure.
6. Écrit data/forecast.json, consommé par la page HTML.

Exécuter avec : python scripts/build_forecast.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import traceback

from config import (
    STATION_TEMP_HUMI,
    STATION_WIND,
    BIAS_WINDOW_HOURS,
    BIAS_DECAY_HOURS_TEMP_HUMI,
    BIAS_DECAY_HOURS_WIND,
    FORECAST_HOURS,
    OUTPUT_PATH,
)
from fetch_arome import fetch_arome_forecast, AromeFetchError
from fetch_infoclimat import fetch_station_observations, InfoclimatFetchError
from bias_correction import compute_bias, apply_decaying_bias
from weather_icons import category_for


def _is_day(time_iso: str, daily: dict) -> bool:
    date_key = time_iso[:10]
    try:
        idx = daily["time"].index(date_key)
    except ValueError:
        # Pas d'info jour/nuit dispo pour cette date -> estimation grossière
        hour = int(time_iso[11:13])
        return 7 <= hour <= 21

    sunrise = daily["sunrise"][idx]
    sunset = daily["sunset"][idx]
    return sunrise <= time_iso <= sunset


def _compute_tn_tx(hourly: list[dict]) -> dict:
    """TN = min de température recalibrée sur la nuit à venir (prochain
    passage 18h-10h). TX = max sur le prochain jour (10h-20h du lendemain).
    Heuristique simple mais robuste sur un horizon de 36h.
    """
    now = dt.datetime.now(dt.timezone.utc)

    night_candidates = []
    day_candidates = []

    for f in hourly:
        t = dt.datetime.fromisoformat(f["time"].replace("Z", "+00:00"))
        if t.tzinfo is None:
            # timezone locale déjà appliquée par Open-Meteo (Europe/Paris)
            t = t.replace(tzinfo=dt.timezone.utc)  # approx pour comparaison relative
        hour_local = int(f["time"][11:13])

        is_night_hour = hour_local >= 18 or hour_local <= 9
        is_day_hour = 10 <= hour_local <= 20

        if is_night_hour:
            night_candidates.append(f)
        if is_day_hour:
            day_candidates.append(f)

    tn = min(
        night_candidates,
        key=lambda f: f["temperature_2m_recalibre"],
        default=None,
    )
    tx = max(
        day_candidates,
        key=lambda f: f["temperature_2m_recalibre"],
        default=None,
    )

    return {
        "tn": {"time": tn["time"], "value": round(tn["temperature_2m_recalibre"], 1)} if tn else None,
        "tx": {"time": tx["time"], "value": round(tx["temperature_2m_recalibre"], 1)} if tx else None,
    }


def main() -> int:
    warnings = []

    arome = fetch_arome_forecast()
    hourly = arome["hourly"][:FORECAST_HOURS]
    daily = arome["daily"]

    # --- Observations station perso (temp/humidité) ---
    try:
        obs_temp_humi = fetch_station_observations(
            STATION_TEMP_HUMI["infoclimat_id"], hours_back=max(6, BIAS_WINDOW_HOURS * 2)
        )
    except InfoclimatFetchError as e:
        warnings.append(f"Station temp/humidité indisponible : {e}")
        obs_temp_humi = []

    # --- Observations station voisine (vent) ---
    try:
        obs_wind = fetch_station_observations(
            STATION_WIND["infoclimat_id"], hours_back=max(6, BIAS_WINDOW_HOURS * 2)
        )
    except InfoclimatFetchError as e:
        warnings.append(f"Station vent indisponible : {e}")
        obs_wind = []

    # --- Biais température ---
    bias_temp = compute_bias(
        hourly, obs_temp_humi, "temperature_2m", "temperature", BIAS_WINDOW_HOURS
    )
    apply_decaying_bias(
        hourly, "temperature_2m", bias_temp, BIAS_DECAY_HOURS_TEMP_HUMI, "temperature_2m_recalibre"
    )

    # --- Biais humidité ---
    bias_humi = compute_bias(
        hourly, obs_temp_humi, "relative_humidity_2m", "humidity", BIAS_WINDOW_HOURS
    )
    apply_decaying_bias(
        hourly, "relative_humidity_2m", bias_humi, BIAS_DECAY_HOURS_TEMP_HUMI, "relative_humidity_2m_recalibre"
    )

    # --- Biais vent (vitesse) ---
    bias_wind = compute_bias(
        hourly, obs_wind, "windspeed_10m", "wind_speed", BIAS_WINDOW_HOURS
    )
    apply_decaying_bias(
        hourly, "windspeed_10m", bias_wind, BIAS_DECAY_HOURS_WIND, "windspeed_10m_recalibre"
    )

    # La direction du vent n'est pas recalibrée par biais additif (ça n'a pas
    # de sens sur un angle) : on garde AROME brut pour la direction.
    for f in hourly:
        f["winddirection_10m_recalibre"] = f["winddirection_10m"]
        # Bornes physiques : humidité recalibrée dans [0, 100], vent >= 0
        f["relative_humidity_2m_recalibre"] = max(0, min(100, f["relative_humidity_2m_recalibre"]))
        f["windspeed_10m_recalibre"] = max(0, f["windspeed_10m_recalibre"])

    # --- Pictogramme par heure ---
    for f in hourly:
        f["is_day"] = _is_day(f["time"], daily)
        f["icon_category"] = category_for(f["weathercode"])

    # --- TN / TX ---
    tn_tx = _compute_tn_tx(hourly)

    output = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "model": arome["model"],
        "arome_first_hourly_time": arome["first_hourly_time"],
        "station_temp_humi": STATION_TEMP_HUMI,
        "station_wind": STATION_WIND,
        "bias_applied": {
            "temperature": bias_temp,
            "humidity": bias_humi,
            "wind_speed": bias_wind,
        },
        "warnings": warnings,
        "tn_tonight": tn_tx["tn"],
        "tx_tomorrow": tn_tx["tx"],
        "hourly": [
            {
                "time": f["time"],
                "temperature": round(f["temperature_2m_recalibre"], 1),
                "temperature_brute_arome": round(f["temperature_2m"], 1),
                "humidity": round(f["relative_humidity_2m_recalibre"]),
                "precipitation": f["precipitation"],
                "wind_speed": round(f["windspeed_10m_recalibre"], 1),
                "wind_gust": f["windgusts_10m"],
                "wind_direction": f["winddirection_10m_recalibre"],
                "weathercode": f["weathercode"],
                "icon_category": f["icon_category"],
                "is_day": f["is_day"],
            }
            for f in hourly
        ],
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    print(f"OK — forecast.json écrit ({len(hourly)} heures). Avertissements: {warnings}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AromeFetchError as e:
        print(f"Erreur AROME : {e}", file=sys.stderr)
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
