import { startWeatherBg } from "./weather-bg.js";
import { fetchWeather, searchCity, weatherInfo, splitTodayByPart } from "./weather.js";
import { saveArticle, unsaveArticle, getSavedIds, getAllSaved } from "./storage.js";
import { renderCOT } from "./cot.js";

const DEFAULT_CITY = { name: "Liberec", country: "Česko", latitude: 50.7663, longitude: 15.0543 };
const TABS = [
  { id: "world", label: "Svět" },
  { id: "czech", label: "Česko" },
  { id: "sport", label: "Sport" },
  { id: "tech", label: "Technologie" },
  { id: "culture", label: "Kultura" },
  { id: "good_news", label: "Good News" },
  { id: "lesson", label: "Naučit se" },
  { id: "joke", label: "Vtip" },
  { id: "quote", label: "Citát" },
  { id: "cot", label: "COT" },
];

const SECONDARY_TABS = [
  { id: "saved", label: "Uloženo", icon: "★", title: "Uloženo" },
  { id: "settings", label: "Nastavení", icon: "⚙", title: "Nastavení" },
];

const CZ_DAY_SHORT = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"];
const CZ_MONTHS_GEN = ["ledna","února","března","dubna","května","června","července","srpna","září","října","listopadu","prosince"];

const SUBSECTIONS = {
  sport: [
    { key: "football", label: "Fotbal" },
    { key: "hockey", label: "Hokej" },
    { key: "tennis", label: "Tenis" },
    { key: "f1", label: "F1" },
  ],
  tech: [
    { key: "ai", label: "AI novinky" },
    { key: "startups", label: "Startupy & funding" },
    { key: "robotics", label: "Robotika" },
  ],
  culture: [
    { key: "music", label: "Hudba" },
    { key: "film", label: "Film" },
    { key: "linkin_park", label: "Linkin Park" },
    { key: "oasis", label: "Oasis" },
  ],
};

const WEATHER_REFRESH_MS = 30 * 60 * 1000; // 30 min

const state = {
  data: null,
  activeTab: "world",
  savedIds: new Set(),
  city: null,
  weather: null,
  stopBg: null,
  infoPanelOpen: false,
  weatherTimer: null,
};

// -------------------- DATA LOADING --------------------

async function loadData() {
  const res = await fetch("data.json", { cache: "no-cache" });
  if (!res.ok) throw new Error(`data.json: ${res.status}`);
  return res.json();
}

// -------------------- SETTINGS --------------------

function loadCity() {
  try {
    const raw = localStorage.getItem("jn:city");
    if (raw) return JSON.parse(raw);
  } catch {}
  return DEFAULT_CITY;
}

function saveCity(city) {
  localStorage.setItem("jn:city", JSON.stringify(city));
}

// -------------------- ESCAPE --------------------

