"""Fast local keyword filter — drops obviously disturbing articles without any API calls.

Runs before Gemini to:
  1. Reduce Gemini load (fewer articles sent = fewer tokens)
  2. Provide a working safety net when Gemini is rate-limited / offline
  3. Be deterministic — same article always treated the same way

Kept intentionally aggressive. False positives on culture/sport (metaphorical
"murder / killed") are acceptable — those feeds have plenty of content; losing
a few articles matters less than leaking one graphic headline.
"""
import re

# Regex patterns with word boundaries — match only whole-word occurrences.
BLOCK_PATTERNS_CZ = [
    r"\bzavražd(il|ila|ili|ěn|ěna|ění)",
    r"\bvrah(a|em|ovi|y|ů)?\b",
    r"\bvražd[aěoyě]",
    r"\bzastřel(il|ila|ili|en|ena)",
    r"\bpostřel(il|ila|ili|en|ena)",
    r"\bstřelb[aěyou]",
    r"\bhromadn[áéý]\s+střelb",
    r"\bsebevražd",
    r"\bspáchal\s+sebevraž",
    r"\bznásil(nil|nila|nili|nění)",
    r"\buškrt(il|ila|en|ena)",
    r"\bubod(l|la|li|nut)",
    r"\bpobodal|\bpobodán",
    r"\bumuči(l|la)",
    r"\btýr(al|ala|án[íe])",
    r"\bmrtv[éýáé]+\s+(dít|děti|dětí|dívk|chlap|mimink|batol)",
    r"\bnaleze(no|n)\s+tělo",
    r"\bnašli\s+tělo",
    r"\bnález\s+těl",
    r"\bsexuálně\s+zneuž",
    r"\bzneužíván[íe]\s+(dět|nezletil)",
    r"\bpedofil",
]

BLOCK_PATTERNS_EN = [
    r"\bmurder(ed|ing|er|ers|s)?\b",
    r"\bmass\s+shooting",
    r"\bmass\s+killing",
    r"\bshot\s+(and\s+killed|dead|to\s+death)",
    r"\bshoots?\s+(his|her|their)\s+(children|kids|wife|husband|family|daughter|son)",
    r"\bkill(s|ed)\s+(his|her|their|own)\s+(children|kids|wife|husband|family|daughter|son|parents)",
    r"\bstabbed?\s+to\s+death",
    r"\bstabbing\s+(death|spree|attack)",
    r"\bstrangl(ed|ing)\b",
    r"\brape(d|s|r)?\b",
    r"\bsexual(ly)?\s+(assault|abuse|abused|molest)",
    r"\bchild\s+(abuse|molestation|rape|murder|trafficking)",
    r"\bpaedophil|\bpedophil",
    r"\bbody\s+(found|discovered|recovered)",
    r"\bbodies\s+(found|discovered|recovered)",
    r"\bsuicide\b",
    r"\bsuicidal\b",
    r"\bdismember",
    r"\btortur(ed|ing|er|e\s+victim)",
    r"\bhomicide",
    r"\bbeaten\s+to\s+death",
    r"\bburned\s+alive",
    r"\bdecapit",
    r"\bmutilat",
]

_RE_CZ = [re.compile(p, re.IGNORECASE) for p in BLOCK_PATTERNS_CZ]
_RE_EN = [re.compile(p, re.IGNORECASE) for p in BLOCK_PATTERNS_EN]
_ALL = _RE_CZ + _RE_EN


def _is_disturbing(text: str) -> str | None:
    """Return the first matching pattern (for logging) or None."""
    if not text:
        return None
    for rx in _ALL:
        m = rx.search(text)
        if m:
            return m.group(0)
    return None


def filter_keyword(articles: list[dict]) -> list[dict]:
    """Drop articles whose title/summary contains obvious disturbing keywords.

    Checks both CZ and EN patterns against every article regardless of lang —
    CZ feeds sometimes quote English, and vice versa.
    """
    if not articles:
        return []
    kept = []
    dropped = 0
    for a in articles:
        haystack = f"{a.get('title', '')} {a.get('summary', '')}"
        hit = _is_disturbing(haystack)
        if hit:
            dropped += 1
            continue
        kept.append(a)
    if dropped:
        print(f"  Keyword filter: dropped {dropped}/{len(articles)} ({len(kept)} kept)")
    return kept
