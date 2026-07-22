// ---------------------------------------------------------------------------
// Pictogrammes meteoblue — images hébergées directement chez meteoblue,
// d'après la table officielle "Day and night pictograms" (1-35) publiée sur
// https://content.meteoblue.com/en/research-education/specifications/standards/symbols-and-pictograms
// Aucun téléchargement/dézippage n'est nécessaire : ce sont des liens
// directs vers des fichiers PNG individuels. L'usage gratuit est autorisé
// à condition de conserver un lien vers meteoblue (déjà présent en pied de
// page d'index.html).
// ---------------------------------------------------------------------------
const PICTO_BASE = "https://content.meteoblue.com/assets/images/graphics/pictos";

// Numéro du pictogramme (1-35) pour chaque catégorie sémantique produite
// par scripts/weather_icons.py
const CATEGORY_TO_NUMBER = {
  clear: 1,
  mostly_clear: 2,
  partly_cloudy: 7,
  overcast: 22,
  fog: 16,
  fog_rime: 16,
  drizzle_light: 33,
  drizzle: 33,
  drizzle_heavy: 23,
  drizzle_freezing: 23,
  rain_light: 33,
  rain: 23,
  rain_heavy: 25,
  rain_freezing: 25,
  snow_light: 34,
  snow: 24,
  snow_heavy: 26,
  snow_grains: 24,
  showers_light: 31,
  showers: 31,
  showers_heavy: 31,
  snow_showers_light: 32,
  snow_showers_heavy: 32,
  thunderstorm: 27,
  thunderstorm_hail: 30,
  unknown: 19,
};

// Nom de fichier exact jour/nuit pour chaque numéro (la plupart suivent
// "NN_day.png" / "NN_night.png", quelques-uns ont un suffixe descriptif).
const PICTO_FILES = {
  1: { day: "01_day_cloudless.png", night: "01_night_cloudless.png" },
  2: { day: "02_day_cirrus.png", night: "02_night_cirrus.png" },
  3: { day: "03_day_cirrocumulus.png", night: "03_night.png" },
  4: { day: "04_day.png", night: "04_night.png" },
  5: { day: "05_day.png", night: "05_night.png" },
  6: { day: "06_day_altrostratus_3.png", night: "06_night.png" },
  7: { day: "07_day_altocumulus.png", night: "07_night.png" },
  8: { day: "08_day_cumulus_3.png", night: "08_night.png" },
  9: { day: "09_day_altostratus_2.png", night: "09_night.png" },
  10: { day: "10_day.png", night: "10_night.png" },
  11: { day: "11_day.png", night: "11_night.png" },
  12: { day: "12_day.png", night: "12_night.png" },
  13: { day: "13_day_stratus.png", night: "13_night.png" },
  14: { day: "14_day.png", night: "14_night.png" },
  15: { day: "15_day_altrostratus_1.png", night: "15_night.png" },
  16: { day: "16_day.png", night: "16_night.png" },
  17: { day: "17_day.png", night: "17_night.png" },
  18: { day: "18_day.png", night: "18_night.png" },
  19: { day: "19_day.png", night: "19_night.png" },
  20: { day: "20_day_cumulus_2.png", night: "20_night.png" },
  21: { day: "21_day.png", night: "21_night.png" },
  22: { day: "22_day.png", night: "22_night.png" },
  23: { day: "23_day.png", night: "23_night.png" },
  24: { day: "24_day_nimbostratus_6.png", night: "24_night.png" },
  25: { day: "25_day_nimbostratus_2.png", night: "25_night.png" },
  26: { day: "26_day.png", night: "26_night.png" },
  27: { day: "27_day.png", night: "27_night.png" },
  28: { day: "28_day_cumulonimbus_2.png", night: "28_night.png" },
  29: { day: "29_day_nimbostratus_5.png", night: "29_night.png" },
  30: { day: "30_day_cumulomimbus_3.png", night: "30_night.png" },
  31: { day: "31_day.png", night: "31_night.png" },
  32: { day: "32_day.png", night: "32_night.png" },
  33: { day: "33_day_nimbostratus_1.png", night: "33_night.png" },
  34: { day: "34_day_nimbostratus_4.png", night: "34_night.png" },
  35: { day: "35_day.png", night: "35_night.png" },
};