function escape(s) {
  return String(s || "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// -------------------- RENDER TOP BAR + WEATHER --------------------

function renderTopBar() {
  const data = state.data;
  const weather = state.weather;

  document.getElementById("day-name").textContent = data.today.day_name;
  document.getElementById("date-text").textContent = data.today.date_cz;
  document.getElementById("week-info").textContent =
    `${data.today.week_parity} týden (${data.today.week_number})`;

  document.getElementById("nameday").textContent = data.nameday || "—";

  const holidays = parseHolidays(data.world_holiday);
  document.getElementById("world-holiday-main").textContent = holidays[0] || "—";

  const list = document.getElementById("world-holiday-list");
  list.innerHTML = "";
  if (holidays.length) {
    for (const h of holidays) {
      const li = document.createElement("li");
      li.className = "info-panel__list-item";
      li.textContent = h;
      list.appendChild(li);
    }
  } else {
    const li = document.createElement("li");
    li.className = "info-panel__list-item info-panel__list-item--empty";
    li.textContent = "Žádný mezinárodní den není dnes zaznamenán.";
    list.appendChild(li);
  }

  const wEl = document.getElementById("weather-compact");
  wEl.onclick = () => setActiveTab("weather_10d");
  wEl.classList.toggle("weather-chip--active", state.activeTab === "weather_10d");
  if (weather && weather.current) {
    const info = weatherInfo(weather.current.weather_code);
    wEl.innerHTML = `
      <span class="weather-chip__icon">${info.icon}</span>
      <span class="weather-chip__temp">${Math.round(weather.current.temperature_2m)}°</span>
      <span class="weather-chip__city">${escape(state.city.name)}</span>
    `;
  } else {
    wEl.textContent = state.city ? state.city.name : "—";
  }

  const btn = document.getElementById("info-toggle");
  btn.onclick = toggleInfoPanel;
  const panel = document.getElementById("info-panel");
  panel.hidden = !state.infoPanelOpen;
  btn.setAttribute("aria-expanded", String(state.infoPanelOpen));
  btn.classList.toggle("chip--open", state.infoPanelOpen);

  renderWeatherStrip();
}

function parseHolidays(raw) {
  if (!raw) return [];
  return raw.split(/\s+·\s+/).map(s => s.trim()).filter(Boolean);
}

function toggleInfoPanel() {
  state.infoPanelOpen = !state.infoPanelOpen;
  const panel = document.getElementById("info-panel");
  const btn = document.getElementById("info-toggle");
  panel.hidden = !state.infoPanelOpen;
  btn.setAttribute("aria-expanded", String(state.infoPanelOpen));
  btn.classList.toggle("chip--open", state.infoPanelOpen);
}

function renderWeatherStrip() {
  const strip = document.getElementById("weather-strip");
  if (!strip) return;
  const w = state.weather;
  if (!w) { strip.innerHTML = ""; return; }
  const parts = splitTodayByPart(w);
  if (!parts) { strip.innerHTML = ""; return; }

  const tile = (label, p) => {
    if (!p) {
      return `
        <div class="weather-strip__tile weather-strip__tile--empty">
          <span class="weather-strip__label">${label}</span>
          <span class="weather-strip__temp">—</span>
        </div>`;
    }
    const info = weatherInfo(p.weather_code);
    const tempText = p.temp_min === p.temp_max ? `${p.temp_max}°` : `${p.temp_min}–${p.temp_max}°`;
    const precip = p.precip_max != null && p.precip_max > 0
      ? `<span class="weather-strip__precip" title="Pravděpodobnost srážek">💧${p.precip_max}%</span>`
      : "";
    return `
      <div class="weather-strip__tile">
        <span class="weather-strip__label">${label}</span>
        <span class="weather-strip__icon" title="${escape(info.desc)}">${info.icon}</span>
        <span class="weather-strip__temp" title="Rozmezí teplot (min–max)">${tempText}</span>
        ${precip}
      </div>`;
  };

  strip.innerHTML = `
    ${tile("Ráno", parts.morning)}
    ${tile("Odpoledne", parts.afternoon)}
    ${tile("Večer", parts.evening)}
  `;
}

// -------------------- TABS --------------------

function renderTabs() {
  const nav = document.getElementById("tabs-nav");
  nav.innerHTML = "";
  for (const t of TABS) {
    const btn = document.createElement("button");
    btn.className = "tab" + (state.activeTab === t.id ? " tab--active" : "");
    btn.textContent = t.label;
    btn.onclick = () => setActiveTab(t.id);
    nav.appendChild(btn);
  }
  const active = nav.querySelector(".tab--active");
  if (active) active.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  renderDock();
}

function renderDock() {
  const dock = document.getElementById("dock");
  if (!dock) return;
  dock.innerHTML = "";
  for (const t of SECONDARY_TABS) {
    const btn = document.createElement("button");
    btn.className = "dock__btn" + (state.activeTab === t.id ? " dock__btn--active" : "");
    btn.title = t.title;
    btn.setAttribute("aria-label", t.title);
    btn.innerHTML = `<span class="dock__icon">${t.icon}</span><span class="dock__label">${escape(t.label)}</span>`;
    btn.onclick = () => setActiveTab(t.id);
    dock.appendChild(btn);
  }
}

function setActiveTab(id) {
  if (state.activeTab === id) return;
  state.activeTab = id;
  const wEl = document.getElementById("weather-compact");
  if (wEl) wEl.classList.toggle("weather-chip--active", id === "weather_10d");
  renderTabs();
  renderContent();
}

function switchTabBy(delta) {
  const idx = TABS.findIndex(t => t.id === state.activeTab);
  const next = (idx + delta + TABS.length) % TABS.length;
  setActiveTab(TABS[next].id);
}

// -------------------- ARTICLES --------------------

function formatDate(iso) {
  try {
    const d = new Date(iso);
    const pad = n => String(n).padStart(2, "0");
    return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}. ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch { return ""; }
}

function articleEl(a) {
  const el = document.createElement("article");
  el.className = "article";
  const saved = state.savedIds.has(a.id);
  el.innerHTML = `
    <h2 class="article__title">
      <a href="${a.link}" target="_blank" rel="noopener noreferrer">${escape(a.title_cs || a.title)}</a>
    </h2>
    ${a.summary_cs ? `<p class="article__summary">${escape(a.summary_cs)}</p>` : ""}
    <div class="article__footer">
      <div class="article__meta">
        <span class="article__source">${escape(a.source)}</span>
        <span class="article__date">${formatDate(a.published)}</span>
      </div>
      <div class="article__actions">
        <button class="btn-save ${saved ? "btn-save--saved" : ""}">${saved ? "★ Uloženo" : "☆ Uložit"}</button>
      </div>
    </div>
  `;
  el.querySelector(".btn-save").onclick = () => toggleSave({ ...a, _type: "article" });
  return el;
}

async function toggleSave(item) {
  if (state.savedIds.has(item.id)) {
    await unsaveArticle(item.id);
    state.savedIds.delete(item.id);
  } else {
    await saveArticle(item);
    state.savedIds.add(item.id);
  }
  renderContent();
}

function renderArticleList(articles, container, subsection) {
  if (!articles.length) {
    container.innerHTML = `<div class="empty">Žádné články pro dnešek.</div>`;
    return;
  }
  if (subsection) {
    const groups = {};
    for (const sub of subsection) groups[sub.key] = [];
    for (const a of articles) {
      if (groups[a.sub]) groups[a.sub].push(a);
      else (groups._other = groups._other || []).push(a);
    }
    for (const sub of subsection) {
      if (!groups[sub.key] || !groups[sub.key].length) continue;
      const h = document.createElement("div");
      h.className = "subsection";
      h.textContent = sub.label;
      container.appendChild(h);
      for (const a of groups[sub.key]) container.appendChild(articleEl(a));
    }
    if (groups._other && groups._other.length) {
      const h = document.createElement("div");
      h.className = "subsection";
      h.textContent = "Další";
      container.appendChild(h);
      for (const a of groups._other) container.appendChild(articleEl(a));
    }
  } else {
    for (const a of articles) container.appendChild(articleEl(a));
  }
}

// -------------------- JOKE / QUOTE --------------------

function jokeCardEl(joke, lang) {
  const saved = state.savedIds.has(joke.id);
  const div = document.createElement("div");
  div.className = "centered-card";
  div.innerHTML = `
    <div class="centered-card__heading">${lang === "cs" ? "Český vtip" : "English joke"}</div>
    <div class="centered-card__text">${escape(joke.text || "—")}</div>
    <div class="centered-card__footer">
      <div class="centered-card__source">Zdroj: ${joke.source_url
        ? `<a href="${escape(joke.source_url)}" target="_blank" rel="noopener">${escape(joke.source || "—")}</a>`
        : escape(joke.source || "—")}</div>
      <button class="btn-save ${saved ? "btn-save--saved" : ""}">${saved ? "★ Uloženo" : "☆ Uložit"}</button>
    </div>
  `;
  div.querySelector(".btn-save").onclick = () =>
    toggleSave({ ...joke, _type: "joke", _lang: lang });
  return div;
}

function renderJoke(data, container) {
  container.appendChild(jokeCardEl(data.joke_cs || {}, "cs"));
  container.appendChild(jokeCardEl(data.joke_en || {}, "en"));
}

function quoteCardEl(q) {
  const saved = q.id && state.savedIds.has(q.id);
  const div = document.createElement("div");
  div.className = "centered-card";
  div.innerHTML = `
    <div class="centered-card__heading">Citát dne</div>
    <div class="centered-card__text centered-card__text--quote">„${escape(q.text || "—")}"</div>
    <div class="centered-card__author">— ${escape(q.author || "Neznámý")}</div>
    ${q.author_bio ? `<div class="centered-card__bio">${escape(q.author_bio)}</div>` : ""}
    ${q.text_original ? `<div class="centered-card__original"><em>Originál:</em><br>„${escape(q.text_original)}"</div>` : ""}
    <div class="centered-card__footer">
      <div class="centered-card__source">Zdroj: <a href="${escape(q.source_url || "#")}" target="_blank" rel="noopener">${escape(q.source || "—")}</a></div>
      <button class="btn-save ${saved ? "btn-save--saved" : ""}">${saved ? "★ Uloženo" : "☆ Uložit"}</button>
    </div>
  `;
  const btn = div.querySelector(".btn-save");
  if (q.id) {
    btn.onclick = () => toggleSave({ ...q, _type: "quote" });
  } else {
    btn.disabled = true;
    btn.style.opacity = 0.5;
  }
  return div;
}

function renderQuote(data, container) {
  container.appendChild(quoteCardEl(data.quote || {}));
}

// -------------------- LESSON + FUN FACT --------------------

function lessonCardEl(lesson) {
  const saved = lesson.id && state.savedIds.has(lesson.id);
  const div = document.createElement("div");
  div.className = "centered-card lesson-card";
  const thumb = lesson.thumbnail
    ? `<img class="lesson-card__thumb" src="${escape(lesson.thumbnail)}" alt="" loading="lazy">`
    : "";
  div.innerHTML = `
    <div class="centered-card__heading">🎓 Dnes se něco nauč</div>
    ${thumb}
    <h2 class="lesson-card__title">${escape(lesson.title || "—")}</h2>
    <div class="centered-card__text">${escape(lesson.text || "—")}</div>
    <div class="centered-card__footer">
      <div class="centered-card__source">Zdroj: ${lesson.url
        ? `<a href="${escape(lesson.url)}" target="_blank" rel="noopener">${escape(lesson.source || "Wikipedia")}</a>`
        : escape(lesson.source || "—")}</div>
      <button class="btn-save ${saved ? "btn-save--saved" : ""}">${saved ? "★ Uloženo" : "☆ Uložit"}</button>
    </div>
  `;
  const btn = div.querySelector(".btn-save");
  if (lesson.id) {
    btn.onclick = () => toggleSave({ ...lesson, _type: "lesson" });
  } else {
    btn.disabled = true;
    btn.style.opacity = 0.5;
  }
  return div;
}

// -------------------- 10-DAY WEATHER TAB --------------------

function formatDayLabel(isoDate, i) {
  const d = new Date(isoDate + "T00:00:00");
  if (i === 0) return "Dnes";
  if (i === 1) return "Zítra";
  return `${CZ_DAY_SHORT[(d.getDay() + 6) % 7]} ${d.getDate()}. ${CZ_MONTHS_GEN[d.getMonth()]}`;
}

function formatTimeHM(iso) {
  try {
    return iso.slice(11, 16);
  } catch { return ""; }
}

function renderWeather10Day(container) {
  const w = state.weather;
  if (!w || !w.daily || !w.current) {
    container.innerHTML = `<div class="empty">Data počasí nejsou k dispozici.</div>`;
    return;
  }
  const d = w.daily;
  const cityName = state.city ? state.city.name : "";

  const sunrise = d.sunrise && d.sunrise[0] ? formatTimeHM(d.sunrise[0]) : "";
  const sunset = d.sunset && d.sunset[0] ? formatTimeHM(d.sunset[0]) : "";
  if (sunrise && sunset) {
    const sun = document.createElement("div");
    sun.className = "wx-sun";
    sun.innerHTML = `
      <div class="wx-sun__item"><span>🌅</span><div><div class="wx-sun__label">Východ</div><div class="wx-sun__val">${sunrise}</div></div></div>
      <div class="wx-sun__item"><span>🌇</span><div><div class="wx-sun__label">Západ</div><div class="wx-sun__val">${sunset}</div></div></div>
    `;
    container.appendChild(sun);
  }

  const daysHeading = document.createElement("div");
  daysHeading.className = "wx-days__heading";
  daysHeading.textContent = `Předpověď na 10 dní${cityName ? " — 📍 " + cityName : ""}`;
  container.appendChild(daysHeading);

  const total = Math.min(11, d.time.length);
  const chartWrap = document.createElement("div");
  chartWrap.className = "wx-chart-wrap";
  chartWrap.innerHTML = buildForecastChart(d, total);
  container.appendChild(chartWrap);
}

function _catmullRomPath(pts) {
  if (pts.length < 2) return "";
  let out = `M ${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] || p2;
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    out += ` C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${p2[0]} ${p2[1]}`;
  }
  return out;
}

function buildForecastChart(d, total) {
  const W = 760, H = 280;
  const padL = 38, padR = 20, padT = 44, padB = 58;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const highs = [], lows = [];
  for (let i = 0; i < total; i++) {
    highs.push(d.temperature_2m_max[i]);
    lows.push(d.temperature_2m_min[i]);
  }
  const dataMin = Math.min(...lows);
  const dataMax = Math.max(...highs);
  const yMin = Math.floor((dataMin - 2) / 2) * 2;
  const yMax = Math.ceil((dataMax + 2) / 2) * 2;
  const yRange = Math.max(1, yMax - yMin);

  const xAt = i => padL + (i / Math.max(1, total - 1)) * plotW;
  const yAt = t => padT + ((yMax - t) / yRange) * plotH;

  const highPts = highs.map((t, i) => [xAt(i), yAt(t)]);
  const lowPts = lows.map((t, i) => [xAt(i), yAt(t)]);
  const highPath = _catmullRomPath(highPts);
  const lowPath = _catmullRomPath(lowPts);
  const areaPoints = [
    ...highPts.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`),
    ...lowPts.slice().reverse().map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`),
  ].join(" ");

  // Y-axis ticks
  const tickStep = Math.max(2, Math.round(yRange / 5 / 2) * 2);
  const yTicks = [];
  for (let t = Math.ceil(yMin / tickStep) * tickStep; t <= yMax; t += tickStep) yTicks.push(t);

  let body = "";
  body += `
    <defs>
      <linearGradient id="wx-area-grad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#f87171" stop-opacity="0.35"/>
        <stop offset="55%" stop-color="#fbbf24" stop-opacity="0.18"/>
        <stop offset="100%" stop-color="#60a5fa" stop-opacity="0.28"/>
      </linearGradient>
    </defs>
  `;

  // Grid + Y labels
  for (const t of yTicks) {
    const y = yAt(t);
    body += `<line class="wx-chart__grid" x1="${padL}" y1="${y.toFixed(1)}" x2="${W - padR}" y2="${y.toFixed(1)}"/>`;
    body += `<text class="wx-chart__y-label" x="${padL - 6}" y="${(y + 4).toFixed(1)}" text-anchor="end">${t}°</text>`;
  }

  // Today vertical stripe
  const todayX = xAt(0);
  body += `<line class="wx-chart__today" x1="${todayX}" y1="${padT}" x2="${todayX}" y2="${padT + plotH}"/>`;

  // Area + lines
  body += `<polygon class="wx-chart__area" points="${areaPoints}" fill="url(#wx-area-grad)"/>`;
  body += `<path class="wx-chart__line wx-chart__line--low" d="${lowPath}"/>`;
  body += `<path class="wx-chart__line wx-chart__line--high" d="${highPath}"/>`;

  // Nodes + labels per day
  for (let i = 0; i < total; i++) {
    const x = xAt(i);
    const yh = yAt(highs[i]);
    const yl = yAt(lows[i]);
    const info = weatherInfo(d.weather_code[i]);
    body += `<circle class="wx-chart__dot wx-chart__dot--high" cx="${x}" cy="${yh.toFixed(1)}" r="3.2"/>`;
    body += `<circle class="wx-chart__dot wx-chart__dot--low" cx="${x}" cy="${yl.toFixed(1)}" r="3.2"/>`;
    body += `<text class="wx-chart__value wx-chart__value--high" x="${x}" y="${(yh - 8).toFixed(1)}" text-anchor="middle">${Math.round(highs[i])}°</text>`;
    body += `<text class="wx-chart__value wx-chart__value--low" x="${x}" y="${(yl + 16).toFixed(1)}" text-anchor="middle">${Math.round(lows[i])}°</text>`;
    body += `<text class="wx-chart__icon-svg" x="${x}" y="${(H - padB + 20).toFixed(1)}" text-anchor="middle">${info.icon}</text>`;
    body += `<text class="wx-chart__x-label${i === 0 ? " wx-chart__x-label--today" : ""}" x="${x}" y="${H - 10}" text-anchor="middle">${escape(formatDayShort(d.time[i], i))}</text>`;
  }

  return `<svg class="wx-chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Předpověď teploty na 10 dní">${body}</svg>`;
}

