"""Weather, jokes, quote, nameday, week info."""
import os
import json
import requests
from datetime import datetime, date
from google import genai
from google.genai import types


# -------------------- WEATHER --------------------

WEATHER_CODES = {
    0: "Jasno", 1: "Převážně jasno", 2: "Polojasno", 3: "Zataženo",
    45: "Mlha", 48: "Mlha s námrazou",
    51: "Slabé mrholení", 53: "Mrholení", 55: "Silné mrholení",
    61: "Slabý déšť", 63: "Déšť", 65: "Silný déšť",
    71: "Slabé sněžení", 73: "Sněžení", 75: "Silné sněžení",
    77: "Sněhová zrna",
    80: "Přeháňky", 81: "Silné přeháňky", 82: "Prudké přeháňky",
    85: "Sněhové přeháňky", 86: "Silné sněhové přeháňky",
    95: "Bouřka", 96: "Bouřka s kroupami", 99: "Silná bouřka s kroupami",
}


def fetch_weather(lat: float, lon: float, name: str) -> dict:
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m",
                "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_sum",
                "timezone": "Europe/Prague",
                "forecast_days": 3,
            },
            timeout=15,
        )
        data = resp.json()
        current = data.get("current", {})
        daily = data.get("daily", {})

        forecast = []
        for i in range(len(daily.get("time", []))):
            code = daily["weather_code"][i]
            forecast.append({
                "date": daily["time"][i],
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "weather_code": code,
                "weather_desc": WEATHER_CODES.get(code, "—"),
                "precipitation": daily["precipitation_sum"][i],
            })

        current_code = current.get("weather_code", 0)
        return {
            "location": name,
            "current": {
                "temperature": current.get("temperature_2m"),
                "weather_code": current_code,
                "weather_desc": WEATHER_CODES.get(current_code, "—"),
                "wind_speed": current.get("wind_speed_10m"),
                "humidity": current.get("relative_humidity_2m"),
            },
            "forecast": forecast,
        }
    except Exception as e:
        print(f"  [weather error] {e}")
        return {"location": name, "error": str(e)}


# -------------------- NAMEDAY --------------------

def fetch_nameday() -> str:
    from .namedays import get_nameday_for
    now = datetime.now()
    return get_nameday_for(now.month, now.day)


def fetch_world_holiday() -> str:
    from .world_holidays import get_world_holiday
    now = datetime.now()
    return get_world_holiday(now.month, now.day)


# -------------------- WEEK INFO --------------------

CZ_DAYS = ["Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek", "Sobota", "Neděle"]
CZ_MONTHS = [
    "ledna", "února", "března", "dubna", "května", "června",
    "července", "srpna", "září", "října", "listopadu", "prosince",
]


def today_info() -> dict:
    now = datetime.now()
    week_num = now.isocalendar().week
    return {
        "day_name": CZ_DAYS[now.weekday()],
        "date_cz": f"{now.day}. {CZ_MONTHS[now.month - 1]} {now.year}",
        "date_iso": now.strftime("%Y-%m-%d"),
        "week_number": week_num,
        "week_parity": "sudý" if week_num % 2 == 0 else "lichý",
    }


# -------------------- JOKES --------------------

def fetch_joke_en() -> dict:
    doy = datetime.now().strftime("%Y%m%d")
    try:
        resp = requests.get(
            "https://v2.jokeapi.dev/joke/Any",
            params={
                "type": "single",
                "blacklistFlags": "nsfw,religious,political,racist,sexist,explicit",
                "lang": "en",
            },
            timeout=15,
        )
        data = resp.json()
        return {
            "id": f"joke_en_{doy}",
            "text": data.get("joke", ""),
            "source": "JokeAPI",
            "source_url": "https://jokeapi.dev/",
        }
    except Exception as e:
        print(f"  [joke EN error] {e}")
        return {"id": f"joke_en_{doy}", "text": "", "source": "JokeAPI", "error": str(e)}


