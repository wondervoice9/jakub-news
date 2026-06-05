"""Main aggregator entrypoint. Produces data/data.json."""
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Use OS trust store for SSL — works around Python 3.13+ strict cert validation
# that rejects several Czech servers' certificates (e.g. iRozhlas).
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# Force UTF-8 stdout on Windows (prevents cp1252 crash on Czech chars)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

from aggregator.sources import SOURCES, LIMITS, WEATHER_LOCATION
from aggregator.rss_fetcher import fetch_category
from aggregator.dedup import dedup
from aggregator.translator import translate_articles
from aggregator.gemini_filter import filter_czech, filter_good_news, filter_disturbing
from aggregator.keyword_filter import filter_keyword
from aggregator.extras import (
    fetch_weather, fetch_nameday, fetch_world_holiday, today_info,
    fetch_joke_en, fetch_joke_cs, fetch_quote,
)
from aggregator.sports_fixtures import fetch_today_fixtures
from aggregator.daily_lesson import fetch_daily_lesson
from aggregator.events import fetch_all_events
from aggregator.falco import fetch_falco


def _sort_by_date(articles: list[dict]) -> list[dict]:
    return sorted(articles, key=lambda a: a.get("published", ""), reverse=True)


def _prioritize_sport(articles: list[dict], limit: int) -> list[dict]:
    """Football first, then hockey, then everything else (tennis, F1, basketball, …)."""
    priorities = {"football": 0, "hockey": 1, "other": 2}
    buckets = {0: [], 1: [], 2: []}
    for a in articles:
        p = priorities.get(a.get("sub"), 2)
        buckets[p].append(a)
    # Football 50%, hockey 25%, other 25%
    f_take = int(limit * 0.50)
    h_take = int(limit * 0.25)
    r_take = limit - f_take - h_take
    result = buckets[0][:f_take] + buckets[1][:h_take] + buckets[2][:r_take]
    # If any bucket was short, top up from remaining pool
    remaining = limit - len(result)
    if remaining > 0:
        leftovers = (buckets[0][f_take:] + buckets[1][h_take:] + buckets[2][r_take:])
        result += leftovers[:remaining]
    return result


def _prioritize_tech(articles: list[dict], limit: int) -> list[dict]:
    """AI first, then startups, then robotics."""
    priorities = {"ai": 0, "startups": 1, "robotics": 2}
    buckets = {0: [], 1: [], 2: []}
    for a in articles:
        p = priorities.get(a.get("sub"), 1)
        buckets[p].append(a)
    ai_take = int(limit * 0.60)
    sp_take = int(limit * 0.25)
    rb_take = limit - ai_take - sp_take
    result = buckets[0][:ai_take] + buckets[1][:sp_take] + buckets[2][:rb_take]
    remaining = limit - len(result)
    if remaining > 0:
        leftovers = (buckets[0][ai_take:] + buckets[1][sp_take:] + buckets[2][rb_take:])
        result += leftovers[:remaining]
    return result


def _prioritize_culture(articles: list[dict], limit: int) -> list[dict]:
    """Music + film first, Linkin Park + Oasis at the end."""
    priorities = {"music": 0, "film": 1, "linkin_park": 2, "oasis": 3}
    buckets = {0: [], 1: [], 2: [], 3: []}
    for a in articles:
        p = priorities.get(a.get("sub"), 0)
        buckets[p].append(a)
    # Distribution: music 40%, film 30%, LP 15%, Oasis 15%
    m_take = int(limit * 0.40)
    f_take = int(limit * 0.30)
    lp_take = int(limit * 0.15)
    oa_take = limit - m_take - f_take - lp_take
    result = (buckets[0][:m_take] + buckets[1][:f_take]
              + buckets[2][:lp_take] + buckets[3][:oa_take])
    remaining = limit - len(result)
    if remaining > 0:
        leftovers = (buckets[0][m_take:] + buckets[1][f_take:]
                     + buckets[2][lp_take:] + buckets[3][oa_take:])
        result += leftovers[:remaining]
    return result


