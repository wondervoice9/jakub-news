"""Today's match fixtures for: Czech first league + cup, Premier League + FA Cup + EFL Cup,
Champions/Europa/Conference League, Czech hockey extraliga, F1 (main race), MotoGP (main race),
plus Czech national football/hockey when playing.

All sources are free, no API key required (ESPN, TheSportsDB, Ergast/Jolpica).
"""
import requests
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo

CZ_TZ = ZoneInfo("Europe/Prague")

SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"
ERGAST_BASE = "https://api.jolpi.ca/ergast/f1"


def _today_iso() -> str:
    return datetime.now(CZ_TZ).strftime("%Y-%m-%d")


def _today_yyyymmdd() -> str:
    return datetime.now(CZ_TZ).strftime("%Y%m%d")


def _to_local_time(iso_utc: str) -> str:
    """Convert ISO UTC datetime string to HH:MM in Europe/Prague."""
    if not iso_utc:
        return ""
    try:
        # ESPN: 2026-04-19T13:00Z, TheSportsDB: separate date+time fields
        s = iso_utc.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(CZ_TZ).strftime("%H:%M")
    except Exception:
        return ""


def _fixture(time: str, home: str, away: str, status: str = "") -> dict:
    return {"time": time, "home": home, "away": away, "status": status}


# -------------------- ESPN --------------------

def _espn_fetch(sport: str, league: str, ymd: str) -> list[dict]:
    try:
        r = requests.get(
            f"{ESPN_BASE}/{sport}/{league}/scoreboard",
            params={"dates": ymd},
            timeout=15,
        )
        d = r.json()
        events = d.get("events") or []
        out = []
        for e in events:
            comps = (e.get("competitions") or [{}])[0]
            competitors = comps.get("competitors") or []
            home = away = ""
            for c in competitors:
                team = (c.get("team") or {}).get("displayName", "")
                if c.get("homeAway") == "home":
                    home = team
                else:
                    away = team
            time = _to_local_time(e.get("date"))
            status_obj = (e.get("status") or {}).get("type") or {}
            status = status_obj.get("shortDetail", "") or status_obj.get("description", "")
            out.append(_fixture(time, home, away, status))
        return out
    except Exception as e:
        print(f"  [espn {sport}/{league} error] {e}")
        return []


def fetch_premier_league() -> list[dict]:
    return _espn_fetch("soccer", "eng.1", _today_yyyymmdd())


def fetch_fa_cup() -> list[dict]:
    return _espn_fetch("soccer", "eng.fa", _today_yyyymmdd())


def fetch_efl_cup() -> list[dict]:
    return _espn_fetch("soccer", "eng.league_cup", _today_yyyymmdd())


def fetch_champions_league() -> list[dict]:
    return _espn_fetch("soccer", "uefa.champions", _today_yyyymmdd())


def fetch_europa_league() -> list[dict]:
    return _espn_fetch("soccer", "uefa.europa", _today_yyyymmdd())


def fetch_conference_league() -> list[dict]:
    return _espn_fetch("soccer", "uefa.europa.conf", _today_yyyymmdd())


def fetch_czech_cup() -> list[dict]:
    return _espn_fetch("soccer", "cze.cup", _today_yyyymmdd())


def fetch_world_cup() -> list[dict]:
    return _espn_fetch("soccer", "fifa.world", _today_yyyymmdd())


def fetch_world_cup_qualifiers() -> list[dict]:
    """UEFA region qualifiers (most relevant for CZ audience)."""
    return _espn_fetch("soccer", "fifa.worldq.uefa", _today_yyyymmdd())


def fetch_euro() -> list[dict]:
    return _espn_fetch("soccer", "uefa.euro", _today_yyyymmdd())


def fetch_euro_qualifiers() -> list[dict]:
    return _espn_fetch("soccer", "uefa.euroq", _today_yyyymmdd())


def fetch_nations_league() -> list[dict]:
    """Combine all UEFA Nations League divisions (A/B/C/D)."""
    ymd = _today_yyyymmdd()
    out = []
    for div in ("uefa.nations_league_a", "uefa.nations_league_b",
                "uefa.nations_league_c", "uefa.nations_league_d"):
        out.extend(_espn_fetch("soccer", div, ymd))
    return out


def fetch_iihf_worlds() -> list[dict]:
    return _espn_fetch("hockey", "iihf-mens-world-championship", _today_yyyymmdd())


def fetch_olympic_hockey() -> list[dict]:
    return _espn_fetch("hockey", "mens-olympic-hockey", _today_yyyymmdd())


def fetch_nhl() -> list[dict]:
    return _espn_fetch("hockey", "nhl", _today_yyyymmdd())