def _scrape_alik_jokes() -> list[str]:
    """Scrape jokes from alik.cz/v (Czech humor portal)."""
    from bs4 import BeautifulSoup
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get("https://www.alik.cz/v", headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        out = []
        for el in soup.select(".vtip-text"):
            text = el.get_text("\n", strip=True)
            if 30 < len(text) < 800:
                out.append(text)
        return out
    except Exception as e:
        print(f"  [alik scrape error] {e}")
        return []


def fetch_joke_cs() -> dict:
    """Scrape today's joke from alik.cz (rotated deterministically by day-of-year)."""
    doy_str = datetime.now().strftime("%Y%m%d")
    jokes = _scrape_alik_jokes()
    if jokes:
        idx = datetime.now().timetuple().tm_yday % len(jokes)
        return {
            "id": f"joke_cs_{doy_str}",
            "text": jokes[idx],
            "source": "Alík.cz",
            "source_url": "https://www.alik.cz/v",
        }
    # Last-resort fallback (Alík unreachable): curated rotating list.
    from .jokes_cs import get_joke_for_day
    doy = datetime.now().timetuple().tm_yday
    return {
        "id": f"joke_cs_{doy_str}",
        "text": get_joke_for_day(doy),
        "source": "Kurátorovaný výběr",
        "source_url": None,
    }


# -------------------- QUOTE --------------------

def _fetch_author_bio(author: str) -> str:
    """Use Gemini to generate a 1-2 sentence Czech bio of the quote author. Optional."""
    if not author or author.lower() in ("unknown", "anonymous", "neznámý"):
        return ""
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key or api_key == "PASTE_YOUR_KEY_HERE":
            return ""
        client = genai.Client(api_key=api_key)
        prompt = (
            f"Napiš krátký česky bio o osobě '{author}' — jednou větou kdo byl/je, "
            f"druhou větou roky života a hlavní činnost. Maximálně 2 věty, celkem max 200 znaků. "
            f"Žádný úvod, odpověz přímo bio."
        )
        resp = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return (resp.text or "").strip()
    except Exception as e:
        print(f"    [author bio error] {e}")
        return ""


def _scrape_citaty_net() -> dict | None:
    """Scrape a random Czech quote (already in Czech) from citaty.net."""
    from bs4 import BeautifulSoup
    import re
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get("https://citaty.net/citaty/nahodny-citat/", headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["nav", "header", "footer", "script", "style"]):
            tag.decompose()
        text = ""
        h1_with_quote = None
        for h1 in soup.select("h1"):
            t = h1.get_text(strip=True)
            if "„" in t or "“" in t:
                h1_with_quote = h1
                m = re.search(r"„(.+?)[\u201c\u201d\"]", t)
                text = m.group(1).strip() if m else t.strip("„“”\"\u201c\u201d ")
                break
        if not text:
            return None
        # Author: a link to /autori/<slug>/ near the quote (skip the "Autoři" menu link)
        author = ""
        author_url = None
        scope = h1_with_quote.find_parent(["article", "section", "div"]) or soup
        for a in scope.find_all("a", href=True):
            href = a["href"]
            if "/autori/" in href and href.rstrip("/") != "/autori":
                name = a.get_text(strip=True)
                if name and 2 < len(name) < 80:
                    author = name
                    author_url = f"https://citaty.net{href}" if href.startswith("/") else href
                    break
        return {
            "text": text,
            "author": author or "Neznámý",
            "author_url": author_url,
        }
    except Exception as e:
        print(f"  [citaty.net scrape error] {e}")
        return None


def fetch_quote() -> dict:
    """Fetch a Czech quote from a Czech site (citaty.net). No translation."""
    doy = datetime.now().strftime("%Y%m%d")
    qid = f"quote_{doy}"
    scraped = _scrape_citaty_net()
    if scraped:
        author_bio = _fetch_author_bio(scraped["author"])
        return {
            "id": qid,
            "text": scraped["text"],
            "author": scraped["author"],
            "author_bio": author_bio,
            "source": "Citáty.net",
            "source_url": scraped.get("author_url") or "https://citaty.net/",
        }
    return {
        "id": qid,
        "text": "",
        "author": "",
        "author_bio": "",
        "source": "Citáty.net",
        "source_url": "https://citaty.net/",
        "error": "scrape failed",
    }
