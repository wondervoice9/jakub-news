"""Pure analysis functions for COT + macro data.

No I/O here — only math and text generation. This keeps the module easy to
unit-test and to reason about. All functions accept plain dicts/lists.
"""
from __future__ import annotations

from typing import Any, Literal

SentimentBucket = Literal[
    "extreme_bearish", "bearish", "neutral", "bullish", "extreme_bullish"
]

VerdictBucket = Literal["strong_sell", "sell", "neutral", "buy", "strong_buy"]


# -------------------- MOVING AVERAGE --------------------

def moving_average(values: list[float], window: int) -> float | None:
    """Simple moving average of the last `window` values. None if too short."""
    clean = [v for v in values if v is not None]
    if len(clean) < window:
        return None
    return sum(clean[-window:]) / window


# -------------------- COT INDEX --------------------

def cot_index(net_current: float, historical_nets: list[float]) -> float:
    """Williams COT Index: where the current net position sits within the
    historical window, on a 0–100 scale.

    0   = net is the most bearish value in the window.
    100 = most bullish value in the window.

    Edge cases: empty window → 50 (neutral), flat window (hi==lo) → 50.
    """
    if not historical_nets:
        return 50.0
    hi = max(historical_nets)
    lo = min(historical_nets)
    if hi == lo:
        return 50.0
    raw = (net_current - lo) / (hi - lo) * 100.0
    return max(0.0, min(100.0, raw))


def compute_indexes(
    records: list[dict],
    window_6m: int = 26,
    window_3y: int = 156,
    min_sample: int = 4,
) -> list[dict]:
    """Attach cot_index_6m and cot_index_3y to each record.

    Records MUST be sorted ascending by report_date (oldest first).
    Records with window smaller than `min_sample` get `None` for that index.
    """
    out: list[dict] = []
    for i, rec in enumerate(records):
        start_6m = max(0, i + 1 - window_6m)
        start_3y = max(0, i + 1 - window_3y)
        nets_6m = [r["noncomm_net"] for r in records[start_6m:i + 1]]
        nets_3y = [r["noncomm_net"] for r in records[start_3y:i + 1]]

        new = dict(rec)
        new["cot_index_6m"] = cot_index(rec["noncomm_net"], nets_6m) if len(nets_6m) >= min_sample else None
        new["cot_index_3y"] = cot_index(rec["noncomm_net"], nets_3y) if len(nets_3y) >= min_sample else None
        out.append(new)
    return out


# -------------------- SENTIMENT --------------------

def classify_sentiment(
    index_value: float,
    thresholds: dict[str, float] | None = None,
) -> SentimentBucket:
    """Map a 0–100 COT Index value to a sentiment bucket. Thresholds are
    inclusive on the lower bound, so exact 20 = bearish, 80 = extreme_bullish.
    """
    t = thresholds or {
        "extreme_bearish_max": 20,
        "bearish_max": 40,
        "neutral_max": 60,
        "bullish_max": 80,
    }
    if index_value < t["extreme_bearish_max"]:
        return "extreme_bearish"
    if index_value < t["bearish_max"]:
        return "bearish"
    if index_value < t["neutral_max"]:
        return "neutral"
    if index_value < t["bullish_max"]:
        return "bullish"
    return "extreme_bullish"


# -------------------- PROJECTION BANDS --------------------

