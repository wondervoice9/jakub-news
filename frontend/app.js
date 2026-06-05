import { startWeatherBg } from "./weather-bg.js";
import { fetchWeather, searchCity, weatherInfo, splitTodayByPart } from "./weather.js";
import { saveArticle, unsaveArticle, getSavedIds, getAllSaved } from "./storage.js";

const DEFAULT_CITY = { name: "Liberec", country: "Česko", latitude: 50.7663, longitude: 15.0543 };
const TABS = [
  { id: "world", label: "Svět" },
  { id: "czech", label: "Česko" },
  { id: "sport", label: "Sport" },
  { id: "tech", label: "Technologie" },
  { id: "culture", label: "Kultura" },
  { id: "events", label: "Events" },
  { id: "good_news", label: "Good News" },
  { id: "lesson", label: "Naučit se" },
  { id: "joke", label: "Vtip" },
  { id: "quote", label: "Citát" },
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
    { key: "other", label: "Ostatní" },
    { key: "falco", label: "Falco" },
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
  eventsRegion: "liberec",   // "liberec" | "liberec_okoli" | "praha"
};

const EVENT_REGION_FILTERS = [
  { id: "liberec", label: "Liberec" },
  { id: "liberec_okoli", label: "Liberec okolí" },
  { id: "praha", label: "Praha" },
];

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
    ${(a.summary_cs || a.summary) ? `<p class="article__summary">${escape(a.summary_cs || a.summary)}</p>` : ""}
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

function renderArticleList(articles, container, subsection, tabId) {
  if (!articles.length) {
    container.innerHTML = `<div class="empty">Žádné články pro dnešek.</div>`;
    return;
  }
  if (!subsection) {
    for (const a of articles) container.appendChild(articleEl(a));
    return;
  }

  // Build counts and chips (same pattern as events region filter)
  const knownKeys = subsection.map(s => s.key);
  const knownSet = new Set(knownKeys);
  const counts = { all: articles.length, _other: 0 };
  for (const k of knownKeys) counts[k] = 0;
  for (const a of articles) {
    if (knownSet.has(a.sub)) counts[a.sub]++;
    else counts._other++;
  }

  state.subsectionFilter = state.subsectionFilter || {};
  const current = state.subsectionFilter[tabId] || subsection[0].key;

  const filters = [...subsection];
  if (counts._other > 0) filters.push({ key: "_other", label: "Další" });

  const chips = document.createElement("div");
  chips.className = "event-region-chips";
  for (const f of filters) {
    const btn = document.createElement("button");
    btn.className = "event-region-chip" + (current === f.key ? " event-region-chip--active" : "");
    btn.innerHTML = f.key === "falco"
      ? escape(f.label)
      : `${escape(f.label)} <span class="event-region-chip__count">${counts[f.key] || 0}</span>`;
    btn.onclick = () => {
      if (state.subsectionFilter[tabId] === f.key) return;
      state.subsectionFilter[tabId] = f.key;
      renderContent();
    };
    chips.appendChild(btn);
  }
  container.appendChild(chips);

  // Falco isn't an article category — it's images. Render only the chips here;
  // the caller (renderContent) appends the Falco view below.
  if (current === "falco") return;

  let toShow;
  if (current === "_other") toShow = articles.filter(a => !knownSet.has(a.sub));
  else toShow = articles.filter(a => a.sub === current);

  if (!toShow.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "V této kategorii dnes nic není.";
    container.appendChild(empty);
    return;
  }
  for (const a of toShow) container.appendChild(articleEl(a));
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

// -------------------- EVENTS --------------------

function formatEventDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso + "T00:00:00");
    const day = CZ_DAY_SHORT[(d.getDay() + 6) % 7];
    return `${day} ${d.getDate()}. ${CZ_MONTHS_GEN[d.getMonth()]}`;
  } catch { return iso; }
}

function eventGroupLabel(iso) {
  if (!iso) return "Bez data";
  try {
    const ev = new Date(iso + "T00:00:00");
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diffDays = Math.round((ev - today) / 86400000);
    if (diffDays < 0) return "Proběhlo";
    if (diffDays === 0) return "Dnes";
    if (diffDays === 1) return "Zítra";
    if (diffDays <= 7) return "Tento týden";
    if (diffDays <= 14) return "Příští týden";
    if (diffDays <= 30) return "Tento měsíc";
    return "Později";
  } catch { return "Bez data"; }
}

