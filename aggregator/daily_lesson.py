"""Daily lesson — jedna zajímavost z historie, geografie, vědy, techniky, ekonomiky.

Zdroj: kurátorovaný seznam širokých témat z cs.wikipedia (lesson_topics.py).
Stabilní výběr podle dne (datum = seed).
"""
import random
import urllib.parse
import requests
from datetime import datetime

from .lesson_topics import LESSON_TOPICS

WIKI_HEADERS = {"User-Agent": "JakubNews/1.0 (wondervoice9@gmail.com)"}
WIKI_REST = "https://cs.wikipedia.org/api/rest_v1"


def _seeded_random() -> random.Random:
    return random.Random(datetime.now().strftime("%Y%m%d"))


def _fetch_summary(title: str) -> dict | None:
    """Stáhne shrnutí článku podle přesného názvu."""
    slug = urllib.parse.quote(title.replace(" ", "_"))
    url = f"{WIKI_REST}/page/summary/{slug}"
    try:
        r = requests.get(url, headers=WIKI_HEADERS, timeout=12)
        if r.status_code != 200:
            return None
        d = r.json()
        extract = (d.get("extract") or "").strip()
        if len(extract) < 140:
            return None
        if extract.lower().startswith("rozcestník"):
            return None
        return {
            "title": d.get("title", title),
            "text": extract,
            "url": (d.get("content_urls") or {}).get("desktop", {}).get("page", ""),
            "thumbnail": (d.get("thumbnail") or {}).get("source", ""),
        }
    except Exception as e:
        print(f"    [lesson fetch '{title}' error] {e}")
        return None


def fetch_daily_lesson() -> dict:
    """Vybere jedno kurátorované téma pro dnešek a stáhne jeho shrnutí z cs.wiki."""
    rng = _seeded_random()
    order = LESSON_TOPICS[:]
    rng.shuffle(order)
    for title in order[:12]:
        data = _fetch_summary(title)
        if data:
            return {
                "id": f"lesson_{datetime.now():%Y%m%d}",
                **data,
                "source": "Wikipedia (cs)",
            }
    return {"title": "", "text": "", "url": "", "error": "no topic summary available"}
