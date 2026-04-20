"""Translate EN → CS. Chain: Gemini (batched) → MyMemory → Google (deep-translator)."""
import os
import json
import time
import requests
from google import genai
from google.genai import types

try:
    from deep_translator import GoogleTranslator
    _HAS_DEEP = True
except Exception:
    _HAS_DEEP = False


MYMEMORY_URL = "https://api.mymemory.translated.net/get"
_MM_EMAIL = os.environ.get("MYMEMORY_EMAIL", "wondervoice9@gmail.com")

_client = None
_mm_dead = False  # Once MyMemory returns "ALL AVAILABLE FREE TRANSLATIONS", stop calling it.
_google_dead = False  # Same for deep-translator.


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key or api_key == "PASTE_YOUR_KEY_HERE":
            return None
        _client = genai.Client(api_key=api_key)
    return _client


def _mymemory_translate(text: str) -> str:
    """Single MyMemory call. Sets _mm_dead on quota exhaustion."""
    global _mm_dead
    if not text or _mm_dead:
        return text or ""
    try:
        resp = requests.get(
            MYMEMORY_URL,
            params={
                "q": text[:480],
                "langpair": "en|cs",
                "de": _MM_EMAIL,
            },
            timeout=15,
        )
        data = resp.json()
        result = data.get("responseData", {}).get("translatedText", "")
        if "MYMEMORY WARNING" in result.upper():
            _mm_dead = True
            return text
        return result or text
    except Exception:
        return text


def _google_translate(text: str) -> str:
    """Free fallback via deep-translator (Google Translate web). Sets _google_dead on failure."""
    global _google_dead
    if not text or _google_dead or not _HAS_DEEP:
        return text or ""
    try:
        result = GoogleTranslator(source="en", target="cs").translate(text[:4500])
        return result or text
    except Exception as e:
        print(f"    [google translate error] {e}")
        _google_dead = True
        return text


def _translate_with_fallbacks(text: str) -> str:
    """Try MyMemory first, then Google web. Returns original text if both fail."""
    out = _mymemory_translate(text)
    if out and out != text:
        return out
    out = _google_translate(text)
    return out or text


def translate_text(text: str) -> str:
    """Translate a single text via Gemini (fallback to MyMemory)."""
    if not text:
        return ""
    client = _get_client()
    if client is None:
        return _translate_with_fallbacks(text)
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"Přelož následující text do češtiny. Odpověz POUZE překladem, bez úvodu:\n\n{text}",
            config=types.GenerateContentConfig(temperature=0.0),
        )
        return (resp.text or "").strip() or text
    except Exception as e:
        print(f"    [gemini translate error] {e}")
        return _translate_with_fallbacks(text)


def translate_articles(articles: list[dict]) -> list[dict]:
    """Batch-translate all EN articles in one Gemini call per chunk."""
    en_articles = [a for a in articles if a["lang"] == "en"]
    cs_articles = [a for a in articles if a["lang"] == "cs"]

    # Czech articles just copy
    for a in cs_articles:
        a["title_cs"] = a["title"]
        a["summary_cs"] = a["summary"]

    if not en_articles:
        return articles

    client = _get_client()
    if client is None:
        # Fallback chain per article
        for a in en_articles:
            a["title_cs"] = _translate_with_fallbacks(a["title"])
            a["summary_cs"] = _translate_with_fallbacks(a["summary"])
            time.sleep(0.2)
        return articles

    # Batch: up to 15 articles per request
    BATCH = 15
    for i in range(0, len(en_articles), BATCH):
        chunk = en_articles[i:i + BATCH]
        payload = [{"i": idx, "title": a["title"], "summary": a["summary"]} for idx, a in enumerate(chunk)]
        prompt = (
            "Přelož následující články z angličtiny do češtiny. "
            "Pro každý článek přelož 'title' a 'summary'. "
            "Zachovej význam, piš přirozenou češtinou, žádný strojový překlad. "
            "Odpověz POUZE JSONem ve formátu: "
            '[{"i": 0, "title_cs": "...", "summary_cs": "..."}, ...]\n\n'
            f"Články:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            translations = json.loads(resp.text)
            by_idx = {t["i"]: t for t in translations}
            for idx, a in enumerate(chunk):
                t = by_idx.get(idx, {})
                a["title_cs"] = t.get("title_cs") or a["title"]
                a["summary_cs"] = t.get("summary_cs") or a["summary"]
        except Exception as e:
            print(f"    [gemini batch error] {e} — falling back to MyMemory/Google")
            for a in chunk:
                a["title_cs"] = _translate_with_fallbacks(a["title"])
                a["summary_cs"] = _translate_with_fallbacks(a["summary"])
                time.sleep(0.2)

    return articles