function formatDayShort(iso, i) {
  if (i === 1) return "Zítra";
  const d = new Date(iso + "T00:00:00");
  return `${CZ_DAY_SHORT[(d.getDay() + 6) % 7]} ${d.getDate()}.`;
}

function renderLesson(data, container) {
  const lesson = data.lesson || {};
  if (!lesson.title) {
    container.innerHTML = `<div class="empty">Dnešní lekci se nepodařilo načíst.</div>`;
    return;
  }
  container.appendChild(lessonCardEl(lesson));
}

// -------------------- SAVED --------------------

async function renderSaved(container) {
  const saved = await getAllSaved();
  saved.sort((a, b) => (b.saved_at || "").localeCompare(a.saved_at || ""));
  if (!saved.length) {
    container.innerHTML = `<div class="empty">Zatím nemáš uložené žádné položky.<br>Klikni na ☆ u čehokoli pro uložení.</div>`;
    return;
  }
  const articles = saved.filter(s => s._type === "article" || !s._type);
  const jokes = saved.filter(s => s._type === "joke");
  const quotes = saved.filter(s => s._type === "quote");
  const lessons = saved.filter(s => s._type === "lesson");

  if (articles.length) {
    const h = document.createElement("div");
    h.className = "subsection";
    h.textContent = `Články (${articles.length})`;
    container.appendChild(h);
    for (const a of articles) container.appendChild(articleEl(a));
  }
  if (jokes.length) {
    const h = document.createElement("div");
    h.className = "subsection";
    h.textContent = `Vtipy (${jokes.length})`;
    container.appendChild(h);
    for (const j of jokes) container.appendChild(jokeCardEl(j, j._lang || "cs"));
  }
  if (quotes.length) {
    const h = document.createElement("div");
    h.className = "subsection";
    h.textContent = `Citáty (${quotes.length})`;
    container.appendChild(h);
    for (const q of quotes) container.appendChild(quoteCardEl(q));
  }
  if (lessons.length) {
    const h = document.createElement("div");
    h.className = "subsection";
    h.textContent = `Lekce (${lessons.length})`;
    container.appendChild(h);
    for (const l of lessons) container.appendChild(lessonCardEl(l));
  }
}

