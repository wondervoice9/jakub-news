"""Fetch and parse RSS feeds into normalized article dicts."""
import feedparser
import hashlib
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup


# Sport content classifiers — override the source's static `sub` when the
# article text clearly belongs to a different discipline. Sport.cz and
# iRozhlas Sport are generic feeds tagged football by default, but they
# regularly carry hockey, tennis, cycling, etc. — without these regexes
# a hockey-trainer story would land in the football bucket.
_HOCKEY_RE = re.compile(
    r"\b(hokej\w*|NHL\b|extralig\w*|hokejov\w*|Stanley\s+Cup|MS\s+v\s+hokeji|"
    r"Tipsport\s+extralig\w*|KHL\b|Komet\w*\s+Brno|T[řr]inec\s+(?:o[ck]el|hokej)|"
    r"Sparta\s+(?:hokej|Praha\s+hokej))",
    re.IGNORECASE | re.UNICODE,
)
_OTHER_SPORT_RE = re.compile(
    r"\b(tenis\w*|ATP\b|WTA\b|grand\s+slam|F1\b|formule\s+1|"
    r"Giro\b|Tour\s+de\s+France|Vuelta|cyklist\w*|atletik\w*|"
    r"UFC\b|MMA\b|box(?:er|ing)?\b|moderní\s+p[ěe]tib\w*|"
    r"biatlon\w*|ly[žz]ov\w*|sjezdov\w*|b[ěe][ž]eck\w*\s+ly[žz]\w*|"
    r"basket\w*|NBA\b|volejbal\w*|h[áa]zen\w*|florbal\w*|golf\b|plavá\w*)",
    re.IGNORECASE | re.UNICODE,
)


def _classify_sport_sub(title: str, summary: str, fallback: str | None) -> str | None:
    """Re-tag generic-feed sport articles to the right bucket by content."""
    if fallback not in ("football", "hockey", "other"):
        return fallback
    haystack = f"{title} {summary}"
    if _HOCKEY_RE.search(haystack):
        return "hockey"
    # Don't downgrade a clear hockey label, but football → other when the
    # content is plainly tennis/F1/cycling/etc.
    if fallback == "football" and _OTHER_SPORT_RE.search(haystack):
        return "other"
    return fallback


def _clean_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _parse_date(entry) -> str:
    for key in ("published", "updated", "pubDate"):
        val = entry.get(key)
        if val:
            try:
                dt = parsedate_to_datetime(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def _article_id(title: str, link: str) -> str:
    basis = (title or "") + (link or "")
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def fetch_feed(source: dict) -> list[dict]:
    """Fetch one RSS feed and return list of normalized articles."""
    try:
        parsed = feedparser.parse(source["url"])
    except Exception as e:
        print(f"  [ERROR] {source['name']}: {e}")
        return []

    articles = []
    for entry in parsed.entries:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link:
            continue

        summary = _clean_html(entry.get("summary") or entry.get("description") or "")
        # Drop stubs: articles without meaningful body text are unusable
        # (e.g. NYT live-blog anchors like "Here's the latest." with empty summary).
        if len(summary) < 30:
            continue
        if len(summary) > 500:
            summary = summary[:497] + "..."

        sub = _classify_sport_sub(title, summary, source.get("sub"))

        articles.append({
            "id": _article_id(title, link),
            "title": title,
            "summary": summary,
            "link": link,
            "published": _parse_date(entry),
            "source": source["name"],
            "lang": source["lang"],
            "sub": sub,
        })
    return articles


def fetch_category(sources: list[dict]) -> list[dict]:
    """Fetch all feeds in a category, merged."""
    all_articles = []
    for src in sources:
        print(f"  Fetching {src['name']}...")
        articles = fetch_feed(src)
        print(f"    {len(articles)} articles")
        all_articles.extend(articles)
    return all_articles
