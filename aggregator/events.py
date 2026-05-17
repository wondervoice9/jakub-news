"""Events aggregator for Liberec region + surroundings (within ~1h drive).

Strategy — three layers:
  A) Structured calendars (aggregators + city websites)     → precise date/place
  B) Google News RSS per city + keyword                      → event "tips" from media
  C) Dedup and merge into one list, sorted by date

Each fetcher is wrapped in try/except so one broken site doesn't break the run.
"""
from __future__ import annotations

import re
import hashlib
from datetime import datetime, date, timedelta
from typing import Optional
from urllib.parse import urljoin, urlencode, quote

import requests
import feedparser
from bs4 import BeautifulSoup


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
}
TIMEOUT = 15

# Cities using the "vismo" template (URL pattern: */vismo/kalendar-akci.asp)
CITY_VISMO = [
    {"city": "Jablonné v Podještědí",
     "url": "https://www.jvpmesto.cz/vismo/kalendar-akci.asp"},
    {"city": "Semily",
     "url": "https://www.semily.cz/vismo/kalendar-akci.asp"},
    {"city": "Česká Lípa",
     "url": "https://www.mucl.cz/vismo/kalendar.asp"},
    {"city": "Nový Bor",
     "url": "https://www.novy-bor.cz/vismo/kalendar-akci.asp"},
    {"city": "Doksy",
     "url": "https://www.mesto-doksy.cz/kalendar-udalosti"},
    {"city": "Mladá Boleslav",
     "url": "https://www.mb-net.cz/vismo/kalendar.asp"},
]

# Cities using the "redakce" template (URL pattern: */redakce/index.php?subakce=events)
# Jablonec excluded — uses Drupal portal that redirects to 365jablonec.cz (custom handler below)
CITY_REDAKCE = [
    {"city": "Turnov",
     "url": "https://www.turnov.cz/redakce/index.php?subakce=events&lanG=cs"},
    {"city": "Frýdlant",
     "url": "https://www.mesto-frydlant.cz/redakce/index.php?subakce=events&lanG=cs"},
    {"city": "Tanvald",
     "url": "https://www.tanvald.eu/redakce/index.php?subakce=events&lanG=cs"},
    {"city": "Hejnice",
     "url": "https://www.mestohejnice.cz/redakce/index.php?subakce=events&lanG=cs"},
]

