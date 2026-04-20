"""COT Gold fetcher — downloads weekly COT data + price history and
writes frontend/cot_gold.json.

Run with:
    python -m aggregator.cot_fetcher

The script is idempotent and incremental:
- Existing cot_gold.json is loaded and its history is preserved.
- Only new weeks are appended; prices get refreshed for the tail window.
- Analysis (COT Index, projection, narrative) is re-computed from scratch
  each run.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# Force UTF-8 on Windows stdout (matches aggregator.main)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from aggregator.cot_analysis import summarize


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "cot_config.json"
OUT_PATH = ROOT / "frontend" / "cot_gold.json"

CFTC_SOCRATA_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"


# -------------------- CONFIG --------------------

def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


# -------------------- CFTC FETCH --------------------

def fetch_cot_rows(cftc_code: str, limit: int = 200, max_retries: int = 4) -> list[dict]:
    """Download raw COT rows from CFTC Socrata (Legacy Futures-Only dataset).

    Retries with exponential backoff. Raises the last exception on failure.
    """
    params = {
        "cftc_contract_market_code": cftc_code,
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": limit,
    }
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            r = requests.get(CFTC_SOCRATA_URL, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last_err = e
            wait = 2 ** attempt
            print(f"  [retry {attempt + 1}/{max_retries}] CFTC fetch failed: {e}; waiting {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"CFTC fetch failed after {max_retries} attempts: {last_err}")


def _to_int(value) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def normalize_cot_row(raw: dict) -> dict:
    """Convert a raw Socrata row into our compact schema."""
    date_raw = raw.get("report_date_as_yyyy_mm_dd", "") or ""
    report_date = date_raw[:10]  # "2026-04-14T00:00:00.000" -> "2026-04-14"

    nc_long = _to_int(raw.get("noncomm_positions_long_all"))
    nc_short = _to_int(raw.get("noncomm_positions_short_all"))
    c_long = _to_int(raw.get("comm_positions_long_all"))
    c_short = _to_int(raw.get("comm_positions_short_all"))
    oi = _to_int(raw.get("open_interest_all"))

    return {
        "report_date": report_date,
        "open_interest": oi,
        "noncomm_long": nc_long,
        "noncomm_short": nc_short,
        "noncomm_net": nc_long - nc_short,
        "comm_long": c_long,
        "comm_short": c_short,
        "comm_net": c_long - c_short,
    }


# -------------------- GOLD PRICES --------------------

def fetch_gold_daily_prices(symbol: str, years: int, max_retries: int = 3) -> dict[str, float]:
    """Return {YYYY-MM-DD: close_price} for the symbol (daily interval).

    We use yfinance lazily so that a missing dependency fails only when the
    fetcher is actually run (unit tests don't need it).
    """
    import yfinance as yf  # type: ignore

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=f"{years}y", interval="1d", auto_adjust=False)
            if hist is None or hist.empty:
                raise RuntimeError("yfinance returned empty frame")
            out: dict[str, float] = {}
            for ts, row in hist.iterrows():
                close = row.get("Close")
                if close is None:
                    continue
                out[ts.date().isoformat()] = float(close)
            return out
        except Exception as e:  # yfinance throws various; keep it broad
            last_err = e
            wait = 2 ** attempt
            print(f"  [retry {attempt + 1}/{max_retries}] price fetch failed: {e}; waiting {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Price fetch failed after {max_retries} attempts: {last_err}")


def fetch_macro_snapshot(symbols: dict[str, str], max_retries: int = 3) -> dict[str, float | None]:
    """Fetch current + 3-months-ago values for DXY, TNX, VIX from yfinance
    and return normalized metrics used by the verdict.

    Returns a dict with keys:
      - dxy_change_3m_pct  (percent change of the dollar index over ~3M)
      - tnx_change_3m_pp   (10Y yield change in percentage points; yfinance
                             reports ^TNX in tenths-of-percent, e.g. 43.2 = 4.32 %)
      - vix_current        (current VIX close)
    Any missing/failed ticker becomes None and is handled gracefully downstream.
    """
    import yfinance as yf  # type: ignore

    def _last_and_3m_ago(symbol: str) -> tuple[float | None, float | None]:
        for attempt in range(max_retries):
            try:
                hist = yf.Ticker(symbol).history(period="4mo", interval="1d", auto_adjust=False)
                if hist is None or hist.empty:
                    raise RuntimeError(f"empty history for {symbol}")
                closes: list[tuple[str, float]] = []
                for ts, row in hist.iterrows():
                    close = row.get("Close")
                    if close is None:
                        continue
                    closes.append((ts.date().isoformat(), float(close)))
                if not closes:
                    return None, None
                closes.sort()
                last_val = closes[-1][1]
                # ~3 months ≈ 63 trading days; clamp if history is shorter
                idx_3m = max(0, len(closes) - 63)
                prev_val = closes[idx_3m][1]
                return last_val, prev_val
            except Exception as e:
                wait = 2 ** attempt
                print(f"  [retry {attempt + 1}/{max_retries}] macro fetch {symbol} failed: {e}; waiting {wait}s")
                time.sleep(wait)
        print(f"  ! macro fetch {symbol} gave up — treating as unknown")
        return None, None

    dxy_last, dxy_prev = _last_and_3m_ago(symbols.get("dxy", "DX-Y.NYB"))
    tnx_last, tnx_prev = _last_and_3m_ago(symbols.get("tnx", "^TNX"))
    vix_last, _ = _last_and_3m_ago(symbols.get("vix", "^VIX"))

    dxy_change_3m_pct: float | None = None
    if dxy_last is not None and dxy_prev and dxy_prev > 0:
        dxy_change_3m_pct = (dxy_last - dxy_prev) / dxy_prev * 100.0

    tnx_change_3m_pp: float | None = None
    if tnx_last is not None and tnx_prev is not None:
        # ^TNX is quoted as yield × 10 (e.g. 43.2 = 4.32 %). Divide to get real pp.
        tnx_change_3m_pp = (tnx_last - tnx_prev) / 10.0

    return {
        "dxy_current": dxy_last,
        "dxy_3m_ago": dxy_prev,
        "dxy_change_3m_pct": dxy_change_3m_pct,
        "tnx_current": (tnx_last / 10.0) if tnx_last is not None else None,
        "tnx_3m_ago": (tnx_prev / 10.0) if tnx_prev is not None else None,
        "tnx_change_3m_pp": tnx_change_3m_pp,
        "vix_current": vix_last,
    }


def match_price_for_tuesday(prices: dict[str, float], tuesday_iso: str) -> float | None:
    """For a COT Tuesday, return the Friday close of the same week.

    Falls back to the nearest earlier trading day (Thu/Wed/Tue) when the
    Friday is missing (holiday, incomplete current week).
    """
    try:
        tue = datetime.fromisoformat(tuesday_iso).date()
    except ValueError:
        return None
    target = tue + timedelta(days=3)  # Friday
    for offset in range(0, 7):  # Fri, Thu, Wed, Tue, Mon, Sun, Sat
        candidate = (target - timedelta(days=offset)).isoformat()
        if candidate in prices:
            return prices[candidate]
    return None


# -------------------- MERGE + PERSIST --------------------

def load_existing() -> dict:
    if not OUT_PATH.exists():
        return {}
    try:
        return json.loads(OUT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def merge_history(existing: list[dict], fresh: list[dict]) -> list[dict]:
    """Merge by report_date (fresh wins on collisions). Sorted ascending."""
    by_date: dict[str, dict] = {r["report_date"]: r for r in existing}
    for r in fresh:
        by_date[r["report_date"]] = r
    merged = [by_date[d] for d in sorted(by_date.keys())]
    return merged


def main() -> int:
    print("=== COT Gold fetcher ===")
    config = load_config()
    instrument = config["instrument"]
    history_weeks = config.get("history_weeks", 156)

    print(f"  Instrument: {instrument['display_name']} (CFTC {instrument['cftc_code']})")

    # 1) CFTC data
    print("  Downloading CFTC report rows...")
    raw_rows = fetch_cot_rows(instrument["cftc_code"], limit=history_weeks + 10)
    fresh_cot = [normalize_cot_row(r) for r in raw_rows if r.get("report_date_as_yyyy_mm_dd")]
    print(f"  Received {len(fresh_cot)} COT rows")

    # 2) Merge with persisted history
    existing_blob = load_existing()
    existing_history = existing_blob.get("history", [])
    merged = merge_history(existing_history, fresh_cot)

    # Trim to keep the rolling window tidy (plus a few extra for safety)
    if len(merged) > history_weeks + 20:
        merged = merged[-(history_weeks + 20):]
    print(f"  History size after merge: {len(merged)}")

    # 3) Gold prices — always refresh the full window so weekly deltas stay correct
    print("  Downloading Gold futures prices (yfinance)...")
    daily_prices = fetch_gold_daily_prices(instrument["yfinance_symbol"], years=(history_weeks // 52) + 1)
    print(f"  Received {len(daily_prices)} daily closes")

    for rec in merged:
        rec["price_close"] = match_price_for_tuesday(daily_prices, rec["report_date"])

    # 4) Macro snapshot (DXY, 10Y yields, VIX) — drives the SELL/BUY verdict
    print("  Downloading macro snapshot (DXY / 10Y / VIX)...")
    try:
        macro_snapshot = fetch_macro_snapshot(config.get("macro_symbols", {}))
    except Exception as e:
        print(f"  ! macro snapshot failed entirely: {e}; verdict will fall back to neutral")
        macro_snapshot = {
            "dxy_change_3m_pct": None,
            "tnx_change_3m_pp": None,
            "vix_current": None,
        }
    print(
        "  Macros: "
        f"DXY Δ3M={macro_snapshot.get('dxy_change_3m_pct')}, "
        f"TNX Δ3M pp={macro_snapshot.get('tnx_change_3m_pp')}, "
        f"VIX={macro_snapshot.get('vix_current')}"
    )

    # 5) Analysis
    print("  Running analysis (COT Index, projection bands, narrative, verdict)...")
    summary = summarize(merged, config, macros=macro_snapshot)

    # 6) Build output payload
    now_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    last_report_date = merged[-1]["report_date"] if merged else None

    payload = {
        "meta": {
            "last_fetch_attempt_utc": now_utc,
            "last_successful_fetch_utc": now_utc,
            "last_report_date": last_report_date,
            "cftc_code": instrument["cftc_code"],
            "instrument_name": instrument["name"],
            "display_name": instrument["display_name"],
        },
        "latest": summary["latest"],
        "sentiment": summary["sentiment"],
        "projection": summary["projection"],
        "narrative": summary["narrative"],
        "verdict": summary["verdict"],
        "macros": {**summary["macros"], **macro_snapshot},
        "history": summary["history"],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ Wrote {OUT_PATH}")
    print(f"  Report date: {last_report_date}")
    if summary["latest"]:
        print(f"  COT Index 3Y: {summary['latest'].get('cot_index_3y')}")
        print(f"  Sentiment:    {summary['sentiment']['label']}")
        print(f"  Analogies:    {summary['projection']['analogies_count']}")
        print(f"  Verdict:      {summary['verdict']['label']} (score {summary['verdict']['score']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
