// Client-side weather via Open-Meteo (free, no key, CORS enabled).

const WEATHER_CODES = {
  0: { desc: "Jasno", icon: "☀️" },
  1: { desc: "Převážně jasno", icon: "🌤️" },
  2: { desc: "Polojasno", icon: "⛅" },
  3: { desc: "Zataženo", icon: "☁️" },
  45: { desc: "Mlha", icon: "🌫️" },
  48: { desc: "Mlha s námrazou", icon: "🌫️" },
  51: { desc: "Slabé mrholení", icon: "🌦️" },
  53: { desc: "Mrholení", icon: "🌦️" },
  55: { desc: "Silné mrholení", icon: "🌦️" },
  61: { desc: "Slabý déšť", icon: "🌧️" },
  63: { desc: "Déšť", icon: "🌧️" },
  65: { desc: "Silný déšť", icon: "🌧️" },
  71: { desc: "Slabé sněžení", icon: "🌨️" },
  73: { desc: "Sněžení", icon: "🌨️" },
  75: { desc: "Silné sněžení", icon: "❄️" },
  77: { desc: "Sněhová zrna", icon: "🌨️" },
  80: { desc: "Přeháňky", icon: "🌦️" },
  81: { desc: "Silné přeháňky", icon: "🌧️" },
  82: { desc: "Prudké přeháňky", icon: "🌧️" },
  85: { desc: "Sněhové přeháňky", icon: "🌨️" },
  86: { desc: "Silné sněhové přeháňky", icon: "❄️" },
  95: { desc: "Bouřka", icon: "⛈️" },
  96: { desc: "Bouřka s kroupami", icon: "⛈️" },
  99: { desc: "Silná bouřka s kroupami", icon: "⛈️" },
};

export function weatherInfo(code) {
  return WEATHER_CODES[code] || { desc: "—", icon: "🌡️" };
}

export async function fetchWeather(lat, lon) {
  const url = new URL("https://api.open-meteo.com/v1/forecast");
  url.search = new URLSearchParams({
    latitude: lat,
    longitude: lon,
    current: "temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m",
    hourly: "temperature_2m,weather_code,precipitation_probability",
    daily: "temperature_2m_max,temperature_2m_min,weather_code,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,sunrise,sunset",
    timezone: "Europe/Prague",
    forecast_days: 11,
  }).toString();
  const res = await fetch(url);
  if (!res.ok) throw new Error("weather fetch failed");
  return res.json();
}

// Split today's hourly data into morning / afternoon / evening averages.
export function splitTodayByPart(weather) {
  if (!weather || !weather.hourly) return null;
  const { time, temperature_2m, weather_code, precipitation_probability } = weather.hourly;
  const today = new Date().toISOString().slice(0, 10);
  const parts = {
    morning: { hours: [6, 7, 8, 9, 10, 11], samples: [] },
    afternoon: { hours: [12, 13, 14, 15, 16, 17], samples: [] },
    evening: { hours: [18, 19, 20, 21, 22], samples: [] },
  };
  for (let i = 0; i < time.length; i++) {
    const t = time[i];
    if (!t.startsWith(today)) continue;
    const hour = parseInt(t.slice(11, 13), 10);
    for (const [k, v] of Object.entries(parts)) {
      if (v.hours.includes(hour)) {
        v.samples.push({
          temp: temperature_2m[i],
          code: weather_code[i],
          precip: precipitation_probability ? precipitation_probability[i] : null,
        });
      }
    }
  }
  const summarize = samples => {
    if (!samples.length) return null;
    const temps = samples.map(s => s.temp);
    const codes = samples.map(s => s.code);
    const precips = samples.map(s => s.precip).filter(p => p != null);
    // Most common code
    const codeCount = {};
    for (const c of codes) codeCount[c] = (codeCount[c] || 0) + 1;
    const topCode = Number(Object.entries(codeCount).sort((a, b) => b[1] - a[1])[0][0]);
    return {
      temp_min: Math.round(Math.min(...temps)),
      temp_max: Math.round(Math.max(...temps)),
      temp_avg: Math.round(temps.reduce((a, b) => a + b, 0) / temps.length),
      weather_code: topCode,
      precip_max: precips.length ? Math.max(...precips) : 0,
    };
  };
  return {
    morning: summarize(parts.morning.samples),
    afternoon: summarize(parts.afternoon.samples),
    evening: summarize(parts.evening.samples),
  };
}

export async function searchCity(query) {
  if (!query || query.length < 2) return [];
  const url = new URL("https://geocoding-api.open-meteo.com/v1/search");
  url.search = new URLSearchParams({
    name: query,
    count: "8",
    language: "cs",
    format: "json",
  }).toString();
  const res = await fetch(url);
  if (!res.ok) return [];
  const data = await res.json();
  return (data.results || []).map(r => ({
    name: r.name,
    country: r.country,
    admin: r.admin1 || "",
    latitude: r.latitude,
    longitude: r.longitude,
  }));
}
