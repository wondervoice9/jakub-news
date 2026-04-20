"""Fetch and parse RSS feeds into normalized article dicts."""
import feedparser
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup


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

        articles.append({
            "id": _article_id(title, link),
            "title": title,
            "summary": summary,
            "link": link,
            "published": _parse_date(entry),
            "source": source["name"],
            "lang": source["lang"],
            "sub": source.get("sub"),
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