// -------------------- SETTINGS VIEW --------------------

function renderSettings(container) {
  container.innerHTML = `
    <div class="centered-card">
      <div class="centered-card__heading">Město pro počasí</div>
      <p style="margin:0 0 0.75rem;">Aktuálně: <strong id="current-city">${escape(state.city.name)}${state.city.country ? ", " + escape(state.city.country) : ""}</strong></p>
      <input id="city-search" type="text" placeholder="Hledat město…" autocomplete="off"
        style="width:100%; padding:0.6rem; border-radius:8px; border:1px solid var(--border); background:var(--bg-alt); color:var(--text); font-size:1rem;" />
      <div id="city-results" style="margin-top:0.5rem;"></div>
    </div>
    <div class="centered-card">
      <div class="centered-card__heading">Tipy</div>
      <ul style="margin:0; padding-left:1.2rem; color:var(--text-muted); font-size:0.9rem; line-height:1.7;">
        <li>Mezi záložkami se dá přepínat <strong>svajpem vlevo/vpravo</strong> na obsahu.</li>
        <li>Klikni na počasí v horní liště pro detail rána/odpoledne/večera.</li>
        <li>Přidej aplikaci na plochu přes menu prohlížeče → „Přidat na plochu".</li>
        <li>Uložené věci zůstávají v paměti tohoto zařízení, i offline.</li>
      </ul>
    </div>
  `;
  const input = container.querySelector("#city-search");
  const results = container.querySelector("#city-results");
  let timer = null;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = input.value.trim();
      results.innerHTML = "";
      if (q.length < 2) return;
      const cities = await searchCity(q);
      for (const c of cities) {
        const btn = document.createElement("button");
        btn.textContent = `${c.name}${c.admin ? ", " + c.admin : ""}, ${c.country}`;
        btn.style.cssText = "display:block; width:100%; text-align:left; padding:0.6rem; margin:0.25rem 0; border:1px solid var(--border); border-radius:8px; background:transparent; color:var(--text); cursor:pointer;";
        btn.onclick = async () => {
          state.city = c;
          saveCity(c);
          await refreshWeather();
          renderTopBar();
          container.querySelector("#current-city").textContent = `${c.name}${c.country ? ", " + c.country : ""}`;
          results.innerHTML = "";
          input.value = "";
        };
        results.appendChild(btn);
      }
      if (!cities.length) {
        results.innerHTML = `<div style="color:var(--text-muted); padding:0.5rem;">Nic nenalezeno.</div>`;
      }
    }, 300);
  });
}