function iconUrl(category, isDay) {
  const number = CATEGORY_TO_NUMBER[category] ?? CATEGORY_TO_NUMBER.unknown;
  const files = PICTO_FILES[number];
  const folder = isDay ? "day" : "night";
  const file = isDay ? files.day : files.night;
  return `${PICTO_BASE}/${folder}/${file}`;
}

function formatHour(isoTime) {
  // "2026-07-21T14:00" -> "14h"
  return isoTime.slice(11, 13) + "h";
}

function formatFullTime(isoTime) {
  const d = new Date(isoTime);
  return d.toLocaleString("fr-FR", {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function loadForecast() {
  const res = await fetch("data/forecast.json", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Impossible de charger data/forecast.json (${res.status})`);
  }
  return res.json();
}

function renderRunInfo(data) {
  const el = document.getElementById("run-info");
  el.textContent = `AROME HD — dernières données dispo. à partir de ${formatFullTime(
    data.arome_first_hourly_time
  )}`;

  const gen = document.getElementById("generated-at");
  gen.textContent = `Page générée le ${formatFullTime(data.generated_at)}`;
}

function renderTnTx(data) {
  if (data.tn_tonight) {
    document.getElementById("tn-value").textContent = `${data.tn_tonight.value}°C`;
    document.getElementById("tn-time").textContent = formatFullTime(data.tn_tonight.time);
  }
  if (data.tx_tomorrow) {
    document.getElementById("tx-value").textContent = `${data.tx_tomorrow.value}°C`;
    document.getElementById("tx-time").textContent = formatFullTime(data.tx_tomorrow.time);
  }
}

function renderWarnings(data) {
  const el = document.getElementById("warnings");
  if (data.warnings && data.warnings.length > 0) {
    el.hidden = false;
    el.textContent = data.warnings.join(" · ");
  }
}

function renderHourlyStrip(data) {
  const container = document.getElementById("hourly-strip");
  container.innerHTML = "";

  data.hourly.forEach((h) => {
    const item = document.createElement("div");
    item.className = "hour-item";

    const time = document.createElement("div");
    time.className = "h-time";
    time.textContent = formatHour(h.time);

    const icon = document.createElement("img");
    icon.className = "h-icon";
    icon.src = iconUrl(h.icon_category, h.is_day);
    icon.alt = h.icon_category.replace(/_/g, " ");
    icon.loading = "lazy";

    const temp = document.createElement("div");
    temp.className = "h-temp";
    temp.textContent = `${Math.round(h.temperature)}°`;

    const precip = document.createElement("div");
    precip.className = "h-precip";
    precip.textContent = h.precipitation > 0 ? `${h.precipitation.toFixed(1)}mm` : "";

    item.append(time, icon, temp, precip);
    container.appendChild(item);
  });
}

function renderChart(data) {
  const ctx = document.getElementById("temp-chart");
  const labels = data.hourly.map((h) => formatHour(h.time));
  const temps = data.hourly.map((h) => h.temperature);

  new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Température recalibrée (°C)",
          data: temps,
          borderColor: "#3E6FA6",
          backgroundColor: "rgba(62, 111, 166, 0.08)",
          fill: true,
          tension: 0.35,
          pointRadius: 2,
          pointHoverRadius: 5,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (item) => ` ${item.parsed.y.toFixed(1)}°C`,
          },
        },
      },
      scales: {
        x: {
          ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 12 },
          grid: { display: false },
        },
        y: {
          ticks: { callback: (v) => `${v}°` },
          grid: { color: "rgba(0,0,0,0.06)" },
        },
      },
    },
  });
}

async function init() {
  try {
    const data = await loadForecast();
    renderRunInfo(data);
    renderTnTx(data);
    renderWarnings(data);
    renderHourlyStrip(data);
    renderChart(data);
  } catch (err) {
    document.getElementById("hourly-strip").innerHTML =
      `<p class="loading">Erreur de chargement : ${err.message}</p>`;
  }
}

init();
