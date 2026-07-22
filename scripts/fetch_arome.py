"""
Récupération des prévisions Météo-France via l'API Open-Meteo.

⚠️ Le modèle AROME France HD (1.3 km, "meteofrance_arome_france_hd") ne
fournit pas toutes les variables : pas d'humidité, de vent, ni de code
météo (seulement température, précipitations et quelques autres). C'est
documenté par Open-Meteo elle-même : "AROME France HD ... offers fewer
weather variables" que l'AROME France standard (2.5 km).

On combine donc deux appels :
1. AROME France HD -> température (résolution la plus fine, comme demandé)
   et précipitations.
2. AROME France standard (2.5 km) -> humidité, vent, code météo,
   nébulosité (variables absentes de la version HD).

Les deux séries sont fusionnées heure par heure (même grille horaire et
même fuseau horaire pour les deux appels).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import requests

from config import (
    AROME_LAT,
    AROME_LON,
    OPEN_METEO_URL,
    OPEN_METEO_MODEL_HD,
    OPEN_METEO_MODEL_STANDARD,
    OPEN_METEO_HD_VARS,
    OPEN_METEO_STANDARD_VARS,
    OPEN_METEO_DAILY_VARS,
    TIMEZONE,
)


class AromeFetchError(RuntimeError):
    pass


def _query_open_meteo(model: str, hourly_vars: list[str], daily_vars: list[str]) -> dict[str, Any]:
    params = {
        "latitude": AROME_LAT,
        "longitude": AROME_LON,
        "hourly": ",".join(hourly_vars),
        "daily": ",".join(daily_vars),
        "models": model,
        "timezone": TIMEZONE,
        "forecast_days": 3,
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=30)
    if resp.status_code != 200:
        raise AromeFetchError(
            f"Open-Meteo a répondu {resp.status_code} (modèle {model}): {resp.text[:300]}"
        )
    payload = resp.json()
    if "hourly" not in payload:
        raise AromeFetchError(f"Réponse Open-Meteo inattendue (modèle {model}): {payload}")
    return payload


def fetch_arome_forecast() -> dict[str, Any]:
    """Interroge Open-Meteo (AROME HD + AROME standard) et renvoie un dict
    structuré heure par heure, avec uniquement les heures pour lesquelles
    les deux modèles ont des données complètes.
    """
    hd_payload = _query_open_meteo(OPEN_METEO_MODEL_HD, OPEN_METEO_HD_VARS, OPEN_METEO_DAILY_VARS)
    std_payload = _query_open_meteo(
        OPEN_METEO_MODEL_STANDARD, OPEN_METEO_STANDARD_VARS, OPEN_METEO_DAILY_VARS
    )

    hd_hourly = hd_payload["hourly"]
    std_hourly = std_payload["hourly"]

    run_reference_time = hd_hourly["time"][0] if hd_hourly["time"] else None

    # Index des données "standard" par heure ronde, pour les associer aux
    # heures du modèle HD (les deux utilisent la même grille horaire et le
    # même fuseau, donc en théorie les clés "time" correspondent déjà —
    # on indexe quand même par sécurité en cas de léger décalage d'horizon).
    std_by_time = {}
    for i, t in enumerate(std_hourly["time"]):
        std_by_time[t] = {var: std_hourly[var][i] for var in OPEN_METEO_STANDARD_VARS}

    records = []
    for i, t in enumerate(hd_hourly["time"]):
        temp = hd_hourly["temperature_2m"][i]
        precip = hd_hourly["precipitation"][i]
        std = std_by_time.get(t)

        if temp is None or std is None or std.get("weathercode") is None:
            # Heure incomplète sur l'un des deux modèles (hors horizon
            # réellement couvert) : on l'ignore plutôt que de planter plus
            # loin dans le pipeline.
            continue

        records.append(
            {
                "time": t,
                "temperature_2m": temp,
                "precipitation": precip,
                "relative_humidity_2m": std["relative_humidity_2m"],
                "weathercode": std["weathercode"],
                "windspeed_10m": std["windspeed_10m"],
                "winddirection_10m": std["winddirection_10m"],
                "windgusts_10m": std["windgusts_10m"],
                "cloudcover": std["cloudcover"],
            }
        )

    daily = hd_payload.get("daily", {})

    return {
        "fetched_at": dt.datetime.utcnow().isoformat() + "Z",
        "model": f"{OPEN_METEO_MODEL_HD} + {OPEN_METEO_MODEL_STANDARD}",
        "first_hourly_time": run_reference_time,
        "hourly": records,
        "daily": {
            "time": daily.get("time", []),
            "sunrise": daily.get("sunrise", []),
            "sunset": daily.get("sunset", []),
        },
    }


if __name__ == "__main__":
    import json

    data = fetch_arome_forecast()
    print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