// -------------------- CONTENT RENDER --------------------

function renderContent() {
  const c = document.getElementById("content");
  c.innerHTML = "";
  const tab = state.activeTab;

  // Fade-in animation on tab switch
  c.classList.remove("content--enter");
  void c.offsetWidth; // restart animation
  c.classList.add("content--enter");

  if (tab === "joke") return renderJoke(state.data, c);
  if (tab === "quote") return renderQuote(state.data, c);
  if (tab === "lesson") return renderLesson(state.data, c);
  if (tab === "weather_10d") return renderWeather10Day(c);
  if (tab === "cot") return renderCOT(c);
  if (tab === "saved") return renderSaved(c);
  if (tab === "settings") return renderSettings(c);

  const articles = state.data.tabs[tab] || [];
  renderArticleList(articles, c, SUBSECTIONS[tab]);

  if (tab === "sport" && state.data.sport_fixtures) {
    renderSportFixtures(state.data.sport_fixtures, c);
  }
}

function renderSportFixtures(fixtures, container) {
  const order = [
    "premier_league",
    "czech_national_football",
    "czech_first_league",
    "czech_extraliga",
    "czech_national_hockey",
    "f1",
  ];
  const wrap = document.createElement("div");
  wrap.className = "fixtures-wrap";
  const heading = document.createElement("h2");
  heading.className = "fixtures-heading";
  heading.textContent = "📅 Dnešní program";
  wrap.appendChild(heading);

  let totalMatches = 0;
  for (const key of order) {
    const cat = fixtures[key];
    if (!cat) continue;
    const block = document.createElement("div");
    block.className = "fixtures-block";
    const title = document.createElement("div");
    title.className = "fixtures-block__title";
    title.innerHTML = `<span>${cat.icon || "🏆"}</span> ${escape(cat.label)}`;
    block.appendChild(title);
    if (!cat.matches.length) {
      const empty = document.createElement("div");
      empty.className = "fixtures-empty";
      empty.textContent = "Dnes žádný zápas.";
      block.appendChild(empty);
    } else {
      totalMatches += cat.matches.length;
      for (const m of cat.matches) {
        const row = document.createElement("div");
        row.className = "fixture-row";
        row.innerHTML = `
          <span class="fixture-time">${escape(m.time || "—")}</span>
          <span class="fixture-teams">${escape(m.home || "—")} <span class="fixture-vs">vs</span> ${escape(m.away || "—")}</span>
          ${m.status ? `<span class="fixture-status">${escape(m.status)}</span>` : ""}
        `;
        block.appendChild(row);
      }
    }
    wrap.appendChild(block);
  }
  container.appendChild(wrap);
}