function eventCardEl(ev) {
  const saved = state.savedIds.has(ev.id);
  const el = document.createElement("article");
  el.className = "article event-card" + (ev.is_tip ? " event-card--tip" : "");
  const dateStr = ev.date ? formatEventDate(ev.date) : "";
  const timeStr = ev.time ? ev.time : "";
  const dateTime = [dateStr, timeStr].filter(Boolean).join(" · ");
  const meta = [];
  if (ev.city) meta.push(`<span class="event-card__city">📍 ${escape(ev.city)}</span>`);
  if (ev.place) meta.push(`<span class="event-card__place">${escape(ev.place)}</span>`);
  if (dateTime) meta.push(`<span class="event-card__date">🗓 ${escape(dateTime)}</span>`);
  const tipBadge = ev.is_tip
    ? `<span class="event-card__tip-badge" title="Tip z médií (Google News)">📰 Tip</span>`
    : "";
  el.innerHTML = `
    <h2 class="article__title">
      ${tipBadge}
      <a href="${escape(ev.url)}" target="_blank" rel="noopener noreferrer">${escape(ev.title)}</a>
    </h2>
    <div class="event-card__meta">${meta.join("")}</div>
    <div class="article__footer">
      <div class="article__meta">
        <span class="article__source">${escape(ev.source)}</span>
      </div>
      <div class="article__actions">
        <button class="btn-save ${saved ? "btn-save--saved" : ""}">${saved ? "★ Uloženo" : "☆ Uložit"}</button>
        <div class="event-card__kebab-wrap">
          <button class="event-card__kebab-btn" aria-label="Další možnosti" aria-haspopup="true" aria-expanded="false">⋮</button>
          <div class="event-card__kebab-menu" hidden>
            <a class="event-card__kebab-item" href="${escape(ev.url)}" target="_blank" rel="noopener noreferrer">↗ Otevřít originál</a>
          </div>
        </div>
      </div>
    </div>
  `;
  el.querySelector(".btn-save").onclick = () => toggleSave({ ...ev, _type: "event" });
  const kebabBtn = el.querySelector(".event-card__kebab-btn");
  const kebabMenu = el.querySelector(".event-card__kebab-menu");
  kebabBtn.onclick = (e) => {
    e.stopPropagation();
    closeAllKebabMenus(kebabMenu);
    const open = !kebabMenu.hidden;
    kebabMenu.hidden = open;
    kebabBtn.setAttribute("aria-expanded", String(!open));
    // Lift card above siblings while menu is open so dropdown isn't clipped
    el.classList.toggle("event-card--menu-open", !open);
  };
  return el;
}

function closeAllKebabMenus(except) {
  document.querySelectorAll(".event-card__kebab-menu").forEach(m => {
    if (m === except) return;
    if (!m.hidden) {
      m.hidden = true;
      const btn = m.parentElement?.querySelector(".event-card__kebab-btn");
      if (btn) btn.setAttribute("aria-expanded", "false");
      const card = m.closest(".event-card");
      if (card) card.classList.remove("event-card--menu-open");
    }
  });
}

// Click outside any kebab menu closes them all
document.addEventListener("click", (e) => {
  if (!e.target.closest(".event-card__kebab-wrap")) {
    closeAllKebabMenus(null);
  }
});

function renderEventRegionChips(allEvents, container) {
  // Count events per region so chips show how many fall under each
  const counts = { liberec: 0, liberec_okoli: 0, praha: 0 };
  for (const ev of allEvents) {
    if (counts[ev.region] !== undefined) counts[ev.region]++;
  }
  const wrap = document.createElement("div");
  wrap.className = "event-region-chips";
  for (const f of EVENT_REGION_FILTERS) {
    const btn = document.createElement("button");
    btn.className = "event-region-chip" + (state.eventsRegion === f.id ? " event-region-chip--active" : "");
    btn.innerHTML = `${escape(f.label)} <span class="event-region-chip__count">${counts[f.id] || 0}</span>`;
    btn.onclick = () => {
      if (state.eventsRegion === f.id) return;
      state.eventsRegion = f.id;
      renderContent();
    };
    wrap.appendChild(btn);
  }
  container.appendChild(wrap);
}

function renderEvents(data, container) {
  const events = data.events || [];
  if (!events.length) {
    container.innerHTML = `<div class="empty">Žádné eventy nejsou aktuálně k dispozici.<br><small>Aggregator je možná ještě nestáhl, nebo selhala síť.</small></div>`;
    return;
  }
  // Region filter chips at top — counts derived from full event list
  renderEventRegionChips(events, container);
  // Apply region filter
  const filtered = events.filter(ev => ev.region === state.eventsRegion);
  // Group by time bucket
  const order = ["Dnes", "Zítra", "Tento týden", "Příští týden", "Tento měsíc", "Později", "Bez data", "Proběhlo"];
  const groups = {};
  for (const ev of filtered) {
    const g = eventGroupLabel(ev.date);
    (groups[g] = groups[g] || []).push(ev);
  }
  let rendered = 0;
  for (const label of order) {
    const items = groups[label];
    if (!items || !items.length) continue;
    const h = document.createElement("div");
    h.className = "subsection";
    h.textContent = `${label} (${items.length})`;
    container.appendChild(h);
    for (const ev of items) {
      container.appendChild(eventCardEl(ev));
      rendered++;
    }
  }
  if (!rendered) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "V této oblasti zatím žádné nadcházející eventy.";
    container.appendChild(empty);
  }
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
  const events = saved.filter(s => s._type === "event");

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
  if (events.length) {
    const h = document.createElement("div");
    h.className = "subsection";
    h.textContent = `Events (${events.length})`;
    container.appendChild(h);
    for (const ev of events) container.appendChild(eventCardEl(ev));
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
  if (tab === "saved") return renderSaved(c);
  if (tab === "settings") return renderSettings(c);
  if (tab === "events") return renderEvents(state.data, c);

  const articles = state.data.tabs[tab] || [];
  renderArticleList(articles, c, SUBSECTIONS[tab], tab);

  if (tab === "sport") {
    const sub = (state.subsectionFilter && state.subsectionFilter.sport) || SUBSECTIONS.sport[0].key;
    if (sub === "falco") {
      renderFalco(state.data.falco, c);
    } else if (state.data.sport_fixtures) {
      renderSportFixtures(state.data.sport_fixtures, c, sub);
    }
  }
}

