"""
Falco — Vratliga (malá kopaná, Vratislavice).

The league site (vratliga.webnode.cz) publishes EVERYTHING as images: the
schedule, current round, standings, top scorers and hat-tricks are all uploaded
screenshots, so there's no text to scrape. We therefore just grab the current
content-image URLs from each page and let the frontend display them.

Two quirks handled here:
  * Webnode image URLs carry a content hash that changes on every re-upload, so
    these must be re-scraped on each run (done daily by the aggregator).
  * The site's TLS chain trips strict OpenSSL ("Basic Constraints ... not marked
    critical"), so we pass verify=False. It's a public, read-only page with no
    sensitive data, so skipping verification is acceptable here.
"""
import re

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://vratliga.webnode.cz"

# Logical section -> page path. "matches" = aktuální kolo (what's coming up).
PAGES = {
    "matches": "/aktualni-kolo/",
    "schedule": "/rozlosovani-2024-25/",
    "table": "/tabulka/",
    "scorers": "/tabulka-strelcu/",
    "hattricks": "/strelec-hattricku/",
}

# Czech labels for the frontend.
LABELS = {
    "matches": "Co nás čeká",
    "schedule": "Rozlosování",
    "table": "Tabulka",
    "scorers": "Tabulka střelců",
    "hattricks": "Střelci hattricků",
}

# Filename fragments that are site chrome (banners, logo photo), not data.
_CHROME = ("foto", "play%20off", "play off", "logo", "favicon", "/icon", "banner")

_IMG_RE = re.compile(
    r"https://[a-z0-9]+\.cbaul-cdnwnd\.com/[^\"'() ]+?\.(?:png|jpe?g)", re.I
)


def _content_images(html: str, limit: int) -> list[str]:
    """Pull the real content images from a page, dropping chrome + thumbnails."""
    out: list[str] = []
    for u in _IMG_RE.findall(html):
        low = u.lower()
        if any(c in low for c in _CHROME):
            continue
        if "/700/" in u:  # Webnode resized thumbnail — prefer the full-size one
            continue
        if u not in out:
            out.append(u)
    return out[:limit]


def fetch_falco() -> dict:
    """Scrape current image URLs for each Falco/Vratliga section.

    Returns: {source_url, sections: {key: {label, url, images: [...]}}}
    Failures are non-fatal — a section just ends up with an empty image list.
    """
    sections: dict[str, dict] = {}
    for key, path in PAGES.items():
        url = BASE + path
        # The standings page posts a result sheet per round (many images);
        # cap it lower than the rest so the section stays readable.
        cap = 6 if key in ("table", "schedule") else 3
        try:
            r = requests.get(
                url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25, verify=False
            )
            r.raise_for_status()
            images = _content_images(r.text, cap)
            print(f"  Falco/{key}: {len(images)} images")
        except Exception as e:  # noqa: BLE001 — best-effort scrape
            print(f"  Falco/{key} FAILED: {type(e).__name__}: {e}")
            images = []
        sections[key] = {"label": LABELS[key], "url": url, "images": images}

    return {"source_url": BASE + PAGES["matches"], "sections": sections}