def fetch_czech_national_football() -> list[dict]:
    """Search for Czech national team in multiple international competitions."""
    ymd = _today_yyyymmdd()
    competitions = [
        "fifa.worldq.uefa",   # World Cup qualifiers
        "fifa.world",          # World Cup
        "uefa.nations_league_a",
        "uefa.nations_league_b",
        "uefa.euroq",          # Euro qualifiers
        "uefa.euro",           # Euro finals
        "fifa.friendly",
    ]
    found = []
    for comp in competitions:
        try:
            r = requests.get(
                f"{ESPN_BASE}/soccer/{comp}/scoreboard",
                params={"dates": ymd},
                timeout=12,
            )
            d = r.json()
            for e in d.get("events") or []:
                comps = (e.get("competitions") or [{}])[0]
                competitors = comps.get("competitors") or []
                home = away = ""
                for c in competitors:
                    team = (c.get("team") or {}).get("displayName", "")
                    if c.get("homeAway") == "home":
                        home = team
                    else:
                        away = team
                if "Czech" in home or "Czech" in away:
                    found.append(_fixture(_to_local_time(e.get("date")), home, away))
        except Exception:
            continue
    return found


def fetch_czech_national_hockey() -> list[dict]:
    """IIHF / international hockey featuring Czech team."""
    ymd = _today_yyyymmdd()
    competitions = ["mens-olympic-hockey", "iihf-mens-world-championship"]
    found = []
    for comp in competitions:
        try:
            r = requests.get(
                f"{ESPN_BASE}/hockey/{comp}/scoreboard",
                params={"dates": ymd},
                timeout=12,
            )
            d = r.json()
            for e in d.get("events") or []:
                comps = (e.get("competitions") or [{}])[0]
                competitors = comps.get("competitors") or []
                home = away = ""
                for c in competitors:
                    team = (c.get("team") or {}).get("displayName", "")
                    if c.get("homeAway") == "home":
                        home = team
                    else:
                        away = team
                if "Czech" in home or "Czech" in away:
                    found.append(_fixture(_to_local_time(e.get("date")), home, away))
        except Exception:
            continue
    return found


# -------------------- TheSportsDB --------------------

def _sportsdb_fetch(league: str, iso_date: str) -> list[dict]:
    try:
        r = requests.get(
            f"{SPORTSDB_BASE}/eventsday.php",
            params={"d": iso_date, "l": league},
            timeout=15,
        )
        d = r.json()
        events = d.get("events") or []
        out = []
        for e in events:
            time_local = ""
            t_iso = e.get("strTimestamp")
            if t_iso:
                time_local = _to_local_time(t_iso)
            else:
                t = e.get("strTime") or ""
                if t and t != "00:00:00":
                    # treat as UTC HH:MM:SS
                    try:
                        dt = datetime.fromisoformat(f"{e.get('dateEvent')}T{t}").replace(tzinfo=timezone.utc)
                        time_local = dt.astimezone(CZ_TZ).strftime("%H:%M")
                    except Exception:
                        time_local = t[:5]
            out.append(_fixture(time_local, e.get("strHomeTeam") or "", e.get("strAwayTeam") or ""))
        return out
    except Exception as e:
        print(f"  [sportsdb {league} error] {e}")
        return []


def fetch_czech_first_league() -> list[dict]:
    return _sportsdb_fetch("Czech First League", _today_iso())


def fetch_czech_extraliga() -> list[dict]:
    return _sportsdb_fetch("Czech Extraliga", _today_iso())


# -------------------- F1 (Ergast / Jolpica) --------------------

def fetch_f1_today() -> list[dict]:
    """Return today's F1 main race only (no qualifying/practice/sprint)."""
    today_iso = _today_iso()
    year = datetime.now(CZ_TZ).year
    try:
        r = requests.get(f"{ERGAST_BASE}/{year}.json", timeout=15)
        d = r.json()
        races = d.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        out = []
        for race in races:
            if race.get("date") == today_iso:
                tme = race.get("time")
                iso = f"{today_iso}T{tme}" if tme else f"{today_iso}T00:00:00Z"
                out.append({
                    "time": _to_local_time(iso),
                    "home": race.get("raceName", ""),
                    "away": "Závod",
                    "status": "",
                })
        return out
    except Exception as e:
        print(f"  [f1 ergast error] {e}")
        return []


def fetch_motogp_today() -> list[dict]:
    """Today's MotoGP main race (skip Moto2/Moto3, qualifying, practice, sprint)."""
    try:
        r = requests.get(
            f"{SPORTSDB_BASE}/eventsday.php",
            params={"d": _today_iso(), "l": "MotoGP"},
            timeout=15,
        )
        d = r.json()
        events = d.get("events") or []
        out = []
        skip_terms = ("moto2", "moto3", "qualifying", "practice", "sprint", "warm", "fp1", "fp2", "fp3", "fp4")
        for e in events:
            name = (e.get("strEvent") or "").lower()
            if any(term in name for term in skip_terms):
                continue
            time_local = ""
            t_iso = e.get("strTimestamp")
            if t_iso:
                time_local = _to_local_time(t_iso)
            else:
                t = e.get("strTime") or ""
                if t and t != "00:00:00":
                    try:
                        dt = datetime.fromisoformat(f"{e.get('dateEvent')}T{t}").replace(tzinfo=timezone.utc)
                        time_local = dt.astimezone(CZ_TZ).strftime("%H:%M")
                    except Exception:
                        time_local = t[:5]
            out.append({
                "time": time_local,
                "home": e.get("strEvent") or "MotoGP",
                "away": "Závod",
                "status": "",
            })
        return out
    except Exception as e:
        print(f"  [motogp error] {e}")
        return []


