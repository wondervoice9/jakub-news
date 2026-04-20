// COT Gold tab — loads cot_gold.json on demand and renders a simplified
// SELL ↔ BUY outlook view: verdict gauge, factor breakdown, price sparkline,
// narrative blocks and education.
//
// No external chart library — everything is pure SVG so the tab works
// offline and doesn't bloat the app shell.

const DATA_URL = "cot_gold.json";

async function loadData() {
  const res = await fetch(DATA_URL, { cache: "no-cache" });
  if (!res.ok) throw new Error(`cot_gold.json: ${res.status}`);
  return res.json();
}

// -------------------- FORMATTERS --------------------

const CZ_MONTHS = ["ledna","února","března","dubna","května","června",
                   "července","srpna","září","října","listopadu","prosince"];

function formatReportDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso + "T00:00:00");
  return `${d.getDate()}. ${CZ_MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

function formatDateTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("cs-CZ", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return "—"; }
}

function formatNumber(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("cs-CZ").format(Math.round(n));
}

function formatSigned(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const sign = n > 0 ? "+" : n < 0 ? "−" : "";
  return `${sign}${formatNumber(Math.abs(n))}`;
}

function formatPct(n, digits = 1) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${n.toFixed(digits)} %`;
}

function escape(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// -------------------- MAIN RENDER --------------------

export async function renderCOT(container) {
  container.innerHTML = `<div class="cot-loading">Načítám COT data…</div>`;

  let blob;
  try {
    blob = await loadData();
  } catch (e) {
    container.innerHTML = `
      <div class="cot-error">
        COT data zatím nejsou k dispozici.<br>
        <span class="cot-error__hint">Spusť jednorázově <code>python -m aggregator.cot_fetcher</code>,
        nebo počkej na pátek 22:00 až GitHub Actions stáhne report.</span>
      </div>`;
    return;
  }

  container.innerHTML = shellHTML(blob);
  attachEducationToggle(container);

  // Draw visuals
  drawVerdictGauge(container.querySelector("#cot-verdict-gauge"), blob.verdict);
  drawPriceChart(container.querySelector("#cot-price-chart"), blob.history || []);
}

// -------------------- SHELL HTML --------------------

function verdictTone(bucket) {
  return {
    strong_sell: { color: "#ef4444", emoji: "🔻" },
    sell:        { color: "#f59e0b", emoji: "🔽" },
    neutral:     { color: "#94a3b8", emoji: "⏸" },
    buy:         { color: "#22c55e", emoji: "🔼" },
    strong_buy:  { color: "#16a34a", emoji: "🚀" },
  }[bucket] || { color: "#94a3b8", emoji: "⏸" };
}

function shellHTML(blob) {
  const meta = blob.meta || {};
  const latest = blob.latest || {};
  const n = blob.narrative || {};
  const verdict = blob.verdict || { score: 0, bucket: "neutral", label: "—",
                                    explanation: "", factors: {} };
  const proj = blob.projection || {};
  const h4 = proj.horizons?.["4"] || {};
  const h8 = proj.horizons?.["8"] || {};
  const macros = blob.macros || {};
  const tone = verdictTone(verdict.bucket);

  return `
    <section class="cot-wrap">
      <header class="cot-header">
        <h1 class="cot-header__title">COT výhled – ${escape(meta.display_name || "Zlato")}</h1>
        <div class="cot-header__subtitle">Data k úterý ${escape(formatReportDate(meta.last_report_date))}</div>
        <div class="cot-header__meta">Poslední aktualizace: ${escape(formatDateTime(meta.last_successful_fetch_utc))}</div>
      </header>

      <section class="cot-verdict" style="--verdict-color:${tone.color}">
        <div id="cot-verdict-gauge" class="cot-verdict__gauge"></div>
        <div class="cot-verdict__label">${tone.emoji} ${escape(verdict.label)}</div>
        <div class="cot-verdict__score">Skóre: ${verdict.score != null ? verdict.score.toFixed(0) : "—"} / 100</div>
        <p class="cot-verdict__explanation">${escape(verdict.explanation || "")}</p>
      </section>

      <section class="cot-factors">
        <div class="cot-factors__title">Co tvoří výhled</div>
        <div class="cot-factors__list">
          ${factorsHTML(verdict.factors || {})}
        </div>
      </section>

      <section class="cot-price">
        <div class="cot-price__title">
          Cena zlata (posledních 12 měsíců)
          <span class="cot-price__value">${latest.price_close != null ? `$${formatNumber(latest.price_close)}` : "—"}</span>
        </div>
        <div id="cot-price-chart" class="cot-price__chart"></div>
        <div class="cot-price__legend">
          <span><span class="dot dot--gold"></span> Cena</span>
          <span><span class="dot dot--ma20"></span> Průměr 20 týdnů${macros.gold_ma_short != null ? ` ($${formatNumber(macros.gold_ma_short)})` : ""}</span>
          <span><span class="dot dot--ma50"></span> Průměr 50 týdnů${macros.gold_ma_long != null ? ` ($${formatNumber(macros.gold_ma_long)})` : ""}</span>
        </div>
      </section>

      <section class="cot-quick">
        ${quickCard("Net spekulanti", formatSigned(latest.noncomm_net), latest.noncomm_net_change, "kontrakty")}
        ${quickCard("Open interest", formatNumber(latest.open_interest), latest.open_interest_change, "kontrakty")}
        ${quickCard("Historické analogie", `${proj.analogies_count || 0}× za 3 roky`, null, "±5 bodů COT Indexu")}
        ${quickCard("4-týdenní medián", h4.p50_pct != null ? formatPct(h4.p50_pct) : "—",
                    null, h4.p25_pct != null ? `pásmo ${formatPct(h4.p25_pct)} až ${formatPct(h4.p75_pct)}` : "—")}
        ${quickCard("8-týdenní medián", h8.p50_pct != null ? formatPct(h8.p50_pct) : "—", null, "")}
      </section>

      <section class="cot-narrative">
        <article class="cot-narrative__block">
          <h3 class="cot-narrative__title">🕰️ Co se dělo</h3>
          <p>${escape(n.past || "—")}</p>
        </article>
        <article class="cot-narrative__block">
          <h3 class="cot-narrative__title">📍 Kde jsme teď</h3>
          <p>${escape(n.present || "—")}</p>
        </article>
        <article class="cot-narrative__block cot-narrative__block--future">
          <h3 class="cot-narrative__title">🔮 Co lze očekávat</h3>
          <p>${escape(n.future || "—")}</p>
        </article>
      </section>

      <section class="cot-education">
        <button class="cot-education__toggle" aria-expanded="false">
          <span class="cot-education__chevron">▸</span>
          Jak se skóre počítá a co znamená?
        </button>
        <div class="cot-education__body" hidden>
          <p>Skóre je <strong>vážený průměr pěti faktorů</strong>. Každý faktor má hodnotu od
          <strong>−100</strong> (silně proti zlatu) do <strong>+100</strong> (silně pro zlato).
          Výsledek spadne do jednoho z pěti pásem:</p>
          <ul class="cot-legend-list">
            <li><span class="dot" style="background:#ef4444"></span><strong>SILNÝ SELL</strong> (&lt; −60) — převaha medvědích faktorů.</li>
            <li><span class="dot" style="background:#f59e0b"></span><strong>SELL</strong> (−60 až −20) — mírná medvědí převaha.</li>
            <li><span class="dot" style="background:#94a3b8"></span><strong>NEUTRÁL</strong> (−20 až +20) — faktory se ruší.</li>
            <li><span class="dot" style="background:#22c55e"></span><strong>BUY</strong> (+20 až +60) — mírná býčí převaha.</li>
            <li><span class="dot" style="background:#16a34a"></span><strong>SILNÝ BUY</strong> (&gt; +60) — převaha býčích faktorů.</li>
          </ul>
          <p><strong>Z čeho skóre počítáme:</strong></p>
          <ul>
            <li><strong>COT Index (30 %)</strong> — pozicování spekulantů <em>kontrariánsky</em>.
              Extrémně nakoupení spekulanti = riziko korekce. Extrémně vyprodaní = potenciál růstu.</li>
            <li><strong>Dolar / DXY (25 %)</strong> — silný / rostoucí dolar tlačí na zlato dolů.</li>
            <li><strong>10Y US výnosy (20 %)</strong> — vyšší výnosy = vyšší oportunitní náklady držení zlata.</li>
            <li><strong>Trend ceny (15 %)</strong> — cena nad 20W a 50W průměrem = uptrend.</li>
            <li><strong>VIX / strach na trhu (10 %)</strong> — vyšší strach = bid na safe-haven.</li>
          </ul>
          <p class="cot-disclaimer">
            ⚠ <strong>Toto není investiční doporučení.</strong> Skóre je statistický nástroj,
            ne predikce. Trhy reagují i na události mimo tyto faktory (geopolitika, centrální
            banky, likvidita). Vždy kombinuj s vlastním risk managementem.
          </p>
        </div>
      </section>
    </section>
  `;
}

function quickCard(label, value, change, sub) {
  const arrow = change == null ? "" :
    change > 0 ? `<span class="cot-quick__delta cot-quick__delta--up">▲ ${formatSigned(change)}</span>` :
    change < 0 ? `<span class="cot-quick__delta cot-quick__delta--down">▼ ${formatSigned(change)}</span>` :
    `<span class="cot-quick__delta">→ 0</span>`;
  return `
    <div class="cot-quick__card">
      <div class="cot-quick__label">${escape(label)}</div>
      <div class="cot-quick__value">${escape(value)}</div>
      ${arrow}
      ${sub ? `<div class="cot-quick__sub">${escape(sub)}</div>` : ""}
    </div>
  `;
}

function factorsHTML(factors) {
  const order = ["cot", "usd", "rates", "trend", "vix"];
  const rows = order
    .map(k => ({ key: k, f: factors[k] }))
    .filter(x => x.f);

  if (!rows.length) {
    return `<div class="cot-factor cot-factor--empty">Čekáme na první makro-snímek (DXY, výnosy, VIX).</div>`;
  }

  return rows.map(({ key, f }) => {
    const s = f.score ?? 0;
    // Convert -100..+100 to 0..100 for the bar fill position
    const pct = Math.max(0, Math.min(100, (s + 100) / 2));
    const toneClass =
      s >= 50 ? "cot-factor--strong-buy" :
      s > 0   ? "cot-factor--buy" :
      s === 0 ? "cot-factor--neutral" :
      s > -50 ? "cot-factor--sell" :
                "cot-factor--strong-sell";
    const weightPct = Math.round((f.weight || 0) * 100);
    return `
      <article class="cot-factor ${toneClass}">
        <header class="cot-factor__head">
          <span class="cot-factor__name">${escape(f.label || key)}</span>
          <span class="cot-factor__weight">váha ${weightPct} %</span>
        </header>
        <div class="cot-factor__bar">
          <div class="cot-factor__bar-track">
            <div class="cot-factor__bar-mid"></div>
            <div class="cot-factor__bar-fill" style="--fill:${pct}%"></div>
          </div>
          <div class="cot-factor__bar-labels">
            <span>SELL</span><span>NEUTRÁL</span><span>BUY</span>
          </div>
        </div>
        <div class="cot-factor__row">
          <span class="cot-factor__value">${escape(f.value_label || "")}</span>
          <span class="cot-factor__score">skóre ${s > 0 ? "+" : ""}${Math.round(s)}</span>
        </div>
        <p class="cot-factor__note">${escape(f.note || "")}</p>
      </article>
    `;
  }).join("");
}

function attachEducationToggle(container) {
  const btn = container.querySelector(".cot-education__toggle");
  const body = container.querySelector(".cot-education__body");
  const chev = container.querySelector(".cot-education__chevron");
  if (!btn || !body) return;
  btn.onclick = () => {
    const open = !body.hidden;
    body.hidden = open;
    btn.setAttribute("aria-expanded", String(!open));
    if (chev) chev.textContent = open ? "▸" : "▾";
  };
}

// -------------------- VERDICT GAUGE (SVG speedometer) --------------------

function drawVerdictGauge(slot, verdict) {
  if (!slot) return;
  const score = verdict && typeof verdict.score === "number" ? verdict.score : 0;

  // Arc spans from 180° (left, SELL) to 0° (right, BUY), upper half.
  // Score -100..+100 maps to angle 180..0.
  const t = (score + 100) / 200;              // 0..1
  const clamped = Math.max(0, Math.min(1, t));
  const angleDeg = 180 - clamped * 180;       // 180 → 0
  const angleRad = angleDeg * Math.PI / 180;

  const cx = 150, cy = 130, r = 110;
  const needleX = cx + r * Math.cos(angleRad);
  const needleY = cy - r * Math.sin(angleRad);

  // Five zone arcs (sell/sell/neutral/buy/buy) — match the classification
  const zones = [
    { from: -100, to: -60, color: "#ef4444" },
    { from: -60,  to: -20, color: "#f59e0b" },
    { from: -20,  to:  20, color: "#94a3b8" },
    { from:  20,  to:  60, color: "#22c55e" },
    { from:  60,  to: 100, color: "#16a34a" },
  ];
  const zoneArcs = zones.map(z => arcPath(cx, cy, r, z.from, z.to)).join("");
  const zonePaths = zones.map((z, i) =>
    `<path d="${arcPath(cx, cy, r, z.from, z.to)}" stroke="${z.color}" stroke-width="22" stroke-linecap="butt" fill="none" opacity="0.85"/>`
  ).join("");

  slot.innerHTML = `
    <svg viewBox="0 0 300 170" class="cot-gauge-svg" aria-hidden="true">
      ${zonePaths}
      <!-- tick labels -->
      <text x="20" y="160" fill="#94a3b8" font-size="12" font-weight="600">SELL</text>
      <text x="150" y="28" fill="#94a3b8" font-size="12" font-weight="600" text-anchor="middle">NEUTRÁL</text>
      <text x="280" y="160" fill="#94a3b8" font-size="12" font-weight="600" text-anchor="end">BUY</text>
      <!-- needle -->
      <line x1="${cx}" y1="${cy}" x2="${needleX.toFixed(1)}" y2="${needleY.toFixed(1)}"
            stroke="var(--verdict-color)" stroke-width="4" stroke-linecap="round"/>
      <circle cx="${cx}" cy="${cy}" r="8" fill="var(--verdict-color)"/>
      <circle cx="${cx}" cy="${cy}" r="4" fill="#0f172a"/>
    </svg>
  `;
}

function arcPath(cx, cy, r, fromScore, toScore) {
  // Convert score (-100..+100) → angle in degrees (180..0 left→right).
  const a1 = (180 - ((fromScore + 100) / 200) * 180) * Math.PI / 180;
  const a2 = (180 - ((toScore   + 100) / 200) * 180) * Math.PI / 180;
  const x1 = cx + r * Math.cos(a1), y1 = cy - r * Math.sin(a1);
  const x2 = cx + r * Math.cos(a2), y2 = cy - r * Math.sin(a2);
  const largeArc = Math.abs(a1 - a2) > Math.PI ? 1 : 0;
  // SVG sweep flag 0 because we go from left→right with y inverted; tested visually.
  return `M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r} ${r} 0 ${largeArc} 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`;
}

// -------------------- PRICE SPARKLINE (SVG) --------------------

function drawPriceChart(slot, history) {
  if (!slot) return;
  const points = history
    .filter(r => r.price_close != null)
    .slice(-52);  // last ~12 months of weekly closes

  if (points.length < 2) {
    slot.innerHTML = `<div class="cot-error">Zatím nemáme dost cenových dat.</div>`;
    return;
  }

  const W = 720, H = 180, padX = 8, padY = 14;
  const prices = points.map(p => p.price_close);
  const pMin = Math.min(...prices);
  const pMax = Math.max(...prices);
  const pRange = Math.max(1, pMax - pMin);

  function x(i) { return padX + (i / (points.length - 1)) * (W - 2 * padX); }
  function y(v) { return padY + (1 - (v - pMin) / pRange) * (H - 2 * padY); }

  // Price polyline
  const pricePath = prices.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");

  // 20-week and 50-week moving averages over the visible window
  function movingAvg(series, w) {
    const out = [];
    for (let i = 0; i < series.length; i++) {
      if (i + 1 < w) { out.push(null); continue; }
      let s = 0;
      for (let k = i + 1 - w; k <= i; k++) s += series[k];
      out.push(s / w);
    }
    return out;
  }
  const ma20 = movingAvg(prices, 20);
  const ma50 = movingAvg(prices, 50);

  function seriesPath(series) {
    const segs = [];
    let cur = [];
    for (let i = 0; i < series.length; i++) {
      if (series[i] == null) {
        if (cur.length >= 2) segs.push(cur.join(" "));
        cur = [];
        continue;
      }
      cur.push(`${cur.length === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(series[i]).toFixed(1)}`);
    }
    if (cur.length >= 2) segs.push(cur.join(" "));
    return segs.join(" ");
  }
  const ma20Path = seriesPath(ma20);
  const ma50Path = seriesPath(ma50);

  // Area under price
  const areaPath = `M ${x(0).toFixed(1)} ${y(prices[0]).toFixed(1)} ` +
    prices.slice(1).map((v, i) => `L ${x(i + 1).toFixed(1)} ${y(v).toFixed(1)}`).join(" ") +
    ` L ${x(prices.length - 1).toFixed(1)} ${(H - padY).toFixed(1)} L ${x(0).toFixed(1)} ${(H - padY).toFixed(1)} Z`;

  const lastIdx = prices.length - 1;
  const lastX = x(lastIdx), lastY = y(prices[lastIdx]);

  // Sparse axis labels: first and last dates
  const first = points[0].report_date;
  const last = points[lastIdx].report_date;

  slot.innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" class="cot-spark" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id="gold-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#fbbf24" stop-opacity="0.35"/>
          <stop offset="100%" stop-color="#fbbf24" stop-opacity="0"/>
        </linearGradient>
      </defs>
      <path d="${areaPath}" fill="url(#gold-area)"/>
      ${ma50Path ? `<path d="${ma50Path}" fill="none" stroke="#a78bfa" stroke-width="1.5" stroke-dasharray="4 3" opacity="0.85"/>` : ""}
      ${ma20Path ? `<path d="${ma20Path}" fill="none" stroke="#38bdf8" stroke-width="1.5" opacity="0.9"/>` : ""}
      <path d="${pricePath}" fill="none" stroke="#fbbf24" stroke-width="2.2"/>
      <circle cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="5" fill="#fbbf24" stroke="#0f172a" stroke-width="2"/>
      <text x="${lastX.toFixed(1)}" y="${(lastY - 10).toFixed(1)}" fill="#fbbf24"
            font-size="12" font-weight="700" text-anchor="end">$${Math.round(prices[lastIdx])}</text>
    </svg>
    <div class="cot-spark__axis">
      <span>${escape(first)}</span>
      <span>$${Math.round(pMin)} — $${Math.round(pMax)}</span>
      <span>${escape(last)}</span>
    </div>
  `;
}
