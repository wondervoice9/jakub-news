"""Today's match fixtures for: Premier League, Czech national football, Czech first league,
Czech hockey extraliga, NHL, Czech national hockey, F1.

All sources are free, no API key required.
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
    """Return today's F1 sessions (race, qualifying, sprint, practice)."""
    today_iso = _today_iso()
    year = datetime.now(CZ_TZ).year
    try:
        r = requests.get(f"{ERGAST_BASE}/{year}.json", timeout=15)
        d = r.json()
        races = d.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        out = []
        for race in races:
            sessions = []
            # Race itself
            if race.get("date"):
                sessions.append(("Závod", race["date"], race.get("time")))
            for key, label in [
                ("Qualifying", "Kvalifikace"),
                ("Sprint", "Sprint"),
                ("SprintQualifying", "Sprint kvalifikace"),
                ("FirstPractice", "1. trénink"),
                ("SecondPractice", "2. trénink"),
                ("ThirdPractice", "3. trénink"),
            ]:
                s = race.get(key)
                if s and s.get("date"):
                    sessions.append((label, s["date"], s.get("time")))
            for label, dte, tme in sessions:
                if dte == today_iso:
                    iso = f"{dte}T{tme}" if tme else f"{dte}T00:00:00Z"
                    out.append({
                        "time": _to_local_time(iso),
                        "home": race.get("raceName", ""),
                        "away": label,
                        "status": "",
                    })
        return out
    except Exception as e:
        print(f"  [f1 ergast error] {e}")
        return []


# -------------------- AGGREGATE --------------------

def fetch_today_fixtures() -> dict:
    """Returns dict in user-requested order:
    premier_league, czech_national_football, czech_first_league,
    czech_extraliga, czech_national_hockey, f1
    """
    return {
        "premier_league": {
            "label": "Premier League",
            "icon": "⚽",
            "matches": fetch_premier_league(),
        },
        "czech_national_football": {
            "label": "Reprezentace ČR — fotbal",
            "icon": "🇨🇿⚽",
            "matches": fetch_czech_national_football(),
        },
        "czech_first_league": {
            "label": "Chance Liga (1. liga ČR)",
            "icon": "⚽",
            "matches": fetch_czech_first_league(),
        },
        "czech_extraliga": {
            "label": "Tipsport Extraliga (ČR hokej)",
            "icon": "🏒",
            "matches": fetch_czech_extraliga(),
        },
        "czech_national_hockey": {
            "label": "Reprezentace ČR — hokej",
            "icon": "🇨🇿🏒",
            "matches": fetch_czech_national_hockey(),
        },
        "f1": {
            "label": "Formule 1",
            "icon": "🏎️",
            "matches": fetch_f1_today(),
        },
    }