# Google News RSS — cities to query for event mentions in Czech media
GNEWS_CITIES = [
    "Liberec", "Jablonec nad Nisou", "Turnov", "Frýdlant", "Hejnice",
    "Jablonné v Podještědí", "Semily", "Železný Brod", "Hrádek nad Nisou",
    "Nový Bor", "Česká Lípa", "Tanvald", "Doksy", "Vratislavice",
    "Mladá Boleslav", "Mnichovo Hradiště",
]
GNEWS_KEYWORDS = ["akce", "koncert", "festival", "výstava"]


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _get(url: str) -> Optional[str]:
    """Fetch URL, return HTML text or None on any error."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        # Some old Czech sites mislabel encoding; let BS4 detect from <meta>
        r.encoding = r.apparent_encoding or r.encoding
        return r.text
    except Exception as e:
        print(f"    [http error {url[:60]}] {e}")
        return None


_DATE_RE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


def _parse_cz_date(text: str) -> Optional[str]:
    """Extract first DD.MM.YYYY date from text, return YYYY-MM-DD or None."""
    if not text:
        return None
    m = _DATE_RE.search(text)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def _parse_cz_time(text: str) -> Optional[str]:
    if not text:
        return None
    m = _TIME_RE.search(text)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if 0 <= h < 24 and 0 <= mi < 60:
        return f"{h:02d}:{mi:02d}"
    return None


def _event_id(title: str, url: str) -> str:
    """Stable hash for dedup."""
    base = (title + "|" + url).lower().strip()
    return hashlib.md5(base.encode("utf-8")).hexdigest()[:12]


# Cities that count as "Liberec" itself (city centre + městské obvody)
_LIBEREC_CITIES = {"liberec", "vratislavice nad nisou"}
# Cities that count as Praha (the AI/tech events get region from their city)
_PRAHA_CITIES = {"praha"}


def _derive_region(city: str, override: Optional[str] = None) -> str:
    """Map city name to a region bucket used by UI filter chips:
       'liberec' | 'liberec_okoli' | 'praha'.
       Override lets a fetcher force a region (e.g. AI events without a clear city).
    """
    if override:
        return override
    c = (city or "").strip().lower()
    if c in _LIBEREC_CITIES:
        return "liberec"
    if c in _PRAHA_CITIES:
        return "praha"
    # Everything else from the Liberec region (Jablonec, Turnov, kraj…) → okolí
    return "liberec_okoli"


def _make_event(title: str, url: str, city: str, source: str,
                date_iso: Optional[str] = None, time: Optional[str] = None,
                place: Optional[str] = None, category: Optional[str] = None,
                is_tip: bool = False, region: Optional[str] = None) -> dict:
    title = (title or "").strip()
    return {
        "id": _event_id(title, url),
        "title": title,
        "city": city,
        "place": (place or "").strip() or None,
        "date": date_iso,           # YYYY-MM-DD or None
        "time": time,               # HH:MM or None
        "url": url,
        "source": source,
        "category": (category or "").strip() or None,
        "is_tip": is_tip,           # True = Google News tip, False = structured calendar
        "region": _derive_region(city, region),  # 'liberec' | 'liberec_okoli' | 'praha'
    }


# ----------------------------------------------------------------------------
# Aggregator scrapers (5 main sources)
# ----------------------------------------------------------------------------

def fetch_kraj_lbc() -> list[dict]:
    """Official Liberec region calendar — covers all towns in Liberecký kraj."""
    url = "https://kalendar.kraj-lbc.cz/"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    # Each event typically inside <article> or <li> with an h3/h2 title link
    for h in soup.find_all(["h2", "h3"]):
        a = h.find("a", href=True)
        if not a:
            continue
        title = a.get_text(strip=True)
        href = urljoin(url, a["href"])
        # Walk up to find sibling text with date/place
        block = h.find_parent(["article", "li", "div"]) or h.parent
        text = block.get_text(" ", strip=True) if block else title
        out.append(_make_event(
            title=title,
            url=href,
            city="Liberecký kraj",
            source="Kalendář Libereckého kraje",
            date_iso=_parse_cz_date(text),
            time=_parse_cz_time(text),
        ))
    return out


def fetch_zivyliberec() -> list[dict]:
    """Živá kultura Liberec — large aggregator (300+ events)."""
    url = "https://zivyliberec.cz/"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    # Events link to /akce/{id}
    for a in soup.select('a[href*="/akce/"]'):
        href = a.get("href", "")
        if not re.search(r"/akce/\d+", href):
            continue
        full_url = urljoin(url, href)
        title = a.get_text(" ", strip=True)
        # Skip nav links / very short ones
        if len(title) < 5 or title.lower() in ("akce", "více"):
            continue
        # Date often in parent block
        block = a.find_parent(["article", "li", "div"]) or a
        text = block.get_text(" ", strip=True)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Liberec",
            source="Živá kultura Liberec",
            date_iso=_parse_cz_date(text),
            time=_parse_cz_time(text),
        ))
    return out


def fetch_iliberecko() -> list[dict]:
    """iLIBERECKO.cz — local news portal with event calendar."""
    url = "https://www.iliberecko.cz/kalendar-akci"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        # Heuristic: event detail URLs contain "/kalendar-akci/" or "/akce/"
        if "kalendar-akci/" not in href and "/akce/" not in href:
            continue
        if href.rstrip("/").endswith("kalendar-akci"):
            continue  # skip the listing page itself
        title = a.get_text(" ", strip=True)
        if len(title) < 5:
            continue
        full_url = urljoin(url, href)
        block = a.find_parent(["article", "li", "div"]) or a
        text = block.get_text(" ", strip=True)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Liberecký kraj",
            source="iLIBERECKO",
            date_iso=_parse_cz_date(text),
            time=_parse_cz_time(text),
        ))
    return out


def fetch_kudyznudy() -> list[dict]:
    """Kudy z nudy — state tourism portal, Liberecký kraj filter."""
    url = "https://www.kudyznudy.cz/kalendar-akci/liberecky-kraj"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    # Cards usually have a class containing "card" or are <article>
    for art in soup.find_all(["article", "div"], class_=re.compile(r"card|item|tile", re.I)):
        a = art.find("a", href=True)
        if not a:
            continue
        title_el = art.find(["h2", "h3", "h4"])
        title = (title_el.get_text(strip=True) if title_el else a.get_text(strip=True))
        if len(title) < 5:
            continue
        full_url = urljoin(url, a["href"])
        text = art.get_text(" ", strip=True)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Liberecký kraj",
            source="Kudy z nudy",
            date_iso=_parse_cz_date(text),
            time=_parse_cz_time(text),
        ))
    return out


def fetch_goout_liberec() -> list[dict]:
    """GoOut Liberec — concerts, theater, clubs (commercial)."""
    url = "https://goout.net/cs/liberec/akce/lezwawlkk/"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.select('a[href*="/cs/"]'):
        href = a.get("href", "")
        # GoOut event URLs: /cs/<artist>/<event>/<hash>/
        if href.count("/") < 4 or "/akce/" in href or "/liberec/" in href:
            continue
        title = a.get_text(" ", strip=True)
        if len(title) < 5:
            continue
        full_url = urljoin(url, href)
        block = a.find_parent(["article", "li", "div"]) or a
        text = block.get_text(" ", strip=True)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Liberec",
            source="GoOut",
            date_iso=_parse_cz_date(text),
            time=_parse_cz_time(text),
            category="Koncert/divadlo",
        ))
    return out


# ----------------------------------------------------------------------------
# City template scrapers (handle multiple cities each)
# ----------------------------------------------------------------------------

def _fetch_vismo(city: str, url: str) -> list[dict]:
    """Vismo template — events as <a> with nearby bolded date.

    Structure varies, so we use a permissive pass: find all anchors whose
    parent block contains a Czech date pattern.
    """
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()
    # Look for event links — vismo typically has /vismo/dokumenty2.asp or /dokumenty/
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(" ", strip=True)
        if len(title) < 8 or title.lower() in ("více", "detail", "zpět"):
            continue
        # Walk up to find a block with a date
        block = a.find_parent(["li", "tr", "div", "article"])
        if not block:
            continue
        text = block.get_text(" ", strip=True)
        date_iso = _parse_cz_date(text)
        if not date_iso:
            continue
        # Skip past events (older than 7 days)
        try:
            evd = date.fromisoformat(date_iso)
            if evd < date.today() - timedelta(days=1):
                continue
        except ValueError:
            pass
        full_url = urljoin(url, href)
        key = (title[:80], date_iso)
        if key in seen:
            continue
        seen.add(key)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city=city,
            source=f"{city} (oficiální web)",
            date_iso=date_iso,
            time=_parse_cz_time(text),
        ))
    return out


def _fetch_redakce(city: str, url: str) -> list[dict]:
    """Redakce template — events as <a> with <h4> title and date below."""
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()
    for a in soup.find_all("a", href=True):
        h = a.find(["h2", "h3", "h4"])
        if not h:
            continue
        title = h.get_text(" ", strip=True)
        if len(title) < 5:
            continue
        text = a.get_text(" ", strip=True)
        date_iso = _parse_cz_date(text)
        if not date_iso:
            continue
        try:
            evd = date.fromisoformat(date_iso)
            if evd < date.today() - timedelta(days=1):
                continue
        except ValueError:
            pass
        full_url = urljoin(url, a["href"])
        key = (title[:80], date_iso)
        if key in seen:
            continue
        seen.add(key)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city=city,
            source=f"{city} (oficiální web)",
            date_iso=date_iso,
            time=_parse_cz_time(text),
        ))
    return out


# ----------------------------------------------------------------------------
# Custom per-city scrapers
# ----------------------------------------------------------------------------

def fetch_zeleznybrod() -> list[dict]:
    """Železný Brod — custom calendar with image-based event tiles."""
    url = "https://www.zeleznybrod.cz/cz/aktualne/kalendar-akci/"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.select('a[href*="detail-akce"]'):
        href = a["href"]
        img = a.find("img")
        title = (img.get("alt") if img else a.get_text(strip=True)) or ""
        if len(title) < 3:
            continue
        full_url = urljoin(url, href)
        # Date often encoded in image filename (o_YYYY_MM_DD_*)
        date_iso = None
        if img:
            m = re.search(r"o_(\d{4})_(\d{2})_(\d{2})", img.get("src", ""))
            if m:
                date_iso = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Železný Brod",
            source="Železný Brod (oficiální web)",
            date_iso=date_iso,
        ))
    return out


def fetch_hradek() -> list[dict]:
    """Hrádek nad Nisou — vismo variant via index4.aspx."""
    url = "https://www.hradek.eu/index4.aspx?rub=607"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()
    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        if len(title) < 8:
            continue
        block = a.find_parent(["li", "tr", "div"])
        if not block:
            continue
        text = block.get_text(" ", strip=True)
        date_iso = _parse_cz_date(text)
        if not date_iso:
            continue
        try:
            evd = date.fromisoformat(date_iso)
            if evd < date.today() - timedelta(days=1):
                continue
        except ValueError:
            pass
        full_url = urljoin(url, a["href"])
        key = (title[:80], date_iso)
        if key in seen:
            continue
        seen.add(key)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Hrádek nad Nisou",
            source="Hrádek nad Nisou (oficiální web)",
            date_iso=date_iso,
        ))
    return out


def fetch_mnhradiste() -> list[dict]:
    """Mnichovo Hradiště — custom calendar at /kalendar/."""
    url = "https://www.mnhradiste.cz/kalendar/"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "detailudalosti" not in href and "kalendar" not in href:
            continue
        title = a.get_text(" ", strip=True)
        if len(title) < 5 or "kalendář" in title.lower():
            continue
        block = a.find_parent(["li", "tr", "div"])
        text = block.get_text(" ", strip=True) if block else title
        date_iso = _parse_cz_date(text)
        if not date_iso:
            continue
        try:
            evd = date.fromisoformat(date_iso)
            if evd < date.today() - timedelta(days=1):
                continue
        except ValueError:
            pass
        full_url = urljoin(url, href)
        key = (title[:80], date_iso)
        if key in seen:
            continue
        seen.add(key)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Mnichovo Hradiště",
            source="Mnichovo Hradiště (oficiální web)",
            date_iso=date_iso,
        ))
    return out


def fetch_jablonec_365() -> list[dict]:
    """Jablonec nad Nisou — events on 365jablonec.cz portal (run by city)."""
    url = "https://www.365jablonec.cz/"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()
    for a in soup.select('a[href*="/udalosti-v-jablonci/"]'):
        href = a["href"]
        # Skip the listing page itself, only detail URLs (.../ID/slug)
        if not re.search(r"/udalosti-v-jablonci/\d+/", href):
            continue
        title = a.get_text(" ", strip=True)
        if len(title) < 5:
            # Maybe title is in nested element
            h = a.find(["h2", "h3", "h4"])
            if h:
                title = h.get_text(" ", strip=True)
        if len(title) < 5:
            continue
        full_url = urljoin(url, href)
        block = a.find_parent(["article", "li", "div"]) or a
        text = block.get_text(" ", strip=True)
        if (title[:80], full_url) in seen:
            continue
        seen.add((title[:80], full_url))
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Jablonec nad Nisou",
            source="365 Jablonec",
            date_iso=_parse_cz_date(text),
            time=_parse_cz_time(text),
        ))
    return out


def fetch_vratislavice() -> list[dict]:
    """Vratislavice nad Nisou — městský úřad. Front-page 'Přehled zpráv' has
    community events/announcements as <div class="item__inner"> with format:
    'DD.MM.YYYY NÁZEV číst' + a link with plugin_news_items_1-id query param."""
    url = "https://www.vratislavice.cz/"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()
    for block in soup.select("div.item__inner"):
        text = block.get_text(" ", strip=True)
        date_iso = _parse_cz_date(text)
        if not date_iso:
            continue
        # Title: text between date and "číst" link
        m = re.search(r"\d{1,2}\.\d{1,2}\.\d{4}\s+(.+?)\s+číst\s*$", text)
        title = (m.group(1).strip() if m else text).strip()
        if len(title) < 5:
            continue
        link = block.find("a", href=lambda x: x and "plugin_news_items_1-id=" in x)
        if link is None:
            link = block.find("a", href=True)
        if link is None:
            continue
        # Skip electricity outage announcements (not events)
        if "outages" in link.get("href", ""):
            continue
        full_url = urljoin(url, link["href"])
        key = (title[:80], date_iso)
        if key in seen:
            continue
        seen.add(key)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Vratislavice nad Nisou",
            source="Vratislavice (úřad)",
            date_iso=date_iso,
        ))
    return out


def fetch_vratislavice101010() -> list[dict]:
    """Vratislavice 101010 — kulturní centrum Vratislavic (oficiální kulturní
    centrum městského obvodu). Vratislavice.cz nemá vlastní event calendar —
    odkazuje sem. Page /program-akci has <h3> per event with detail link and
    date 'DD. M. YYYY od HH:MM hod.' in surrounding text."""
    url = "https://www.vratislavice101010.cz/program-akci"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()
    for h in soup.find_all("h3"):
        title = h.get_text(" ", strip=True)
        if len(title) < 5:
            continue
        # Walk up to find the wrapping div that contains the date
        block = h
        date_iso = None
        for _ in range(4):
            block = block.parent
            if block is None:
                break
            text = block.get_text(" ", strip=True)
            date_iso = _parse_cz_date(text)
            if date_iso:
                break
        if not date_iso or block is None:
            continue
        link = block.find("a", href=True)
        if link is None:
            continue
        full_url = urljoin(url, link["href"])
        text = block.get_text(" ", strip=True)
        key = (title[:80], date_iso)
        if key in seen:
            continue
        seen.add(key)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Vratislavice nad Nisou",
            source="Vratislavice 101010",
            date_iso=date_iso,
            time=_parse_cz_time(text),
        ))
    return out


# ----------------------------------------------------------------------------
# Prague — scrapers (city aggregators)
# ----------------------------------------------------------------------------

def fetch_goout_praha() -> list[dict]:
    """GoOut Praha — koncerty, divadlo, kluby."""
    url = "https://goout.net/cs/praha/akce/leznyvlkk/"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.select('a[href*="/cs/"]'):
        href = a.get("href", "")
        if href.count("/") < 4 or "/akce/" in href or "/praha/" in href:
            continue
        title = a.get_text(" ", strip=True)
        if len(title) < 5:
            continue
        full_url = urljoin(url, href)
        block = a.find_parent(["article", "li", "div"]) or a
        text = block.get_text(" ", strip=True)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Praha",
            source="GoOut Praha",
            date_iso=_parse_cz_date(text),
            time=_parse_cz_time(text),
            category="Koncert/divadlo",
            region="praha",
        ))
    return out


def fetch_kudyznudy_praha() -> list[dict]:
    """Kudy z nudy Praha — státní portál, akce v Praze."""
    url = "https://www.kudyznudy.cz/kalendar-akci/hlavni-mesto-praha"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for art in soup.find_all(["article", "div"], class_=re.compile(r"card|item|tile", re.I)):
        a = art.find("a", href=True)
        if not a:
            continue
        title_el = art.find(["h2", "h3", "h4"])
        title = (title_el.get_text(strip=True) if title_el else a.get_text(strip=True))
        if len(title) < 5:
            continue
        full_url = urljoin(url, a["href"])
        text = art.get_text(" ", strip=True)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Praha",
            source="Kudy z nudy",
            date_iso=_parse_cz_date(text),
            time=_parse_cz_time(text),
            region="praha",
        ))
    return out


def fetch_praha_eu() -> list[dict]:
    """praha.eu — oficiální portál hl. m. Prahy (MHMP)."""
    url = "https://praha.eu/kalendar-akci"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()
    for h in soup.find_all(["h2", "h3", "h4"]):
        a = h.find("a", href=True) or (h.find_next("a", href=True) if h.find_next("a", href=True) else None)
        if not a:
            continue
        title = h.get_text(" ", strip=True)
        if len(title) < 5:
            continue
        block = h.find_parent(["article", "li", "div"]) or h.parent
        text = block.get_text(" ", strip=True) if block else title
        date_iso = _parse_cz_date(text)
        full_url = urljoin(url, a["href"])
        key = (title[:80], full_url)
        if key in seen:
            continue
        seen.add(key)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Praha",
            source="praha.eu",
            date_iso=date_iso,
            time=_parse_cz_time(text),
            region="praha",
        ))
    return out


def fetch_prazskypatriot() -> list[dict]:
    """Pražský patriot — komunitní kalendář akcí v Praze."""
    url = "https://www.prazskypatriot.cz/kalendar-akci-v-praze/"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()
    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        if len(title) < 8:
            continue
        block = a.find_parent(["article", "li", "div"])
        if not block:
            continue
        text = block.get_text(" ", strip=True)
        date_iso = _parse_cz_date(text)
        if not date_iso:
            continue
        try:
            evd = date.fromisoformat(date_iso)
            if evd < date.today() - timedelta(days=1):
                continue
        except ValueError:
            pass
        full_url = urljoin(url, a["href"])
        key = (title[:80], date_iso)
        if key in seen:
            continue
        seen.add(key)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city="Praha",
            source="Pražský patriot",
            date_iso=date_iso,
            time=_parse_cz_time(text),
            region="praha",
        ))
    return out


# ----------------------------------------------------------------------------
# AI / tech events — Czech-wide (relevant for Praha mainly)
# ----------------------------------------------------------------------------

def fetch_aiakce() -> list[dict]:
    """AI Akce.cz — dedikovaný portál českých AI/tech eventů.
    Uses The Events Calendar WordPress plugin — <article class="tribe-events-calendar-list__event">
    with <time datetime="YYYY-MM-DD"> and <h4> title.
    """
    url = "https://www.aiakce.cz/seznam/"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for art in soup.select("article.tribe-events-calendar-list__event"):
        title_h = art.find(["h2", "h3", "h4"])
        if not title_h:
            continue
        link = title_h.find("a", href=True) or art.find("a", href=True)
        if not link:
            continue
        title = title_h.get_text(strip=True)
        if len(title) < 3:
            continue
        # Machine-readable date from <time datetime="...">
        date_iso = None
        time_el = art.find("time")
        if time_el and time_el.get("datetime"):
            date_iso = time_el["datetime"][:10]  # YYYY-MM-DD
        # Venue
        venue_el = art.find(class_=lambda c: c and "venue" in str(c).lower())
        place = venue_el.get_text(" ", strip=True)[:120] if venue_el else None
        # City from venue (Praha/Brno/Online/...)
        city = "Praha"
        if place:
            for c_test in ("Praha", "Brno", "Ostrava", "Plzeň", "Hradec Králové",
                          "Olomouc", "Liberec", "Online"):
                if c_test.lower() in place.lower():
                    city = c_test
                    break
        full_url = link["href"]
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city=city,
            source="AI Akce.cz",
            date_iso=date_iso,
            place=place,
            category="AI/tech",
            region="praha",  # AI events go under the Praha filter regardless of city
        ))
    return out


def fetch_brno_ai() -> list[dict]:
    """Brno.AI — kalendář AI eventů, pokrývá i Prahu."""
    url = "https://www.brno.ai/akce/"
    html = _get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()
    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        if len(title) < 5:
            continue
        block = a.find_parent(["article", "li", "div"])
        if not block:
            continue
        text = block.get_text(" ", strip=True)
        date_iso = _parse_cz_date(text)
        if not date_iso:
            continue
        full_url = urljoin(url, a["href"])
        city = "Brno"
        for c_test in ("Praha", "Brno", "Ostrava", "Online"):
            if c_test.lower() in text.lower():
                city = c_test
                break
        key = (title[:80], date_iso)
        if key in seen:
            continue
        seen.add(key)
        out.append(_make_event(
            title=title[:200],
            url=full_url,
            city=city,
            source="Brno.AI",
            date_iso=date_iso,
            time=_parse_cz_time(text),
            category="AI/tech",
            region="praha",  # AI events go under the Praha filter regardless of city
        ))
    return out


# ----------------------------------------------------------------------------
# Layer B: Google News RSS — event tips from Czech media per city
# ----------------------------------------------------------------------------

def fetch_gnews_for_city(city: str) -> list[dict]:
    """Build a Google News RSS query: '<keywords> <city>' in Czech."""
    out = []
    kw_query = " OR ".join(GNEWS_KEYWORDS)
    q = f'({kw_query}) "{city}"'
    rss_url = ("https://news.google.com/rss/search?"
               + urlencode({"q": q, "hl": "cs-CZ", "gl": "CZ", "ceid": "CZ:cs"}))
    try:
        parsed = feedparser.parse(rss_url, request_headers=HEADERS)
    except Exception as e:
        print(f"    [gnews error {city}] {e}")
        return out
    for entry in parsed.entries[:15]:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link:
            continue
        out.append(_make_event(
            title=title,
            url=link,
            city=city,
            source="Google News",
            is_tip=True,
        ))
    return out


# Praha-specific Google News queries — broader topical search than per-city
PRAHA_GNEWS_QUERIES = [
    ("koncert Praha", "Koncerty"),
    ("festival Praha", "Festivaly"),
    ("výstava Praha", "Výstavy"),
    ("divadlo Praha premiéra", "Divadlo"),
    ("AI konference Praha", "AI/tech"),
    ("workshop Praha", "Workshopy"),
    ("gastro Praha akce", "Gastro"),
    ("food festival Praha", "Gastro"),
]


def fetch_gnews_praha_topical() -> list[dict]:
    """Topical Google News searches for Praha events (concerts, AI, gastro…).
    Each query returns up to 15 articles tagged as 'Tip z médií' under Praha filter.
    """
    out = []
    for q, cat in PRAHA_GNEWS_QUERIES:
        rss_url = ("https://news.google.com/rss/search?"
                   + urlencode({"q": q, "hl": "cs-CZ", "gl": "CZ", "ceid": "CZ:cs"}))
        try:
            parsed = feedparser.parse(rss_url, request_headers=HEADERS)
        except Exception as e:
            print(f"    [gnews praha error '{q}'] {e}")
            continue
        for entry in parsed.entries[:12]:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            if not title or not link:
                continue
            out.append(_make_event(
                title=title,
                url=link,
                city="Praha",
                source=f"Google News ({cat})",
                category=cat,
                is_tip=True,
                region="praha",
            ))
    return out


# ----------------------------------------------------------------------------
# Main orchestration
# ----------------------------------------------------------------------------

def _safe_call(fn, *args, label: str) -> list[dict]:
    try:
        result = fn(*args)
        print(f"  {label}: {len(result)} eventů")
        return result
    except Exception as e:
        print(f"  {label}: ERROR — {e}")
        return []


def fetch_all_events() -> list[dict]:
    """Run every scraper, merge, dedup by id, sort by date (newest first, undated last)."""
    print("\n=== EVENTS ===")
    all_events: list[dict] = []

    # Layer A: aggregators
    all_events += _safe_call(fetch_kraj_lbc, label="kalendar.kraj-lbc.cz")
    all_events += _safe_call(fetch_zivyliberec, label="zivyliberec.cz")
    all_events += _safe_call(fetch_iliberecko, label="iLIBERECKO")
    all_events += _safe_call(fetch_kudyznudy, label="Kudy z nudy (LK)")
    all_events += _safe_call(fetch_goout_liberec, label="GoOut Liberec")

    # Layer A: city websites (vismo template)
    for c in CITY_VISMO:
        all_events += _safe_call(_fetch_vismo, c["city"], c["url"],
                                 label=f"vismo: {c['city']}")
    # Layer A: city websites (redakce template)
    for c in CITY_REDAKCE:
        all_events += _safe_call(_fetch_redakce, c["city"], c["url"],
                                 label=f"redakce: {c['city']}")
    # Layer A: custom city scrapers
    all_events += _safe_call(fetch_zeleznybrod, label="Železný Brod")
    all_events += _safe_call(fetch_hradek, label="Hrádek nad Nisou")
    all_events += _safe_call(fetch_mnhradiste, label="Mnichovo Hradiště")
    all_events += _safe_call(fetch_vratislavice, label="Vratislavice (úřad)")
    all_events += _safe_call(fetch_vratislavice101010, label="Vratislavice 101010")
    all_events += _safe_call(fetch_jablonec_365, label="365 Jablonec")

    # Praha + AI sources
    all_events += _safe_call(fetch_goout_praha, label="GoOut Praha")
    all_events += _safe_call(fetch_kudyznudy_praha, label="Kudy z nudy (Praha)")
    all_events += _safe_call(fetch_praha_eu, label="praha.eu (MHMP)")
    all_events += _safe_call(fetch_prazskypatriot, label="Pražský patriot")
    all_events += _safe_call(fetch_aiakce, label="AI Akce.cz")
    all_events += _safe_call(fetch_brno_ai, label="Brno.AI")

    # Layer B: Google News tips per city (Liberec area)
    for city in GNEWS_CITIES:
        all_events += _safe_call(fetch_gnews_for_city, city,
                                 label=f"Google News: {city}")

    # Layer B: Praha topical Google News (koncerty, AI, gastro…)
    all_events += _safe_call(fetch_gnews_praha_topical, label="Google News Praha (topics)")

    # Dedup by id (title+url hash)
    seen_ids: set[str] = set()
    deduped: list[dict] = []
    for ev in all_events:
        if ev["id"] in seen_ids:
            continue
        # Drop events tagged as Praha but happening elsewhere (e.g. AI events
        # in Brno/Ostrava/Online get region='praha' override from AI fetchers;
        # we want Praha filter to be strictly Praha).
        if ev.get("region") == "praha" and (ev.get("city") or "").strip().lower() != "praha":
            continue
        seen_ids.add(ev["id"])
        deduped.append(ev)

    # Sort: dated first (chronological), undated/tips last
    def sort_key(ev):
        d = ev.get("date") or "9999-99-99"
        is_tip = 1 if ev.get("is_tip") else 0
        return (is_tip, d)

    deduped.sort(key=sort_key)

    print(f"  Total: {len(all_events)} → after dedup: {len(deduped)}")
    return deduped


if __name__ == "__main__":
    import json
    events = fetch_all_events()
    print(json.dumps(events[:5], ensure_ascii=False, indent=2))
