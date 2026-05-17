"""Fetch and parse RSS feeds into normalized article dicts."""
import feedparser
import hashlib
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup


# Sport content classifiers — override the source's static `sub` based
# on article text. Sport.cz and iRozhlas Sport are generic feeds tagged
# "other" by default; this routes the football-specific ones into the
# football bucket and the hockey-specific ones into hockey. Everything
# else stays in "other".

_HOCKEY_RE = re.compile(
    r"\b(hokej\w*|NHL\b|extralig\w*|hokejov\w*|Stanley\s+Cup|MS\s+v\s+hokeji|"
    r"Tipsport\s+extralig\w*|KHL\b|Komet\w*\s+Brno|T[řr]inec\s+(?:o[ck]el|hokej)|"
    r"Sparta\s+(?:hokej|Praha\s+hokej)|Dobeš\b|Pastrňák\w*|Necas\b|Hertl\b)",
    re.IGNORECASE | re.UNICODE,
)

_FOOTBALL_RE = re.compile(
    r"\b("
    # Czech terms
    r"fotbal\w*|fotbalov\w*|"
    r"Chance\s+Liga|Fortuna\s+Liga|česká\s+(?:fotbalov[aá]|reprezentac[ei])|"
    # League names
    r"Premier\s+League|Bundesliga|La\s+Liga|Serie\s+A|Ligue\s+1|"
    r"Champions\s+League|Europa\s+League|"
    # Czech clubs (football context)
    r"Slavia\s+Praha|Sparta\s+Praha\s+fotbal|Plzeň\s+fotbal|"
    # English clubs
    r"Chelsea|Arsenal|Liverpool|Manchester\s+(?:United|City)|Tottenham|"
    r"Real\s+Madrid|Barcelona\s+(?:fotbal|FC)|Bayern|"
    # Big football names
    r"Messi|Ronaldo|Haaland|Mbapp[eé]|Pep\s+Guardiola|Xabi\s+Alonso|"
    # Football-specific terms
    r"přestup\w*\s+(?:fotbal|hráč|hraj|liga|klub)|"
    r"střelec\w*\s+ligy|gól\s+(?:vyhrál|prohra)|penalt\w*\s+kop"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)

_OTHER_SPORT_RE = re.compile(
    r"\b("
    # Tennis
    r"tenis\w*|ATP\b|WTA\b|grand\s+slam|Roland\s+Garros|Wimbledon|"
    # Motorsport
    r"F1\b|formule\s+1|MotoGP\b|Moto2\b|Moto3\b|motork\w*|motocykl\w*|"
    r"Dakar|Salač\b|Loprais\w*|Marquez|Verstappen|"
    # Cycling
    r"cyklist\w*|Giro\b|Tour\s+de\s+France|Vuelta|"
    # Athletics
    r"atletik\w*|oštěp\w*|Vadlejch\w*|sprint\w*|maratón\w*|"
    # Combat sports
    r"UFC\b|MMA\b|box(?:er|ing|u)?\b|zápas\w*\s+v\s+kleci|"
    # Multi-sport
    r"moderní\s+p[ěe]tib\w*|Hlaváčk\w*|"
    # Water sports
    r"kajak\w*|kanoe?\w*|veslo\w*|vodní\s+slalom|plavá\w*|plave\w*|"
    r"Dostál\w*|"
    # Winter sports
    r"biatlon\w*|ly[žz]ov\w*|sjezdov\w*|b[ěe][ž]eck\w*\s+ly[žz]\w*|"
    r"sk[oi]\s+jump|skokan\w*|"
    # Team sports (non-football/hockey)
    r"basket\w*|NBA\b|volejbal\w*|h[áa]zen\w*|florbal\w*|"
    # Individual sports
    r"golf\w*|šach\w*|squash\w*|"
    # General race / sport terms
    r"Světový\s+pohár|světový\s+rekord"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)


def _classify_sport_sub(title: str, summary: str, fallback: str | None) -> str | None:
    """Re-tag sport articles based on content keywords.

    Priority order:
      1. Hockey keywords → hockey
      2. Football keywords → football
      3. Other-sport keywords → other
      4. Keep fallback (source's default)
    """
    if fallback not in ("football", "hockey", "other"):
        return fallback
    haystack = f"{title} {summary}"
    if _HOCKEY_RE.search(haystack):
        return "hockey"
    if _FOOTBALL_RE.search(haystack):
        return "football"
    if _OTHER_SPORT_RE.search(haystack):
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
