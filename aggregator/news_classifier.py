"""Content-based subcategory classifier for news articles.

Sport feeds already get their `sub` from the source config + a re-tagging
pass in rss_fetcher. News feeds (world, world_en, czech) are generic —
the source has no useful sub, so we have to classify on title + summary.

Regexes mix Czech and English keywords so the same function works for
both Czech-language (world) and English-language (world_en) articles.
Fallback for unmatched articles is the soft "society" / "social" bucket.
"""
import re

# ============================================================
#  WORLD news — politics / conflicts / economy / society
# ============================================================

_WORLD_CONFLICT_RE = re.compile(
    r"\b("
    # CZ
    r"v[aá]lk\w*|konflikt\w*|invaz\w*|raket\w*|dron\w*|"
    r"voj[aá]ck\w*|armád\w*|p[řr][ií]m[eě][řr][ií]|sankc\w*|"
    r"Hamás\w*|Hizball[aá]h\w*|Ukrajin\w*|Rus[oůu]\w*|Rusk\w*|"
    r"Gaz[ay]|Izrael\w*|S[ýy]rie?\w*|Jemen\w*|terorist\w*|"
    r"atent[aá]t\w*|úto[čc][ií]\w*|úto[kč]\w*|nálet\w*|"
    # EN
    r"war|warfare|conflict|invasion|missile|drone\s+strike|"
    r"military|army|ceasefire|sanction|"
    r"Hamas|Hezbollah|Ukraine|Russia|Gaza|Israel|Syria|Yemen|"
    r"terrorist|airstrike|strike\s+killed"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)

_WORLD_POLITICS_RE = re.compile(
    r"\b("
    # CZ
    r"prezident\w*|prem[ií]ér\w*|vl[aá]d\w*|parlament\w*|"
    r"ministr\w*|sen[aá]tor\w*|sn[ěe]movn\w*|kabinet\w*|"
    r"summit\w*|jedn[aá]n\w*|diplomat\w*|volby?\w*|kandid[aá]t\w*|"
    r"OSN|NATO|EU\b|Evropsk\w+\s+(unie|komise|rad\w*|parlament)|"
    # EN
    r"president|prime\s+minister|government|cabinet|"
    r"minister|senator|parliament|congress|"
    r"summit|diplomatic|election|nominee|"
    r"UN\b|NATO\b|EU\b|European\s+(Union|Commission|Council)|"
    # Names (politicians frequently in headlines)
    r"Trump|Putin|Biden|Macron|Merz|Sch[öo]lz|Zelensk\w*|"
    r"Netanyahu|Erdogan|Modi|Xi\s+Jinping"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)

_WORLD_ECONOMY_RE = re.compile(
    r"\b("
    # CZ — vyhněte se příliš krátkým kořenům, které matchnou názvy lidí/míst
    # (např. dřívější `m[ěe]n\w*` matchovalo Mengelem). Místo toho explicitní tvary.
    r"ekonomik\w*|hospod[aá][řr]\w*|inflac\w*|recese?\w*|HDP\b|"
    r"akci(?:e|í|ích|emi)\b|burz[aěyou]\w*|rop[aěyu]\w*|plyn[aěyou]\w*|"
    r"dolar\w*|euro\w*|m[ěe]n[aěyou]\w*|"  # měna/měny/měně/měnu/měnou — vyžaduje samohlásku po men
    r"komerční\s+bank\w*|centrální\s+bank\w*|"
    r"úv[ěe]r\w*|sazb[aěyou]\w*|sazeb\b|"
    r"ECB\b|FED\b|firma?\w*|trh[uy]\b|trhů\b|kryptom[ěe]n\w*|bitcoin\w*|"
    r"export\w*|import\w*|tržb\w*|zisk\w*|HDP|"
    # EN
    r"economy|GDP|inflation|recession|"
    r"stock|stocks|markets?|oil|gas|dollar|"
    r"central\s+bank|interest\s+rate|"
    r"earnings|revenue|trade\s+(?:deal|war|talks)|tariff|crypto|bitcoin"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)


def classify_world(title: str, summary: str) -> str:
    """Return one of: 'conflicts', 'politics', 'economy', 'society'.

    Order matters: war news often mentions politicians too, so conflict
    is checked first. Economy is checked before politics because some
    economic news mentions presidents in passing.
    """
    haystack = f"{title} {summary}"
    if _WORLD_CONFLICT_RE.search(haystack):
        return "conflicts"
    if _WORLD_ECONOMY_RE.search(haystack):
        return "economy"
    if _WORLD_POLITICS_RE.search(haystack):
        return "politics"
    return "society"


# ============================================================
#  CZECH news — business / infrastructure / crime / social
# ============================================================

_CZECH_CRIME_RE = re.compile(
    r"\b("
    r"zlod[ěe]j\w*|kr[aá]de[žz]\w*|vloup[aá]n\w*|"
    r"podvod\w*|defraudac\w*|úplat\w*|korupc\w*|"
    r"da[ňn]ov\w*\s+[úu]nik\w*|prané\s+peníz\w*|"
    r"kyber\w*|hackerov\w*|hacker\w*|útok\s+na\s+banku|"
    r"policie\s+(?:zadr[žz]ela|vy[šs]et[řr]uje|obvinila|p[aá]tr[aá])|"
    r"soud\s+(?:uznal|zprostil|odsoudil)|"
    r"st[aá]tn[ií]\s+z[aá]stupc\w*|"
    r"ob[žz]alov\w*|trestn[ií]\s+st[ií]h[aá]n\w*|"
    r"vypálen\w*|zpronev[ěe]r\w*"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)

_CZECH_INFRA_RE = re.compile(
    r"\b("
    r"d[aá]lnic\w*|silnic\w*|vlak\w*|[žz]eleznic\w*|metro\w*|"
    r"leti[šs]t\w*|let\w*\s+(?:zpo[žz]d[ěe]|zru[šs]en)|"
    r"ČEZ|elektr[aá]rn\w*|jadern\w*|energetik\w*|"
    r"stavb\w*|most\w*|infrastruktur\w*|tunel\w*|"
    r"D\d{1,2}\b|D0\b|"  # D1, D5, D10... dálnice
    r"ČEPS|operátor"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)

_CZECH_BUSINESS_RE = re.compile(
    r"\b("
    # Note: "společnost" is intentionally NOT here — it ambiguously means
    # either "company" or "society", which polluted the bucket.
    r"firma?\w*|byzny?\w*|burz\w*|"
    r"akcie?\w*|investic\w*|"
    r"DPH|HDP|inflac\w*|"
    r"hospod[aá][řr]\w*|ekonomi\w*|ekonom\b|"
    r"Škoda\s+Auto\w*|Komerčn\w*\s+bank\w*|"
    r"ČSOB|kryptom[ěe]n\w*|startup\w*|"
    r"zisk\w*|tržb\w*|"
    r"akciov\w*|burzovn\w*|úv[ěe]r\w*|"
    r"dolar\w*|sazb\w*\s+ČNB|ČNB\b"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)


def classify_czech(title: str, summary: str) -> str:
    """Return one of: 'crime', 'infrastructure', 'business', 'social'.

    Crime is checked first so 'soud odsoudil firmu' lands in crime, not
    business. Infrastructure before business so 'D1 staví ŘSD' lands in
    infrastructure, not business.
    """
    haystack = f"{title} {summary}"
    if _CZECH_CRIME_RE.search(haystack):
        return "crime"
    if _CZECH_INFRA_RE.search(haystack):
        return "infrastructure"
    if _CZECH_BUSINESS_RE.search(haystack):
        return "business"
    return "social"