def _percentile(sorted_values: list[float], p: float) -> float:
    """Linear-interpolated percentile on a pre-sorted list. p in [0, 100]."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * p / 100.0
    lo = int(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = k - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def projection_bands(
    records: list[dict],
    current_index: float,
    horizons: list[int] | None = None,
    tolerance: float = 5.0,
    percentiles: list[float] | None = None,
) -> dict[str, Any]:
    """Find weeks in history with cot_index_3y close to `current_index`
    (±tolerance) and compute the distribution of forward price changes.

    Returns a dict:
      {
        "analogies_count": int,
        "horizons": {
          "4": {
            "p25_pct": float, "p50_pct": float, "p75_pct": float,
            "hit_rate_up": float (0–1), "hit_rate_down": float (0–1),
            "samples": int,
          },
          "8": {...},
        }
      }
    """
    horizons = horizons or [4, 8]
    percentiles = percentiles or [25, 50, 75]

    valid = [
        r for r in records
        if r.get("cot_index_3y") is not None and r.get("price_close") is not None
    ]
    if not valid:
        return {"analogies_count": 0, "horizons": {}}

    max_h = max(horizons)
    analogy_indices = [
        i for i, r in enumerate(valid)
        if abs(r["cot_index_3y"] - current_index) <= tolerance
        and i + max_h < len(valid)
    ]

    result: dict[str, Any] = {
        "analogies_count": len(analogy_indices),
        "horizons": {},
    }

    for h in horizons:
        changes = []
        for i in analogy_indices:
            start = valid[i]["price_close"]
            end = valid[i + h]["price_close"]
            if start and start > 0:
                changes.append((end - start) / start * 100.0)
        if not changes:
            continue
        changes_sorted = sorted(changes)
        result["horizons"][str(h)] = {
            "p25_pct": round(_percentile(changes_sorted, 25), 2),
            "p50_pct": round(_percentile(changes_sorted, 50), 2),
            "p75_pct": round(_percentile(changes_sorted, 75), 2),
            "hit_rate_up": round(sum(1 for x in changes if x > 0) / len(changes), 3),
            "hit_rate_down": round(sum(1 for x in changes if x < 0) / len(changes), 3),
            "samples": len(changes),
        }
    return result


# -------------------- TEXT GENERATOR --------------------

def _safe(value, default=0):
    return value if value is not None else default


def generate_text(
    records: list[dict],
    projection: dict[str, Any],
    config: dict[str, Any],
    weeks_back: int = 6,
    verdict: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Generate past/present/future narrative.

    Returns {"past": str, "present": str, "future": str}. Falls back to
    placeholder strings when there is not enough data.
    """
    valid = [r for r in records if r.get("cot_index_3y") is not None]
    if len(valid) < 2:
        return {
            "past": "Zatím nemáme dost historických dat pro vyhodnocení.",
            "present": "—",
            "future": "Projekce bude dostupná po nasbírání dostatečné historie.",
        }

    current = valid[-1]
    past_idx = max(0, len(valid) - 1 - weeks_back)
    past_rec = valid[past_idx]
    weeks_span = len(valid) - 1 - past_idx

    bucket = classify_sentiment(
        current["cot_index_3y"],
        config.get("sentiment_thresholds"),
    )

    templates = config["text_templates"]

    # Past
    price_now = _safe(current.get("price_close"))
    price_then = _safe(past_rec.get("price_close"))
    price_change = (
        round((price_now - price_then) / price_then * 100.0, 1)
        if price_then else 0.0
    )
    past_text = templates["past"].format(
        weeks=weeks_span,
        index_start=round(past_rec["cot_index_3y"]),
        index_end=round(current["cot_index_3y"]),
        price_change_pct=price_change,
    )

    # Present
    present_text = templates["present"][bucket].format(
        index_3y=round(current["cot_index_3y"]),
        index_6m=round(current["cot_index_6m"]) if current.get("cot_index_6m") is not None else "—",
    )

    # Future
    h4 = projection.get("horizons", {}).get("4", {})
    h8 = projection.get("horizons", {}).get("8", {})
    verdict_label = (verdict or {}).get("label", "—")
    future_text = templates["future"][bucket].format(
        analogies=projection.get("analogies_count", 0),
        hit_rate_up_pct=round(_safe(h4.get("hit_rate_up")) * 100),
        hit_rate_down_pct=round(_safe(h4.get("hit_rate_down")) * 100),
        p25_pct=_safe(h4.get("p25_pct")),
        p50_pct=_safe(h4.get("p50_pct")),
        p75_pct=_safe(h4.get("p75_pct")),
        median_8w_pct=_safe(h8.get("p50_pct")),
        verdict_label=verdict_label,
    )

    return {"past": past_text, "present": present_text, "future": future_text}


