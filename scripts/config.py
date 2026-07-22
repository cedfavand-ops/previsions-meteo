"""
Configuration centrale du pipeline de prévisions.
Toutes les valeurs sensibles (clés API) sont lues depuis les variables
d'environnement / secrets GitHub Actions — jamais codées en dur ici.
"""

import os

# ---------------------------------------------------------------------------
# Station personnelle (température + humidité recalibrées) — Saint-Paul-les-Fonts
# ---------------------------------------------------------------------------
STATION_TEMP_HUMI = {
    "infoclimat_id": "000ZB",
    "name": "Saint-Paul-les-Fonts",
    "lat": 44.08,
    "lon": 4.61,
    "altitude_m": 80,
}

# ---------------------------------------------------------------------------
# Station voisine utilisée uniquement pour recalibrer le vent
# ---------------------------------------------------------------------------
STATION_WIND = {
    "infoclimat_id": "STATIC0451",
    "name": "Saint-Pons-la-Calm - La Gardie",
    # Coordonnées approximatives (à ajuster si besoin, voir la page
    # "Métadonnées" de la station sur infoclimat.fr) :
    "lat": 44.05,
    "lon": 4.42,
}

# Point de grille utilisé pour interroger AROME HD (on prend la station
# principale ; le point de grille AROME HD fait 1.3 km donc c'est la station
# temp/humidité qui doit primer ici).
AROME_LAT = STATION_TEMP_HUMI["lat"]
AROME_LON = STATION_TEMP_HUMI["lon"]

# ---------------------------------------------------------------------------
# Open-Meteo (accès libre, sans clé, aux runs AROME HD de Météo-France)
# ---------------------------------------------------------------------------
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_MODEL = "meteofrance_arome_france_hd"
OPEN_METEO_HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "weathercode",
    "windspeed_10m",
    "winddirection_10m",
    "windgusts_10m",
    "cloudcover",
]
OPEN_METEO_DAILY_VARS = ["sunrise", "sunset"]
TIMEZONE = "Europe/Paris"

# ---------------------------------------------------------------------------
# Infoclimat OpenData — nécessite un compte + une clé API générée pour
# l'adresse IP depuis laquelle tourne le script (voir README.md, section
# "Limitation IP Infoclimat").
# ---------------------------------------------------------------------------
INFOCLIMAT_API_KEY = os.environ.get("INFOCLIMAT_API_KEY", "")
# URL de base copiée depuis votre tableau de bord https://www.infoclimat.fr/opendata/
# une fois la clé générée (le format exact peut varier selon votre compte,
# d'où la variable d'environnement plutôt qu'une URL figée dans le code).
INFOCLIMAT_BASE_URL = os.environ.get(
    "INFOCLIMAT_BASE_URL", "https://www.infoclimat.fr/opendata/v1/station"
)

# ---------------------------------------------------------------------------
# Recalibrage (biais glissant)
# ---------------------------------------------------------------------------
# Nombre d'heures d'observations récentes utilisées pour calculer le biais
# (moyenne des écarts observation - prévision AROME sur cette fenêtre).
BIAS_WINDOW_HOURS = 3

# Durée sur laquelle la correction de biais s'estompe progressivement.
# À h+0 on applique 100% du biais, puis il décroît linéairement jusqu'à 0%
# à h+DECAY (au-delà, prévision AROME brute). Cela évite de "figer" une
# erreur locale ponctuelle sur tout l'horizon de 36h.
BIAS_DECAY_HOURS_TEMP_HUMI = 9
BIAS_DECAY_HOURS_WIND = 6

# ---------------------------------------------------------------------------
# Horizon de sortie
# ---------------------------------------------------------------------------
FORECAST_HOURS = 36

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "forecast.json"
)