# -------------------- AGGREGATE --------------------

def fetch_today_fixtures() -> dict:
    """Returns dict of today's matches/races per competition, in display order.

    Each entry has a 'sport' field ('football' | 'hockey' | 'other') so the
    frontend can filter by sport subsection (Fotbal / Hokej / Ostatní).
    """
    return {
        # ---------- FOOTBALL — Czech ----------
        "czech_first_league": {
            "sport": "football",
            "label": "Chance Liga (1. liga ČR)",
            "icon": "⚽",
            "matches": fetch_czech_first_league(),
        },
        "czech_cup": {
            "sport": "football",
            "label": "MOL Cup (český pohár)",
            "icon": "🏆",
            "matches": fetch_czech_cup(),
        },
        # ---------- FOOTBALL — English ----------
        "premier_league": {
            "sport": "football",
            "label": "Premier League (1. liga Anglie)",
            "icon": "⚽",
            "matches": fetch_premier_league(),
        },
        "fa_cup": {
            "sport": "football",
            "label": "FA Cup (anglický pohár)",
            "icon": "🏆",
            "matches": fetch_fa_cup(),
        },
        "efl_cup": {
            "sport": "football",
            "label": "EFL Cup (Carabao Cup)",
            "icon": "🏆",
            "matches": fetch_efl_cup(),
        },
        # ---------- FOOTBALL — UEFA clubs ----------
        "champions_league": {
            "sport": "football",
            "label": "Liga mistrů",
            "icon": "🌟",
            "matches": fetch_champions_league(),
        },
        "europa_league": {
            "sport": "football",
            "label": "Evropská liga",
            "icon": "🌍",
            "matches": fetch_europa_league(),
        },
        "conference_league": {
            "sport": "football",
            "label": "Konferenční liga",
            "icon": "🏅",
            "matches": fetch_conference_league(),
        },
        # ---------- FOOTBALL — international (national teams) ----------
        "world_cup": {
            "sport": "football",
            "label": "MS ve fotbale",
            "icon": "🌐",
            "matches": fetch_world_cup(),
        },
        "world_cup_qualifiers": {
            "sport": "football",
            "label": "Kvalifikace MS (UEFA)",
            "icon": "🌐",
            "matches": fetch_world_cup_qualifiers(),
        },
        "euro": {
            "sport": "football",
            "label": "ME ve fotbale",
            "icon": "🇪🇺",
            "matches": fetch_euro(),
        },
        "euro_qualifiers": {
            "sport": "football",
            "label": "Kvalifikace ME",
            "icon": "🇪🇺",
            "matches": fetch_euro_qualifiers(),
        },
        "nations_league": {
            "sport": "football",
            "label": "Liga národů (UEFA)",
            "icon": "🇪🇺",
            "matches": fetch_nations_league(),
        },
        "czech_national_football": {
            "sport": "football",
            "label": "Reprezentace ČR — fotbal",
            "icon": "🇨🇿⚽",
            "matches": fetch_czech_national_football(),
        },
        # ---------- HOCKEY ----------
        "czech_extraliga": {
            "sport": "hockey",
            "label": "Tipsport Extraliga (ČR hokej)",
            "icon": "🏒",
            "matches": fetch_czech_extraliga(),
        },
        "iihf_worlds": {
            "sport": "hockey",
            "label": "MS v hokeji (IIHF)",
            "icon": "🌐",
            "matches": fetch_iihf_worlds(),
        },
        "olympic_hockey": {
            "sport": "hockey",
            "label": "Olympiáda — hokej",
            "icon": "🥇",
            "matches": fetch_olympic_hockey(),
        },
        "czech_national_hockey": {
            "sport": "hockey",
            "label": "Reprezentace ČR — hokej",
            "icon": "🇨🇿🏒",
            "matches": fetch_czech_national_hockey(),
        },
        # ---------- OTHER (motorsport) ----------
        "f1": {
            "sport": "other",
            "label": "Formule 1 — závod",
            "icon": "🏎️",
            "matches": fetch_f1_today(),
        },
        "motogp": {
            "sport": "other",
            "label": "MotoGP — závod",
            "icon": "🏍️",
            "matches": fetch_motogp_today(),
        },
    }