// -------------------- WEATHER + BACKGROUND --------------------

async function refreshWeather() {
  try {
    state.weather = await fetchWeather(state.city.latitude, state.city.longitude);
    if (state.stopBg) state.stopBg();
    const canvas = document.getElementById("weather-bg");
    state.stopBg = startWeatherBg(canvas, state.weather.current.weather_code);
    renderTopBar();
    if (state.activeTab === "weather_10d") renderContent();
  } catch (e) {
    console.warn("weather fetch failed", e);
  }
}

function scheduleWeatherRefresh() {
  if (state.weatherTimer) clearInterval(state.weatherTimer);
  state.weatherTimer = setInterval(() => refreshWeather(), WEATHER_REFRESH_MS);
}

// -------------------- SWIPE GESTURES --------------------

function setupSwipe() {
  const target = document.getElementById("content");
  let startX = 0, startY = 0, tracking = false;
  target.addEventListener("touchstart", e => {
    if (e.touches.length !== 1) return;
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    tracking = true;
  }, { passive: true });
  target.addEventListener("touchend", e => {
    if (!tracking) return;
    tracking = false;
    const t = (e.changedTouches && e.changedTouches[0]) || null;
    if (!t) return;
    const dx = t.clientX - startX;
    const dy = t.clientY - startY;
    // Horizontal swipe only (x dominant, length > 60, not much vertical)
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      switchTabBy(dx < 0 ? 1 : -1);
    }
  }, { passive: true });
}

// -------------------- BOOT --------------------

async function boot() {
  state.city = loadCity();
  state.savedIds = await getSavedIds();

  try {
    state.data = await loadData();
  } catch (e) {
    document.getElementById("content").innerHTML =
      `<div class="empty">Chyba při načítání dat: ${escape(e.message)}<br>Data ještě nebyla vygenerována. Spusť aggregator.</div>`;
    return;
  }

  await refreshWeather();
  renderTopBar();
  renderTabs();
  renderContent();
  setupSwipe();
  scheduleWeatherRefresh();

  document.getElementById("generated-at").textContent =
    "Zprávy naposledy: " + new Date(state.data.generated_at).toLocaleString("cs-CZ");
}

boot();

// Service worker registration (PWA install + offline shell)
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  });
}