// -------------------- FALCO (Vratliga) --------------------

// The Vratliga site publishes everything as images, so we just display the
// current images scraped daily into data.falco. No text to parse.
function renderFalco(falco, container) {
  if (!falco || !falco.sections) {
    const e = document.createElement("div");
    e.className = "empty";
    e.textContent = "Falco data zatím nejsou k dispozici (aggregator ještě neproběhl).";
    container.appendChild(e);
    return;
  }

  const order = ["matches", "table", "scorers", "hattricks", "schedule"];
  const wrap = document.createElement("div");
  wrap.className = "falco";

  for (const key of order) {
    const sec = falco.sections[key];
    if (!sec || !sec.images || !sec.images.length) continue;

    const block = document.createElement("section");
    block.className = "falco__block";

    const h = document.createElement("h3");
    h.className = "falco__heading";
    h.textContent = sec.label || key;
    block.appendChild(h);

    for (const src of sec.images) {
      const link = document.createElement("a");
      link.href = sec.url;
      link.target = "_blank";
      link.rel = "noopener";
      const img = document.createElement("img");
      img.className = "falco__img";
      img.loading = "lazy";
      img.alt = sec.label || key;
      img.src = src;
      link.appendChild(img);
      block.appendChild(link);
    }
    wrap.appendChild(block);
  }

  if (!wrap.children.length) {
    const e = document.createElement("div");
    e.className = "empty";
    e.textContent = "Z webu Vratligy se teď nepodařilo načíst obrázky.";
    container.appendChild(e);
    return;
  }

  const source = document.createElement("a");
  source.className = "falco__source";
  source.href = falco.source_url || "https://vratliga.webnode.cz/";
  source.target = "_blank";
  source.rel = "noopener";
  source.textContent = "Zdroj: vratliga.webnode.cz";
  wrap.appendChild(source);

  container.appendChild(wrap);
}

function renderSportFixtures(fixtures, container, sportFilter) {
  // Display order — all keys grouped by sport (football → hockey → other).
  const order = [
    // football — Czech
    "czech_first_league", "czech_cup",
    // football — English
    "premier_league", "fa_cup", "efl_cup",
    // football — UEFA clubs
    "champions_league", "europa_league", "conference_league",
    // football — national teams / international
    "world_cup", "world_cup_qualifiers", "euro", "euro_qualifiers",
    "nations_league", "czech_national_football",
    // hockey
    "czech_extraliga", "iihf_worlds", "olympic_hockey", "czech_national_hockey",
    // other (motorsport)
    "f1", "motogp",
  ];

  // Map subsection chip → fixture sport field. "_other" (unknown) → "other".
  const filter = (sportFilter === "_other") ? "other"
                : (sportFilter || null);

  const visibleKeys = order.filter(k => {
    const cat = fixtures[k];
    if (!cat) return false;
    if (filter && cat.sport !== filter) return false;
    return true;
  });
  if (!visibleKeys.length) return;

  const headingText = {
    football: "📅 Dnešní fotbal",
    hockey: "📅 Dnešní hokej",
    other: "📅 Dnešní program",
  }[filter] || "📅 Dnešní program";

  const wrap = document.createElement("div");
  wrap.className = "fixtures-wrap";
  const heading = document.createElement("h2");
  heading.className = "fixtures-heading";
  heading.textContent = headingText;
  wrap.appendChild(heading);

  for (const key of visibleKeys) {
    const cat = fixtures[key];
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
  // Listen on document so swipes anywhere (incl. tabs row) work.
  const target = document.body;
  let startX = 0, startY = 0, startT = 0, tracking = false;
  target.addEventListener("touchstart", e => {
    if (e.touches.length !== 1) return;
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    startT = Date.now();
    tracking = true;
  }, { passive: true });
  target.addEventListener("touchend", e => {
    if (!tracking) return;
    tracking = false;
    const t = (e.changedTouches && e.changedTouches[0]) || null;
    if (!t) return;
    const dx = t.clientX - startX;
    const dy = t.clientY - startY;
    const dt = Date.now() - startT;
    // Horizontal swipe: x dominant (> |dy|*1.3), min 40px, max 600ms (flick).
    if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.3 && dt < 600) {
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
