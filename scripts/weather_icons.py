"""
Traduit un code météo WMO (renvoyé par Open-Meteo, table OMM 4677) en une
catégorie sémantique de pictogramme. Le choix jour/nuit est géré séparément
côté front-end (assets/app.js) à partir du champ `is_day` déjà présent dans
chaque heure du JSON — les pictogrammes meteoblue existant en version
jour ET nuit pour les 35 situations, il n'y a pas besoin de le gérer ici.

La correspondance catégorie -> numéro de pictogramme meteoblue (1-35) et
les noms de fichiers exacts sont définis dans assets/app.js (PICTO_FILES),
d'après la table officielle publiée sur
https://content.meteoblue.com/en/research-education/specifications/standards/symbols-and-pictograms
"""

from __future__ import annotations

# Table de correspondance code WMO -> catégorie sémantique
_WMO_TO_CATEGORY = {
    0: "clear",
    1: "mostly_clear",
    2: "partly_cloudy",
    3: "overcast",
    45: "fog",
    48: "fog_rime",
    51: "drizzle_light",
    53: "drizzle",
    55: "drizzle_heavy",
    56: "drizzle_freezing",
    57: "drizzle_freezing",
    61: "rain_light",
    63: "rain",
    65: "rain_heavy",
    66: "rain_freezing",
    67: "rain_freezing",
    71: "snow_light",
    73: "snow",
    75: "snow_heavy",
    77: "snow_grains",
    80: "showers_light",
    81: "showers",
    82: "showers_heavy",
    85: "snow_showers_light",
    86: "snow_showers_heavy",
    95: "thunderstorm",
    96: "thunderstorm_hail",
    99: "thunderstorm_hail",
}

def category_for(weathercode: int) -> str:
    return _WMO_TO_CATEGORY.get(int(weathercode), "unknown")
