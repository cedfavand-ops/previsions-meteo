"""
Récupération des prévisions AROME HD (Météo-France) via l'API Open-Meteo.

Open-Meteo republie librement (sans clé) les sorties du modèle AROME HD
(résolution 1.3 km) sous le nom de modèle "meteofrance_arome_france_hd".
On force explicitement ce modèle (plutôt que l'endpoint /v1/meteofrance
qui peut mélanger AROME/ARPEGE selon la zone) pour être certain de bien
utiliser le dernier run disponible (le run 12z, une fois ingéré, quelques
heures après 12h TU).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import requests

from config import (
    AROME_LAT,
    AROME_LON,
    OPEN_METEO_URL,
    OPEN_METEO_MODEL,
    OPEN_METEO_HOURLY_VARS,
    OPEN_METEO_DAILY_VARS,
    TIMEZONE,
)


class AromeFetchError(RuntimeError):
    pass


def fetch_arome_forecast() -> dict[str, Any]:
    """Interroge Open-Meteo pour le point de grille AROME HD le plus proche
    de la station, et renvoie un dict structuré heure par heure.
    """
    params = {
        "latitude": AROME_LAT,
        "longitude": AROME_LON,
        "hourly": ",".join(OPEN_METEO_HOURLY_VARS),
        "daily": ",".join(OPEN_METEO_DAILY_VARS),
        "models": OPEN_METEO_MODEL,
        "timezone": TIMEZONE,
        "forecast_days": 3,
    }

    resp = requests.get(OPEN_METEO_URL, params=params, timeout=30)
    if resp.status_code != 200:
        raise AromeFetchError(
            f"Open-Meteo a répondu {resp.status_code}: {resp.text[:300]}"
        )

    payload = resp.json()

    if "hourly" not in payload:
        raise AromeFetchError(f"Réponse Open-Meteo inattendue: {payload}")

    hourly = payload["hourly"]
    times = hourly["time"]

    # Vérification rapide de fraîcheur du run : le premier "time" doit être
    # proche de maintenant. On ne peut pas obtenir directement l'heure du
    # run depuis cette API (elle sert toujours le dernier run disponible),
    # donc on se contente de logger l'heure de première valeur pour audit.
    run_reference_time = times[0]

    records = []
    n = len(times)
    for i in range(n):
        temp = hourly["temperature_2m"][i]
        code = hourly["weathercode"][i]
        # Au-delà de l'horizon réellement couvert par AROME HD, Open-Meteo
        # peut renvoyer `null` pour certaines heures du calendrier demandé :
        # on les ignore plutôt que de planter plus loin dans le pipeline.
        if temp is None or code is None:
            continue
        records.append(
            {
                "time": times[i],
                "temperature_2m": temp,
                "relative_humidity_2m": hourly["relative_humidity_2m"][i],
                "precipitation": hourly["precipitation"][i],
                "weathercode": code,
                "windspeed_10m": hourly["windspeed_10m"][i],
                "winddirection_10m": hourly["winddirection_10m"][i],
                "windgusts_10m": hourly["windgusts_10m"][i],
                "cloudcover": hourly["cloudcover"][i],
            }
        )

    daily = payload.get("daily", {})

    return {
        "fetched_at": dt.datetime.utcnow().isoformat() + "Z",
        "model": OPEN_METEO_MODEL,
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