def _diversify_by_source(articles: list[dict], limit: int) -> list[dict]:
    """Round-robin across sources so the top-N isn't dominated by one outlet.

    Articles are expected newest-first; recency order within each source is
    preserved. Picks one article per source in turn until `limit` is reached —
    gives a flat "top news from various sources" list.
    """
    buckets: dict[str, list[dict]] = {}
    order: list[str] = []
    for a in articles:
        src = a.get("source", "")
        if src not in buckets:
            buckets[src] = []
            order.append(src)
        buckets[src].append(a)
    result: list[dict] = []
    while len(result) < limit:
        progressed = False
        for src in order:
            q = buckets[src]
            if q:
                result.append(q.pop(0))
                progressed = True
                if len(result) >= limit:
                    break
        if not progressed:
            break
    return result


def build_tab(name: str, sources: list[dict]) -> list[dict]:
    print(f"\n=== TAB: {name} ===")
    articles = fetch_category(sources)
    print(f"  Total fetched: {len(articles)}")

    articles = dedup(articles)
    print(f"  After dedup: {len(articles)}")

    articles = _sort_by_date(articles)

    # Stage 1: free, deterministic keyword filter (runs even when Gemini is down)
    articles = filter_keyword(articles)

    # Stage 2: Gemini-based filters (more nuanced, but rate-limited)
    articles = filter_disturbing(articles)
    if name == "czech":
        articles = filter_czech(articles)
    elif name == "good_news":
        articles = filter_good_news(articles)

    limit = LIMITS.get(name, 10)

    if name == "sport":
        articles = _prioritize_sport(articles, limit)
    elif name == "tech":
        articles = _prioritize_tech(articles, limit)
    elif name == "culture":
        articles = _prioritize_culture(articles, limit)
    elif name in ("world", "czech"):
        # Flat list of the top-N, spread across sources (no subcategories).
        articles = _diversify_by_source(articles, limit)
    else:
        articles = articles[:limit]

    print(f"  Translating to Czech ({sum(1 for a in articles if a['lang'] == 'en')} EN articles)...")
    articles = translate_articles(articles)

    print(f"  Final: {len(articles)} articles")
    return articles


def main():
    tabs = {}
    for name, sources in SOURCES.items():
        tabs[name] = build_tab(name, sources)

    print("\n=== EXTRAS ===")
    print("  Weather...")
    weather = fetch_weather(
        WEATHER_LOCATION["latitude"],
        WEATHER_LOCATION["longitude"],
        WEATHER_LOCATION["name"],
    )
    print("  Nameday...")
    nameday = fetch_nameday()
    print("  World holiday...")
    world_holiday = fetch_world_holiday()
    print("  Joke EN...")
    joke_en = fetch_joke_en()
    print("  Joke CS...")
    joke_cs = fetch_joke_cs()
    print("  Quote...")
    quote = fetch_quote()
    print("  Sport fixtures...")
    sport_fixtures = fetch_today_fixtures()
    print("  Daily lesson...")
    lesson = fetch_daily_lesson()

    # Events tab (Liberec region + surroundings within ~1h drive)
    events = fetch_all_events()

    # Falco — Vratliga images (schedule, current round, standings, scorers)
    print("  Falco (Vratliga)...")
    falco = fetch_falco()

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "today": today_info(),
        "nameday": nameday,
        "world_holiday": world_holiday,
        "weather": weather,
        "joke_en": joke_en,
        "joke_cs": joke_cs,
        "quote": quote,
        "lesson": lesson,
        "sport_fixtures": sport_fixtures,
        "events": events,
        "falco": falco,
        "tabs": tabs,
    }

    root = Path(__file__).parent.parent
    out_file = root / "frontend" / "data.json"
    out_file.parent.mkdir(exist_ok=True)
    out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ Wrote {out_file}")


if __name__ == "__main__":
    main()
