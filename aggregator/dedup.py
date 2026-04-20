"""Deduplicate articles by title similarity and URL."""
import re


def _normalize(title: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    t = title.lower()
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _token_set(title: str) -> set:
    return set(_normalize(title).split())


def _similarity(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def dedup(articles: list[dict], threshold: float = 0.6) -> list[dict]:
    """Remove duplicates. Keep first occurrence.
    - Same URL → dup.
    - Jaccard similarity of title tokens >= threshold → dup.
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
