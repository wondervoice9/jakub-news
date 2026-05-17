"""Filter Czech news using Gemini: drop politics, violence, individual stories."""
import os
import json
from google import genai
from google.genai import types


_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key or api_key == "PASTE_YOUR_KEY_HERE":
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        _client = genai.Client(api_key=api_key)
    return _client


CZECH_FILTER_PROMPT = """Jsi filtr zpráv. Pro každý článek rozhodni, zda ho NECHAT (keep=true) nebo ZAHODIT (keep=false).

ZAHOĎ (keep=false) pokud článek je o:
- politice, volbách, politicích, vládě, parlamentu, politických stranách
- jakémkoli násilí nebo zločinu, kde někdo přišel k újmě na zdraví nebo zemřel
  (vraždy, napadení, znásilnění, ublížení na zdraví, dopravní nehody se zraněnými, požáry s oběťmi)
- soudních kauzách týkajících se násilí, vražd, znásilnění

NECHEJ (keep=true) články o:
- ekonomice, firmách, businessu, trzích
- společenských trendech, vzdělávání, vědě, výzkumu
- infrastruktuře, dopravě, zdravotnictví
- kultuře, technologiích
- osobních příbězích jednotlivců a celebrit (úmrtí přirozenou cestou, nemoci, osobní tragédie, rozvody, výročí)
- majetkových zločinech (krádeže, vloupání, podvody, korupce, daňové úniky, defraudace,
  finanční zločiny, kybernetické útoky bez fyzické újmy)
- soudních kauzách o majetkových a finančních věcech

Hraniční příklady:
- "Zloděj ukradl auto za milion" → NECHEJ (majetkový zločin, bez újmy na zdraví)
- "Hackeři ukradli data 100 000 klientů banky" → NECHEJ (kybernetický, bez újmy)
- "Známý herec zemřel ve věku 78 let" → NECHEJ (osobní příběh celebrity)
- "Útočník pobodal tři lidi v centru Prahy" → ZAHOĎ (násilí + zranění)
- "Senátor schválil zákon o..." → ZAHOĎ (politika)

Odpověz POUZE JSONem: [{"id": "...", "keep": true/false}, ...]

Články:
"""

DISTURBING_FILTER_PROMPT = """Jsi filtr nepříjemných zpráv. Pro každý článek rozhodni, zda ho NECHAT (keep=true) nebo ZAHODIT (keep=false).

ZAHOĎ (keep=false) články, které jsou především o:
- vraždě, zabití, masové střelbě, útoku nožem, bodnutí, brutálním napadení
- násilí na dětech, týrání, zneužívání (sexuálním i fyzickém)
- sebevraždě, sebepoškozování
- tragických úmrtích jednotlivců (vraždy, nehody s mrtvými, požáry s oběťmi, utonutí, pády)
- detailech kriminálních činů (znásilnění, únos, mučení)
- nálezech mrtvých těl, rozkladu, forenzních detailech
- rodinných tragédiích (otec zabil děti, matka zavraždila, vražda + sebevražda)

NECHEJ (keep=true) vše ostatní — politika, ekonomika, válka jako geopolitické téma, přírodní katastrofy bez detailů obětí, byznys, kultura, sport, technologie, věda, vzdělávání.

Hraniční příklady:
- "Rusko zaútočilo na Kyjev, zemřelo X lidí" → NECHEJ (geopolitika, neutrální tón)
- "Otec uškrtil své tři děti, poté se oběsil" → ZAHOĎ (rodinná tragédie, detaily)
- "Masová střelba ve škole v Louisianě, 8 mrtvých dětí" → ZAHOĎ (násilí na dětech)
- "Nový protitankový systém dodán na Ukrajinu" → NECHEJ

Odpověz POUZE JSONem: [{"id": "...", "keep": true/false}, ...]

Články:
"""

GOOD_NEWS_FILTER_PROMPT = """Jsi filtr pozitivních zpráv. Pro každý článek rozhodni, zda ho NECHAT (keep=true) nebo ZAHODIT (keep=false).

NECHEJ (keep=true) pouze zprávy o:
- pozitivních globálních událostech (ochrana klimatu, ekologie)
- záchraně zvířat, obnově biotopů, přírodě
- vědeckých průlomech ve prospěch lidstva
- společenských úspěších (zastavení lovu velryb, snížení emisí, obnova korálů)
- mezinárodních dohodách ve prospěch společnosti/planety
- technologiích měnících svět k lepšímu

ZAHOĎ (keep=false) zprávy o:
- jednotlivcích a jejich osobních příbězích (hrdinských činech, záchranách, dobrých skutcích konkrétních lidí)
- lokálních úspěších bez širšího dopadu
- celebrity/sportovci vyhráli něco

Odpověz POUZE JSONem: [{"id": "...", "keep": true/false}, ...]

Články:
"""


def _apply_filter(articles: list[dict], prompt_template: str, label: str) -> list[dict]:
    if not articles:
        return []
    payload = [{"id": a["id"], "title": a["title"], "summary": a["summary"][:200]} for a in articles]
    prompt = prompt_template + json.dumps(payload, ensure_ascii=False)
    try:
        client = _get_client()
        resp = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        decisions = json.loads(resp.text)
        keep_ids = {d["id"] for d in decisions if d.get("keep")}
        filtered = [a for a in articles if a["id"] in keep_ids]
        print(f"  Gemini {label} filter: kept {len(filtered)}/{len(articles)}")
        return filtered
    except Exception as e:
        print(f"  [gemini {label} filter error] {e} — keeping all articles as fallback")
        return articles


def filter_czech(articles: list[dict]) -> list[dict]:
    return _apply_filter(articles, CZECH_FILTER_PROMPT, "Czech")


def filter_good_news(articles: list[dict]) -> list[dict]:
    return _apply_filter(articles, GOOD_NEWS_FILTER_PROMPT, "GoodNews")


def filter_disturbing(articles: list[dict]) -> list[dict]:
    return _apply_filter(articles, DISTURBING_FILTER_PROMPT, "Disturbing")
