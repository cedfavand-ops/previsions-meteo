# Prévisions AROME HD recalibrées — Saint-Paul-les-Fonts

Page de prévisions météo à court terme (36h), basée sur les sorties du
modèle **AROME HD** de Météo-France (run 12z), recalibrées à partir des
observations de la station personnelle de Saint-Paul-les-Fonts (température,
humidité) et de la station voisine de Saint-Pons-la-Calm–La Gardie (vent).
La pluie reste la prévision AROME brute.

## 1. Mettre en ligne sur GitHub Pages

1. Poussez ce contenu dans votre dépôt (branche `main`).
2. Dans **Settings → Pages**, choisissez la branche `main` et le dossier
   racine (`/`).
3. Votre page sera disponible à `https://<votre-compte>.github.io/<repo>/`.

Au premier déploiement, `data/forecast.json` n'existe pas encore : générez-le
une première fois en local (étape 4) et commitez-le, sinon la page affichera
une erreur de chargement.

## 2. Pictogrammes meteoblue

Rien à télécharger : `assets/app.js` pointe directement vers les images
individuelles hébergées par meteoblue (table officielle "Day and night
pictograms", 35 situations, sur
<https://content.meteoblue.com/en/research-education/specifications/standards/symbols-and-pictograms>).
La licence meteoblue autorise cet usage gratuit à condition de conserver un
lien vers meteoblue — c'est déjà fait dans le pied de page (`index.html`).

Si meteoblue change un jour ces URLs ou que vous préférez héberger les
images vous-même (pour ne pas dépendre de leur disponibilité), la
correspondance catégorie → fichier se trouve entièrement dans
`PICTO_FILES` et `CATEGORY_TO_NUMBER` en haut de `assets/app.js` — il
suffit d'adapter `PICTO_BASE` vers votre propre dossier `assets/icons/`
une fois les fichiers téléchargés individuellement depuis les liens du
tableau meteoblue ci-dessus.

## 3. Configurer l'accès à l'API Infoclimat

1. Connectez-vous sur <https://www.infoclimat.fr/opendata/> et générez une
   clé API si ce n'est pas déjà fait — vous avez indiqué en avoir déjà une.
2. **Point important : la clé est associée à une adresse IP précise.**
   Repérez sur votre tableau de bord Infoclimat l'URL d'exemple générée pour
   vos stations (000ZB et STATIC0451) — elle contient le format exact de
   requête propre à votre compte.
3. Dans les **Settings → Secrets and variables → Actions** de votre dépôt
   GitHub, créez :
   - `INFOCLIMAT_API_KEY` : votre clé API.
   - `INFOCLIMAT_QUERY_TEMPLATE` (optionnel mais recommandé) : collez l'URL
     d'exemple de votre tableau de bord, en remplaçant les parties variables
     par `{token}`, `{station_id}`, `{start}`, `{end}` — voir les
     commentaires en tête de `scripts/fetch_infoclimat.py` pour un exemple.
4. Testez en local avant de compter sur l'automatisation (voir étape 4).

### ⚠️ Limitation IP — lisez avant de configurer l'automatisation

Les clés Infoclimat étant liées à une IP, les runners **GitHub-hosted**
classiques (`ubuntu-latest`) ne fonctionneront pas : leur IP change à chaque
exécution et ne correspond jamais à celle enregistrée chez Infoclimat.

Deux solutions :

- **Recommandée** : installez un *self-hosted runner* GitHub Actions sur une
  machine chez vous qui a une IP stable (celle enregistrée sur Infoclimat) —
  un Raspberry Pi ou un NAS suffit largement. Le workflow fourni
  (`.github/workflows/update-forecast.yml`) est déjà configuré pour
  `runs-on: self-hosted`. Procédure : dans votre dépôt, **Settings → Actions
  → Runners → New self-hosted runner**, puis suivez les 4 commandes
  affichées (télécharger, configurer, lancer). Laissez-le tourner en
  arrière-plan (ou en service systemd) sur votre machine.
- **Alternative** : faites tourner `scripts/build_forecast.py` via une tâche
  cron sur votre propre machine/box, puis laissez le script faire
  `git add / commit / push` lui-même (pas besoin de GitHub Actions pour la
  partie fetch, uniquement pour publier). Un exemple de cron :
  ```
  30 15 * * * cd /chemin/vers/le/depot && python3 scripts/build_forecast.py && git commit -am "update" && git push
  ```

## 4. Tester en local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export INFOCLIMAT_API_KEY="votre_clé"
export INFOCLIMAT_QUERY_TEMPLATE="..."   # si nécessaire, voir étape 3

python scripts/build_forecast.py
```

Si tout se passe bien, `data/forecast.json` est généré. Ouvrez `index.html`
avec un petit serveur local (`python -m http.server`, sinon `fetch()` sera
bloqué par la politique CORS des fichiers `file://`) et vérifiez le rendu.

## 5. Calage horaire du run 12z

Le workflow est programmé à 15h30 UTC. Open-Meteo republie AROME HD
généralement quelques heures après l'heure du run ; ce délai peut varier.
Après quelques jours, comparez `arome_first_hourly_time` (affiché en haut de
la page) aux horaires réels de disponibilité du run 12z, et ajustez le
`cron` dans `.github/workflows/update-forecast.yml` si besoin. Vous pouvez
aussi déclencher une génération manuelle à tout moment depuis l'onglet
**Actions → Mise à jour prévisions (run 12z) → Run workflow**.

## 6. Ajuster le recalibrage

Dans `scripts/config.py` :

- `BIAS_WINDOW_HOURS` : nombre d'heures d'observations récentes utilisées
  pour calculer le biais (3h par défaut).
- `BIAS_DECAY_HOURS_TEMP_HUMI` / `BIAS_DECAY_HOURS_WIND` : sur combien
  d'heures la correction s'estompe progressivement avant de revenir à
  AROME brut (9h pour temp/humidité, 6h pour le vent par défaut).

## Structure du dépôt

```
.
├── .github/workflows/update-forecast.yml   # automatisation (self-hosted runner)
├── scripts/
│   ├── config.py            # coordonnées stations, paramètres de recalibrage
│   ├── fetch_arome.py       # prévisions AROME HD via Open-Meteo
│   ├── fetch_infoclimat.py  # observations stations Infoclimat
│   ├── bias_correction.py   # biais glissant avec décroissance
│   ├── weather_icons.py     # code météo -> catégorie de pictogramme
│   └── build_forecast.py    # orchestrateur -> data/forecast.json
├── data/forecast.json       # généré (ne pas éditer à la main)
├── assets/
│   ├── style.css
│   └── app.js                # inclut PICTO_FILES : liens directs vers les pictogrammes meteoblue
└── index.html
```