# -------------------- VERDICT (SELL ↔ BUY) --------------------

DEFAULT_VERDICT_WEIGHTS = {
    "cot": 0.30, "usd": 0.25, "rates": 0.20, "trend": 0.15, "vix": 0.10,
}


def _score_cot_contrarian(cot_index_3y: float) -> float:
    """Contrarian COT score. Low index = speculators bearish → bullish for gold.
    High index = speculators extremely long → bearish for gold. -100..+100."""
    if cot_index_3y < 20: return 100.0
    if cot_index_3y < 40: return 50.0
    if cot_index_3y < 60: return 0.0
    if cot_index_3y < 80: return -50.0
    return -100.0


def _score_usd(dxy_change_3m_pct: float | None) -> float:
    """Strong/rising dollar is bearish for gold. Band: ±3 % over 3 months.
    Returns -100 (rising dollar → sell) to +100 (weak dollar → buy)."""
    if dxy_change_3m_pct is None:
        return 0.0
    clamped = max(-3.0, min(3.0, dxy_change_3m_pct))
    return -clamped / 3.0 * 100.0


def _score_rates(tnx_change_3m_pp: float | None) -> float:
    """Rising 10Y yields are bearish for gold (higher opportunity cost).
    Band: ±0.5 percentage points over 3 months."""
    if tnx_change_3m_pp is None:
        return 0.0
    clamped = max(-0.5, min(0.5, tnx_change_3m_pp))
    return -clamped / 0.5 * 100.0


def _score_vix(vix_current: float | None) -> float:
    """Elevated fear (VIX) → safe-haven bid for gold. 0..+100 only
    (we don't treat low VIX as strongly bearish for gold)."""
    if vix_current is None:
        return 0.0
    if vix_current >= 35: return 100.0
    if vix_current >= 25: return 50.0
    if vix_current >= 20: return 20.0
    return 0.0


def _score_trend(
    price: float | None,
    ma_short: float | None,
    ma_long: float | None,
) -> float:
    """Price above short + long MA = uptrend (bullish). Below = downtrend."""
    if price is None:
        return 0.0
    score = 0.0
    if ma_short is not None:
        score += 50.0 if price > ma_short else -50.0
    if ma_long is not None:
        score += 50.0 if price > ma_long else -50.0
    return max(-100.0, min(100.0, score))


def classify_verdict(score: float) -> VerdictBucket:
    if score < -60: return "strong_sell"
    if score < -20: return "sell"
    if score <= 20: return "neutral"
    if score <= 60: return "buy"
    return "strong_buy"


def _factor_note(key: str, value: float | None, score: float) -> str:
    """Short human-readable explanation for each factor card."""
    if value is None:
        return "Data nejsou k dispozici."
    if key == "cot":
        if score > 50:  return f"COT Index {value:.0f}. — spekulanti v medvědím extrému, kontrariánsky býčí."
        if score > 0:   return f"COT Index {value:.0f}. — spekulanti mírně medvědí, lehce býčí tón."
        if score == 0:  return f"COT Index {value:.0f}. — neutrální pozicování."
        if score > -100:return f"COT Index {value:.0f}. — spekulanti nabíráni do longu, opatrnost."
        return f"COT Index {value:.0f}. — extrémně býčí pozicování = zvýšené riziko korekce."
    if key == "usd":
        direction = "posiluje" if value > 0 else "oslabuje" if value < 0 else "stojí"
        return f"Dolar (DXY) {direction} {value:+.1f} % za 3 měsíce. Silný dolar = tlak dolů na zlato."
    if key == "rates":
        direction = "rostou" if value > 0 else "klesají" if value < 0 else "stojí"
        return f"10Y US výnosy {direction} o {value:+.2f} p.b. za 3 měsíce. Rostoucí výnosy = konkurence pro zlato."
    if key == "vix":
        level = "klid" if value < 15 else "normál" if value < 20 else "zvýšený" if value < 25 else "strach" if value < 35 else "panika"
        return f"VIX {value:.1f} ({level}). Vyšší strach = bid na safe-haven zlato."
    if key == "trend":
        if score >= 50:  return "Cena nad 20W i 50W průměrem — silný uptrend."
        if score == 0:   return "Cena mezi průměry — smíšený trend."
        if score <= -50: return "Cena pod 20W i 50W průměrem — downtrend."
        return "Cena nad jedním z průměrů — smíšený trend."
    return ""


