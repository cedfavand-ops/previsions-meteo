"""
Recalibrage des prévisions AROME HD à partir des observations récentes.

Principe (MOS simplifié à biais glissant) :
1. Pour chaque variable à recalibrer (température, humidité, vent), on
   compare la prévision AROME et l'observation réelle sur les dernières
   heures (BIAS_WINDOW_HOURS).
2. On calcule un biais moyen = observation - prévision sur cette fenêtre.
3. On applique ce biais à la prévision future, avec une décroissance
   linéaire : 100% du biais à h+0, 0% au-delà de BIAS_DECAY_HOURS.
   Au-delà de cet horizon, la prévision AROME brute est conservée telle
   quelle (on considère qu'une erreur micro-locale ponctuelle n'a pas de
   raison de persister sur tout l'horizon de 36h).

La pluie n'est jamais recalibrée : on garde AROME brut, comme demandé.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional


def _parse_time(t: str) -> dt.datetime:
    """Parse un timestamp ISO, avec ou sans fuseau horaire."""
    t = t.replace("Z", "+00:00")
    return dt.datetime.fromisoformat(t)


def compute_bias(
    forecast_hourly: list[dict],
    observations: list[dict],
    forecast_field: str,
    obs_field: str,
    window_hours: int,
) -> Optional[float]:
    """Calcule le biais moyen (obs - prévision) sur les `window_hours`
    dernières heures pour lesquelles on a à la fois une observation et une
    valeur AROME à l'heure correspondante (on associe à l'heure ronde la
    plus proche).
    """
    if not observations:
        return None

    now = dt.datetime.now(dt.timezone.utc)
    window_start = now - dt.timedelta(hours=window_hours)

    recent_obs = [
        o for o in observations if o.get(obs_field) is not None and _parse_time(o["time"]) >= window_start
    ]
    if not recent_obs:
        return None

    # Index des prévisions AROME par heure ronde (clé: "YYYY-MM-DDTHH:00")
    fc_by_hour = {}
    for f in forecast_hourly:
        key = f["time"][:13]  # jusqu'à l'heure
        fc_by_hour[key] = f

    diffs = []
    for o in recent_obs:
        obs_hour_key = o["time"][:13]
        fc = fc_by_hour.get(obs_hour_key)
        if fc is None or fc.get(forecast_field) is None:
            continue
        diffs.append(o[obs_field] - fc[forecast_field])

    if not diffs:
        return None

    return sum(diffs) / len(diffs)


def apply_decaying_bias(
    forecast_hourly: list[dict],
    field: str,
    bias: Optional[float],
    decay_hours: int,
    out_field: str | None = None,
) -> None:
    """Applique en place un biais décroissant sur `field`, écrit le
    résultat dans `out_field` (par défaut : field + "_recalibre").
    Si bias est None, la valeur brute est simplement recopiée (pas de
    correction possible, ex : pas d'observation récente disponible).
    """
    target = out_field or f"{field}_recalibre"

    if bias is None:
        for f in forecast_hourly:
            f[target] = f[field]
        return

    for i, f in enumerate(forecast_hourly):
        # i correspond au nombre d'heures depuis le début de la série
        # (le premier point de la série AROME est censé être proche de
        # maintenant — voir fetch_arome.py).
        if i >= decay_hours:
            weight = 0.0
        else:
            weight = 1.0 - (i / decay_hours)
        f[target] = f[field] + bias * weight
