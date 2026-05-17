"""Deduplicate articles by title similarity and URL."""
import re


def _normalize(title: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    t = title.lower()
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _token_set(title: str) -> set:
    """Tokenize and drop short stopword-like tokens (1–2 chars).

    Czech/English prepositions and conjunctions ("se", "z", "v", "k", "a",
    "je", "i", "u", "o", "to", "na", "do", "po", "by", "of", "is", "in",
    "at", "on") inflate the union and depress Jaccard similarity for
    otherwise near-identical headlines. Dropping them gives better dedup
    without needing a stopword list per language.
    """
    return {w for w in _normalize(title).split() if len(w) >= 3}


def _similarity(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def dedup(articles: list[dict], threshold: float = 0.45) -> list[dict]:
    """Remove duplicates. Keep first occurrence.
    - Same URL → dup.
    - Jaccard similarity of title tokens (short tokens stripped) >= threshold → dup.

    The 0.45 threshold catches paraphrases like
        "Lebku svaté Zdislavy se podařilo vyjmout z betonu"
        "Experti vyjmuli lebku svaté Zdislavy z betonu"
    without flagging unrelated stories that happen to share a noun or two.
    """
    seen_urls = set()
    kept = []
    kept_tokens = []

    for art in articles:
        url = art["link"].rstrip("/").lower()
        if url in seen_urls:
            continue

        tokens = _token_set(art["title"])
        is_dup = False
        for prev in kept_tokens:
            if _similarity(tokens, prev) >= threshold:
                is_dup = True
                break
        if is_dup:
            continue

        seen_urls.add(url)
        kept.append(art)
        kept_tokens.append(tokens)

    return kept