def compute_verdict(
    cot_index_3y: float | None,
    dxy_change_3m_pct: float | None,
    tnx_change_3m_pp: float | None,
    vix_current: float | None,
    gold_price: float | None,
    gold_ma_short: float | None,
    gold_ma_long: float | None,
    weights: dict[str, float] | None = None,
    labels: dict[str, str] | None = None,
    explanations: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Combine five factors (COT + USD + rates + VIX + trend) into one
    verdict score in -100 (strong sell) to +100 (strong buy).

    Returns a dict ready to serialize into cot_gold.json.
    """
    w = weights or DEFAULT_VERDICT_WEIGHTS
    _labels = labels or {
        "strong_sell": "SILNÝ SELL", "sell": "SELL", "neutral": "NEUTRÁL",
        "buy": "BUY", "strong_buy": "SILNÝ BUY",
    }
    _explanations = explanations or {}

    factors: dict[str, dict[str, Any]] = {}

    if cot_index_3y is not None:
        s = _score_cot_contrarian(cot_index_3y)
        factors["cot"] = {
            "label": "COT Index (kontrariánsky)",
            "score": round(s, 1),
            "value": round(cot_index_3y, 1),
            "value_label": f"{cot_index_3y:.0f}. percentil",
            "weight": w.get("cot", 0),
            "note": _factor_note("cot", cot_index_3y, s),
        }
    if dxy_change_3m_pct is not None:
        s = _score_usd(dxy_change_3m_pct)
        factors["usd"] = {
            "label": "Dolar (DXY)",
            "score": round(s, 1),
            "value": round(dxy_change_3m_pct, 2),
            "value_label": f"{dxy_change_3m_pct:+.1f} % / 3M",
            "weight": w.get("usd", 0),
            "note": _factor_note("usd", dxy_change_3m_pct, s),
        }
    if tnx_change_3m_pp is not None:
        s = _score_rates(tnx_change_3m_pp)
        factors["rates"] = {
            "label": "10Y výnosy US",
            "score": round(s, 1),
            "value": round(tnx_change_3m_pp, 3),
            "value_label": f"{tnx_change_3m_pp:+.2f} p.b. / 3M",
            "weight": w.get("rates", 0),
            "note": _factor_note("rates", tnx_change_3m_pp, s),
        }
    if gold_price is not None and (gold_ma_short is not None or gold_ma_long is not None):
        s = _score_trend(gold_price, gold_ma_short, gold_ma_long)
        factors["trend"] = {
            "label": "Trend zlata",
            "score": round(s, 1),
            "value": round(gold_price, 2),
            "value_label": f"{gold_price:.0f} USD",
            "weight": w.get("trend", 0),
            "note": _factor_note("trend", gold_price, s),
        }
    if vix_current is not None:
        s = _score_vix(vix_current)
        factors["vix"] = {
            "label": "VIX (strach na trhu)",
            "score": round(s, 1),
            "value": round(vix_current, 1),
            "value_label": f"{vix_current:.1f}",
            "weight": w.get("vix", 0),
            "note": _factor_note("vix", vix_current, s),
        }

    total_w = sum(f["weight"] for f in factors.values())
    if total_w > 0:
        raw_score = sum(f["score"] * f["weight"] for f in factors.values()) / total_w
    else:
        raw_score = 0.0
    score = round(max(-100.0, min(100.0, raw_score)), 1)
    bucket = classify_verdict(score)

    return {
        "score": score,
        "bucket": bucket,
        "label": _labels.get(bucket, bucket),
        "explanation": _explanations.get(bucket, ""),
        "factors": factors,
    }


# -------------------- SUMMARY BUILDER --------------------

def summarize(
    records: list[dict],
    config: dict[str, Any],
    macros: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """High-level helper combining indexes + projection + text. Returns the
    full payload ready to embed in the output JSON.
    """
    if not records:
        return {
            "history": [],
            "latest": None,
            "projection": {"analogies_count": 0, "horizons": {}},
            "narrative": {"past": "—", "present": "—", "future": "—"},
        }

    win = config.get("cot_index_windows", {})
    enriched = compute_indexes(
        records,
        window_6m=win.get("six_months", 26),
        window_3y=win.get("three_years", 156),
    )
    latest = enriched[-1]

    proj_cfg = config.get("projection", {})
    current_3y = latest.get("cot_index_3y")
    projection = (
        projection_bands(
            enriched,
            current_3y,
            horizons=proj_cfg.get("horizons_weeks", [4, 8]),
            tolerance=proj_cfg.get("analogy_tolerance", 5),
            percentiles=proj_cfg.get("percentiles", [25, 50, 75]),
        )
        if current_3y is not None
        else {"analogies_count": 0, "horizons": {}}
    )

    # Moving averages from the enriched price history (uses only weeks that
    # already have a price attached — older CFTC-only rows are skipped).
    price_series = [r["price_close"] for r in enriched if r.get("price_close") is not None]
    ma_windows = config.get("moving_averages_weeks", [20, 50])
    ma_short = moving_average(price_series, ma_windows[0]) if ma_windows else None
    ma_long = moving_average(price_series, ma_windows[1]) if len(ma_windows) > 1 else None

    macros = macros or {}
    verdict = compute_verdict(
        cot_index_3y=current_3y,
        dxy_change_3m_pct=macros.get("dxy_change_3m_pct"),
        tnx_change_3m_pp=macros.get("tnx_change_3m_pp"),
        vix_current=macros.get("vix_current"),
        gold_price=latest.get("price_close"),
        gold_ma_short=ma_short,
        gold_ma_long=ma_long,
        weights=config.get("verdict_weights"),
        labels=config.get("verdict_labels"),
        explanations=config.get("verdict_explanations"),
    )

    narrative = generate_text(enriched, projection, config, verdict=verdict)

    # Weekly deltas on latest row
    if len(enriched) >= 2:
        prev = enriched[-2]
        latest = dict(latest)
        latest["noncomm_net_change"] = latest["noncomm_net"] - prev["noncomm_net"]
        latest["comm_net_change"] = latest["comm_net"] - prev["comm_net"]
        latest["open_interest_change"] = latest["open_interest"] - prev["open_interest"]

    bucket = (
        classify_sentiment(current_3y, config.get("sentiment_thresholds"))
        if current_3y is not None else "neutral"
    )

    return {
        "history": enriched,
        "latest": latest,
        "projection": projection,
        "narrative": narrative,
        "sentiment": {
            "bucket": bucket,
            "label": config.get("sentiment_labels", {}).get(bucket, bucket),
        },
        "verdict": verdict,
        "macros": {
            "dxy_change_3m_pct": macros.get("dxy_change_3m_pct"),
            "tnx_change_3m_pp": macros.get("tnx_change_3m_pp"),
            "vix_current": macros.get("vix_current"),
            "gold_ma_short": ma_short,
            "gold_ma_long": ma_long,
            "ma_windows": ma_windows,
        },
    }
