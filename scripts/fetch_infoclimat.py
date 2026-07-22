"""
Récupération des observations récentes via l'API OpenData d'Infoclimat.

IMPORTANT — lisez le README (section "Limitation IP Infoclimat") :
la clé API Infoclimat est générée pour une adresse IP donnée. Le format
exact de la requête peut aussi varier légèrement selon la formule proposée
sur votre tableau de bord https://www.infoclimat.fr/opendata/.

Pour éviter de coder en dur une URL qui pourrait ne pas correspondre
exactement à votre clé, ce module fonctionne en deux temps :

1. Si la variable d'environnement INFOCLIMAT_QUERY_TEMPLATE est définie,
   elle est utilisée telle quelle. Copiez-collez l'URL d'exemple générée
   sur votre tableau de bord Infoclimat, et remplacez les valeurs
   variables par les gabarits {station_id}, {start}, {end} :
   exemple :
   INFOCLIMAT_QUERY_TEMPLATE=
     "https://www.infoclimat.fr/opendata/v1/observations?token={token}"
     "&stations[]={station_id}&start={start}&end={end}&format=json"

2. Sinon, une URL par défaut "raisonnable" est construite — à valider vous
   même une première fois en local avant de compter dessus en automatique.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import requests

from config import INFOCLIMAT_API_KEY, INFOCLIMAT_BASE_URL

import os

DEFAULT_TEMPLATE = (
    INFOCLIMAT_BASE_URL
    + "?version=2&method=get&format=json&stations[]={station_id}&start={start}&end={end}&token={token}"
)


class InfoclimatFetchError(RuntimeError):
    pass


def _build_url(station_id: str, hours_back: int) -> str:
    # os.environ.get(..., default) ne revient PAS au défaut si la variable
    # existe mais est vide (ex. secret GitHub Actions non renseigné) : on
    # gère donc explicitement ce cas avec "or".
    template = os.environ.get("INFOCLIMAT_QUERY_TEMPLATE") or DEFAULT_TEMPLATE

    # L'API Infoclimat attend des dates simples (AAAA-MM-JJ), pas des
    # horodatages précis. On remonte d'au moins 1 jour complet pour être
    # sûr de couvrir les `hours_back` dernières heures même si l'exécution
    # a lieu tôt le matin.
    end_date = dt.datetime.utcnow().date()
    days_back = max(1, (hours_back // 24) + 1)
    start_date = end_date - dt.timedelta(days=days_back)

    return template.format(
        token=INFOCLIMAT_API_KEY,
        station_id=station_id,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
    )


def fetch_station_observations(station_id: str, hours_back: int = 6) -> list[dict[str, Any]]:
    """Renvoie une liste d'observations triées du plus ancien au plus récent :
    [{"time": "...", "temperature": .., "humidity": .., "wind_speed": ..,
      "wind_gust": .., "wind_direction": ..}, ...]
    Les champs non fournis par la station restent absents du dict.
    """
    if not INFOCLIMAT_API_KEY:
        raise InfoclimatFetchError(
            "INFOCLIMAT_API_KEY n'est pas définie (variable d'environnement / secret GitHub)."
        )

    url = _build_url(station_id, hours_back)
    try:
        resp = requests.get(url, timeout=30)
    except requests.exceptions.RequestException as e:
        # Panne réseau, timeout, DNS, etc. : traité comme une indisponibilité
        # normale de la station plutôt qu'un plantage du script — le run
        # continue avec les prévisions AROME brutes pour cette variable.
        raise InfoclimatFetchError(
            f"Impossible de contacter Infoclimat pour la station {station_id} : {e}"
        ) from e

    if resp.status_code != 200:
        raise InfoclimatFetchError(
            f"Infoclimat a répondu {resp.status_code} pour la station {station_id}: "
            f"{resp.text[:300]}"
        )

    payload = resp.json()
    return _normalize_payload(payload, station_id)


def _normalize_payload(payload: Any, station_id: str) -> list[dict[str, Any]]:
    """Adapte différentes formes de réponse JSON possibles vers un format
    interne homogène. À ajuster si la structure réelle de votre compte
    diffère (regardez simplement `print(payload)` une première fois en
    local et adaptez cette fonction en conséquence)."""

    records: list[dict[str, Any]] = []

    # Forme 1 : {"hourly": [...]} directement, ou liste brute
    candidates = None
    if isinstance(payload, dict):
        if "hourly" in payload:
            candidates = payload["hourly"]
        elif station_id in payload and isinstance(payload[station_id], dict):
            # Format confirmé de l'API Infoclimat (method=get&version=2) :
            # {"000ZB": {"hourly": [...]}, ...}
            candidates = payload[station_id].get("hourly")
        elif station_id in payload:
            candidates = payload[station_id]
        elif "data" in payload:
            candidates = payload["data"]
    elif isinstance(payload, list):
        candidates = payload

    if candidates is None:
        raise InfoclimatFetchError(
            "Structure de réponse Infoclimat non reconnue — adaptez "
            "_normalize_payload() dans fetch_infoclimat.py. Réponse brute : "
            f"{str(payload)[:500]}"
        )

    # Le format "hourly" peut être soit une liste d'observations (une par
    # heure), soit un format "en colonnes" (un dict de listes parallèles,
    # ex. {"dh_utc": [...], "temperature": [...], ...}). On détecte et
    # convertit ce 2e cas vers une liste de dicts pour traiter les deux
    # de façon identique ensuite.
    if isinstance(candidates, dict):
        keys = list(candidates.keys())
        length = len(candidates[keys[0]]) if keys else 0
        candidates = [
            {k: candidates[k][i] for k in keys if i < len(candidates[k])}
            for i in range(length)
        ]

    for item in candidates:
        # On tente plusieurs noms de champs courants selon les versions de l'API
        rec = {
            "time": item.get("dh_utc") or item.get("date") or item.get("time"),
            "temperature": _first_present(item, ["temperature", "temp", "t"]),
            "humidity": _first_present(item, ["humidite", "humidity", "hr"]),
            "wind_speed": _first_present(item, ["vent_moyen", "wind_speed", "wind_avg"]),
            "wind_gust": _first_present(item, ["vent_rafales", "wind_gust"]),
            "wind_direction": _first_present(item, ["vent_direction", "wind_direction"]),
        }
        if rec["time"]:
            records.append(rec)

    records.sort(key=lambda r: r["time"])
    return records


def _first_present(d: dict, keys: list[str]):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            try:
                return float(d[k])
            except (TypeError, ValueError):
                return d[k]
    return None


if __name__ == "__main__":
    import json
    from config import STATION_TEMP_HUMI

    obs = fetch_station_observations(STATION_TEMP_HUMI["infoclimat_id"], hours_back=6)
    print(json.dumps(obs, indent=2, ensure_ascii=False))
