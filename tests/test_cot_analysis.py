"""Unit tests for aggregator.cot_analysis. Run with: python -m pytest -q"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aggregator.cot_analysis import (
    classify_sentiment,
    classify_verdict,
    compute_indexes,
    compute_verdict,
    cot_index,
    generate_text,
    moving_average,
    projection_bands,
    summarize,
    _percentile,
)


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "cot_config.json"


@pytest.fixture(scope="module")
def config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


# -------------------- cot_index --------------------

class TestCotIndex:
    def test_mid_range(self):
        assert cot_index(50, [0, 25, 50, 75, 100]) == 50.0

    def test_min_bound(self):
        assert cot_index(0, [0, 25, 50, 75, 100]) == 0.0

    def test_max_bound(self):
        assert cot_index(100, [0, 25, 50, 75, 100]) == 100.0

    def test_empty_series_returns_neutral(self):
        assert cot_index(42, []) == 50.0

    def test_flat_series_returns_neutral(self):
        assert cot_index(10, [10, 10, 10]) == 50.0

    def test_value_outside_range_is_clamped(self):
        assert cot_index(200, [0, 100]) == 100.0
        assert cot_index(-50, [0, 100]) == 0.0

    def test_negative_nets(self):
        # Commercials are typically net-short (negative)
        assert cot_index(-50, [-100, -50, 0]) == 50.0


# -------------------- classify_sentiment --------------------

class TestClassifySentiment:
    @pytest.mark.parametrize("value,expected", [
        (0, "extreme_bearish"),
        (19.999, "extreme_bearish"),
        (20, "bearish"),
        (39.999, "bearish"),
        (40, "neutral"),
        (59.999, "neutral"),
        (60, "bullish"),
        (79.999, "bullish"),
        (80, "extreme_bullish"),
        (100, "extreme_bullish"),
    ])
    def test_boundaries(self, value, expected):
        assert classify_sentiment(value) == expected


# -------------------- compute_indexes --------------------

class TestComputeIndexes:
    def _make(self, nets: list[int]) -> list[dict]:
        return [
            {"report_date": f"2024-01-{i:02d}", "noncomm_net": n}
            for i, n in enumerate(nets, start=1)
        ]

    def test_last_is_largest_gives_100(self):
        recs = self._make([100, 150, 200, 250, 300])
        out = compute_indexes(recs, window_6m=5, window_3y=5, min_sample=4)
        assert out[-1]["cot_index_6m"] == 100.0

    def test_first_below_min_sample_is_none(self):
        recs = self._make([100, 150, 200, 250, 300])
        out = compute_indexes(recs, window_6m=5, window_3y=5, min_sample=4)
        assert out[0]["cot_index_6m"] is None
        assert out[2]["cot_index_6m"] is None
        assert out[3]["cot_index_6m"] is not None  # 4th week meets min_sample

    def test_rolling_window_limits_history(self):
        recs = self._make([1000, 0, 500, 100, 400])
        out = compute_indexes(recs, window_6m=3, window_3y=3, min_sample=1)
        # Last window is [500, 100, 400] → 400 sits at (400-100)/(500-100)=75
        assert out[-1]["cot_index_6m"] == pytest.approx(75.0)


# -------------------- percentile --------------------

class TestPercentile:
    def test_median_odd(self):
        assert _percentile([1, 2, 3, 4, 5], 50) == 3

    def test_median_even(self):
        assert _percentile([1, 2, 3, 4], 50) == 2.5

    def test_empty(self):
        assert _percentile([], 50) == 0.0

    def test_single(self):
        assert _percentile([7], 25) == 7


# -------------------- projection_bands --------------------

class TestProjectionBands:
    def _records(self, prices: list[float], indexes: list[float]) -> list[dict]:
        assert len(prices) == len(indexes)
        return [
            {
                "report_date": f"2024-01-{i:02d}",
                "noncomm_net": 0,
                "cot_index_3y": idx,
                "price_close": p,
            }
            for i, (idx, p) in enumerate(zip(indexes, prices), start=1)
        ]

    def test_empty(self):
        assert projection_bands([], 50)["analogies_count"] == 0

    def test_no_match_zero_analogies(self):
        recs = self._records(
            prices=[100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            indexes=[10] * 10,
        )
        out = projection_bands(recs, current_index=90, tolerance=5, horizons=[4])
        assert out["analogies_count"] == 0

    def test_rising_price_after_low_cot(self):
        # 12 weeks where COT is at 30 each time, price rises linearly
        prices = [100 + i for i in range(12)]
        recs = self._records(prices=prices, indexes=[30] * 12)
        out = projection_bands(recs, current_index=30, tolerance=5, horizons=[4])
        # analogies = indices 0..7 (need i + 4 < 12)
        assert out["analogies_count"] == 8
        h4 = out["horizons"]["4"]
        assert h4["p50_pct"] > 0  # price went up
        assert h4["hit_rate_up"] == 1.0

    def test_mixed_outcomes_produce_bands(self):
        # Analogies alternate +10% / -9%, so the band must straddle zero
        prices = [100, 110, 100, 110, 100, 110, 100, 110, 100, 110, 100, 110]
        recs = self._records(prices=prices, indexes=[50] * 12)
        out = projection_bands(recs, current_index=50, tolerance=1, horizons=[1])
        h = out["horizons"]["1"]
        assert h["p25_pct"] < 0 < h["p75_pct"]
        assert h["p25_pct"] <= h["p50_pct"] <= h["p75_pct"]
        assert 0 < h["hit_rate_up"] < 1
        assert 0 < h["hit_rate_down"] < 1

    def test_tolerance_filters_strict(self):
        indexes = [30, 30, 30, 40, 40, 40, 50, 50, 50, 60, 60, 60]
        prices = [100 + i for i in range(12)]
        recs = self._records(prices=prices, indexes=indexes)
        narrow = projection_bands(recs, current_index=50, tolerance=2, horizons=[2])
        wide = projection_bands(recs, current_index=50, tolerance=15, horizons=[2])
        assert narrow["analogies_count"] < wide["analogies_count"]


# -------------------- generate_text --------------------

class TestGenerateText:
    def _synthetic_records(self, n: int, final_index: float = 90.0) -> list[dict]:
        """n weeks with cot_index_3y climbing linearly to final_index."""
        recs = []
        for i in range(n):
            pct = i / max(1, n - 1)
            recs.append({
                "report_date": f"2024-{(i // 4) + 1:02d}-{(i % 4) * 7 + 1:02d}",
                "noncomm_net": 1000 * (i + 1),
                "cot_index_3y": round(pct * final_index, 1),
                "cot_index_6m": round(pct * final_index, 1),
                "price_close": 2000 + i * 5,
            })
        return recs

    def test_insufficient_history_fallback(self, config):
        out = generate_text([], {"analogies_count": 0, "horizons": {}}, config)
        assert "Zatím" in out["past"] or "nedost" in out["past"].lower()

    def test_extreme_bullish_bucket(self, config):
        recs = self._synthetic_records(12, final_index=90.0)
        proj = {
            "analogies_count": 12,
            "horizons": {
                "4": {"p25_pct": -5.0, "p50_pct": -2.5, "p75_pct": 1.5,
                      "hit_rate_up": 0.3, "hit_rate_down": 0.7, "samples": 12},
                "8": {"p25_pct": -8.0, "p50_pct": -4.0, "p75_pct": 0.0,
                      "hit_rate_up": 0.3, "hit_rate_down": 0.7, "samples": 12},
            },
        }
        verdict = {"label": "SELL"}
        out = generate_text(recs, proj, config, verdict=verdict)
        assert "12" in out["future"]  # analogies count is rendered
        assert "SELL" in out["future"]  # verdict label injected
        assert "-2.5" in out["future"] or "−2.5" in out["future"]

    def test_neutral_bucket(self, config):
        recs = self._synthetic_records(12, final_index=50.0)
        proj = {
            "analogies_count": 5,
            "horizons": {
                "4": {"p25_pct": -1.0, "p50_pct": 0.5, "p75_pct": 2.0,
                      "hit_rate_up": 0.6, "hit_rate_down": 0.4, "samples": 5},
                "8": {"p25_pct": -2.0, "p50_pct": 1.0, "p75_pct": 3.0,
                      "hit_rate_up": 0.6, "hit_rate_down": 0.4, "samples": 5},
            },
        }
        out = generate_text(recs, proj, config)
        assert "neutrální" in out["present"].lower() or "rovnováze" in out["present"].lower()


# -------------------- summarize (integration) --------------------

class TestSummarize:
    def test_full_pipeline(self, config):
        # 60 weeks of data, slowly rising
        records = [
            {
                "report_date": f"2024-{(i // 4) + 1:02d}-{(i % 4) * 7 + 1:02d}",
                "noncomm_long": 200_000 + i * 500,
                "noncomm_short": 50_000,
                "noncomm_net": 150_000 + i * 500,
                "comm_long": 100_000,
                "comm_short": 250_000 + i * 500,
                "comm_net": -(150_000 + i * 500),
                "open_interest": 500_000 + i * 100,
                "price_close": 2000 + i * 3,
            }
            for i in range(60)
        ]
        out = summarize(records, config)
        assert out["latest"] is not None
        assert out["latest"]["cot_index_6m"] is not None
        assert out["sentiment"]["bucket"] in {
            "extreme_bearish", "bearish", "neutral", "bullish", "extreme_bullish"
        }
        assert "past" in out["narrative"]
        assert "present" in out["narrative"]
        assert "future" in out["narrative"]

    def test_empty_input(self, config):
        out = summarize([], config)
        assert out["latest"] is None
        assert out["history"] == []

    def test_summary_includes_verdict_when_macros_given(self, config):
        records = [
            {
                "report_date": f"2024-{(i // 4) + 1:02d}-{(i % 4) * 7 + 1:02d}",
                "noncomm_long": 200_000 + i * 500,
                "noncomm_short": 50_000,
                "noncomm_net": 150_000 + i * 500,
                "comm_long": 100_000,
                "comm_short": 250_000 + i * 500,
                "comm_net": -(150_000 + i * 500),
                "open_interest": 500_000 + i * 100,
                "price_close": 2000 + i * 3,
            }
            for i in range(60)
        ]
        macros = {
            "dxy_change_3m_pct": -2.0,
            "tnx_change_3m_pp": -0.3,
            "vix_current": 28.0,
        }
        out = summarize(records, config, macros=macros)
        assert "verdict" in out
        assert out["verdict"]["bucket"] in {
            "strong_sell", "sell", "neutral", "buy", "strong_buy"
        }
        assert -100.0 <= out["verdict"]["score"] <= 100.0
        assert "factors" in out["verdict"]
        assert out["macros"]["gold_ma_short"] is not None  # 60 >= 20-week window


# -------------------- moving_average --------------------

class TestMovingAverage:
    def test_returns_none_when_too_short(self):
        assert moving_average([1, 2, 3], window=5) is None

    def test_simple_average(self):
        assert moving_average([10, 20, 30, 40, 50], window=3) == pytest.approx(40.0)

    def test_skips_nones(self):
        # Only last `window` non-None values are averaged
        assert moving_average([None, 10, None, 30, 50], window=3) == pytest.approx(30.0)

    def test_window_of_one(self):
        assert moving_average([7, 8, 9], window=1) == pytest.approx(9.0)


# -------------------- classify_verdict --------------------

class TestClassifyVerdict:
    @pytest.mark.parametrize("score,expected", [
        (-100, "strong_sell"),
        (-61, "strong_sell"),
        (-60, "sell"),
        (-21, "sell"),
        (-20, "neutral"),
        (0, "neutral"),
        (20, "neutral"),
        (21, "buy"),
        (60, "buy"),
        (61, "strong_buy"),
        (100, "strong_buy"),
    ])
    def test_buckets(self, score, expected):
        assert classify_verdict(score) == expected


# -------------------- compute_verdict --------------------

class TestComputeVerdict:
    def test_very_bullish_scenario(self, config):
        # Low COT (speculators capitulated), weak dollar, falling yields,
        # high VIX, price above both MAs → SILNÝ BUY territory
        v = compute_verdict(
            cot_index_3y=10.0,
            dxy_change_3m_pct=-2.5,
            tnx_change_3m_pp=-0.4,
            vix_current=32.0,
            gold_price=2500.0,
            gold_ma_short=2400.0,
            gold_ma_long=2300.0,
            weights=config.get("verdict_weights"),
            labels=config.get("verdict_labels"),
        )
        assert v["score"] > 60
        assert v["bucket"] == "strong_buy"
        assert v["label"] == "SILNÝ BUY"
        assert set(v["factors"].keys()) == {"cot", "usd", "rates", "vix", "trend"}

    def test_very_bearish_scenario(self, config):
        # Crowded specs, strong dollar, rising yields, calm VIX, price below MAs
        v = compute_verdict(
            cot_index_3y=90.0,
            dxy_change_3m_pct=2.8,
            tnx_change_3m_pp=0.45,
            vix_current=13.0,
            gold_price=2000.0,
            gold_ma_short=2100.0,
            gold_ma_long=2200.0,
            weights=config.get("verdict_weights"),
            labels=config.get("verdict_labels"),
        )
        assert v["score"] < -60
        assert v["bucket"] == "strong_sell"

    def test_neutral_when_nothing_known(self, config):
        v = compute_verdict(
            cot_index_3y=None,
            dxy_change_3m_pct=None,
            tnx_change_3m_pp=None,
            vix_current=None,
            gold_price=None,
            gold_ma_short=None,
            gold_ma_long=None,
            weights=config.get("verdict_weights"),
        )
        assert v["score"] == 0.0
        assert v["bucket"] == "neutral"
        assert v["factors"] == {}

    def test_partial_inputs_still_produce_score(self, config):
        # Only COT + VIX known; should still yield a weighted score
        v = compute_verdict(
            cot_index_3y=15.0,
            dxy_change_3m_pct=None,
            tnx_change_3m_pp=None,
            vix_current=30.0,
            gold_price=None,
            gold_ma_short=None,
            gold_ma_long=None,
            weights=config.get("verdict_weights"),
        )
        assert v["score"] > 0
        assert set(v["factors"].keys()) == {"cot", "vix"}

    def test_weights_are_applied(self, config):
        # All factors maximally bullish for USD only; with full weight
        # vector the score should be dominated by USD (0.25) — ≈ +25.
        v = compute_verdict(
            cot_index_3y=50.0,        # score 0 (neutral)
            dxy_change_3m_pct=-3.0,   # score +100
            tnx_change_3m_pp=0.0,     # score 0
            vix_current=15.0,         # score 0
            gold_price=2000.0,
            gold_ma_short=2000.0,     # equal price → counts as "not above" → -50
            gold_ma_long=2000.0,
            weights=config.get("verdict_weights"),
        )
        # Score must be positive (USD dominates) but not 100
        assert v["score"] > 0
        assert v["score"] < 100
