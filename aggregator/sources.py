"""
RSS feed sources configuration for all tabs.
Each source has: name, url, lang (cs/en), category (subsection within tab).
"""

SOURCES = {
    # Svět očima českých médií
    "world": [
        {"name": "ČT24 – Svět", "url": "https://ct24.ceskatelevize.cz/rss/rubrika/svet-16", "lang": "cs"},
        {"name": "iRozhlas – Zahraničí", "url": "https://www.irozhlas.cz/rss/irozhlas/section/zpravy-svet", "lang": "cs"},
        {"name": "Aktuálně – Zahraničí", "url": "https://zpravy.aktualne.cz/rss/zahranici/", "lang": "cs"},
        {"name": "Novinky – Zahraniční", "url": "https://www.novinky.cz/rss/zahranicni", "lang": "cs"},
        {"name": "Seznam Zprávy", "url": "https://www.seznamzpravy.cz/rss", "lang": "cs"},
    ],

    # Domácí české zpravodajství
    "czech": [
        {"name": "Seznam Zprávy", "url": "https://www.seznamzpravy.cz/rss", "lang": "cs"},
        {"name": "ČT24", "url": "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy", "lang": "cs"},
        {"name": "iRozhlas – Domácí", "url": "https://www.irozhlas.cz/rss/irozhlas/section/zpravy-domov", "lang": "cs"},
        {"name": "Novinky.cz", "url": "https://www.novinky.cz/rss", "lang": "cs"},
        {"name": "Aktuálně – Domácí", "url": "https://zpravy.aktualne.cz/rss/domaci/", "lang": "cs"},
        {"name": "Deník N", "url": "https://denikn.cz/feed/", "lang": "cs"},
        {"name": "E15", "url": "https://www.e15.cz/rss", "lang": "cs"},
        {"name": "Forbes CZ", "url": "https://forbes.cz/feed/", "lang": "cs"},
    ],

    "sport": [
        # Fotbal (priorita 1) — iSport + Aktuálně + Sport.cz
        {"name": "iSport – Fotbal", "url": "http://isport.blesk.cz/rss/56", "lang": "cs", "sub": "football"},
        {"name": "iSport – Česká repre", "url": "http://isport.blesk.cz/rss/72", "lang": "cs", "sub": "football"},
        {"name": "Aktuálně – Fotbal", "url": "https://sport.aktualne.cz/rss/fotbal/", "lang": "cs", "sub": "football"},
        {"name": "Sport.cz", "url": "https://www.sport.cz/rss", "lang": "cs", "sub": "football"},
        # Česká fotbalová liga přes Google News (čistí mix od Sport.cz)
        {"name": "Chance Liga (Google News)", "lang": "cs", "sub": "football",
         "url": "https://news.google.com/rss/search?q=%22Chance+Liga%22+OR+%22Fortuna+Liga%22&hl=cs-CZ&gl=CZ&ceid=CZ:cs"},

        # Hokej (priorita 2)
        {"name": "Aktuálně – Hokej", "url": "https://sport.aktualne.cz/rss/hokej/", "lang": "cs", "sub": "hockey"},
        {"name": "iSport – NHL", "url": "http://isport.blesk.cz/rss/98", "lang": "cs", "sub": "hockey"},
        # Tipsport extraliga přes Google News (iSport extraliga feed je prázdný)
        {"name": "Tipsport extraliga (Google News)", "lang": "cs", "sub": "hockey",
         "url": "https://news.google.com/rss/search?q=%22Tipsport+extraliga%22+OR+%22hokejov%C3%A1+extraliga%22&hl=cs-CZ&gl=CZ&ceid=CZ:cs"},
        # Česká hokejová reprezentace
        {"name": "Česká hokejová repre (Google News)", "lang": "cs", "sub": "hockey",
         "url": "https://news.google.com/rss/search?q=%22%C4%8Desk%C3%A1+hokejov%C3%A1+reprezentace%22&hl=cs-CZ&gl=CZ&ceid=CZ:cs"},

        # Tenis (přes Google News v češtině — čistý český tenisový feed neexistuje)
        {"name": "Tenis (Google News CZ)", "lang": "cs", "sub": "tennis",
         "url": "https://news.google.com/rss/search?q=tenis+ATP+OR+WTA+OR+grand+slam&hl=cs-CZ&gl=CZ&ceid=CZ:cs"},

        # F1
        {"name": "iSport – F1", "url": "http://isport.blesk.cz/rss/57", "lang": "cs", "sub": "f1"},

        # iRozhlas sport jako doplněk (mix všech disciplín — default football)
        {"name": "iRozhlas – Sport", "url": "https://www.irozhlas.cz/rss/irozhlas/section/sport", "lang": "cs", "sub": "football"},
    ],

    "tech": [
        # AI / obecná IT (priorita 1) — české technické weby
        {"name": "Lupa.cz", "url": "https://www.lupa.cz/rss/clanky/", "lang": "cs", "sub": "ai"},
        {"name": "Živě.cz", "url": "https://www.zive.cz/rss/sc-47/default.aspx", "lang": "cs", "sub": "ai"},
        {"name": "Root.cz", "url": "https://www.root.cz/rss/clanky/", "lang": "cs", "sub": "ai"},
        {"name": "Cnews.cz", "url": "https://www.cnews.cz/feed/", "lang": "cs", "sub": "ai"},
        # Startupy
        {"name": "CzechCrunch", "url": "https://cc.cz/feed/", "lang": "cs", "sub": "startups"},
        # Robotika (čistý český zdroj neexistuje — Google News v češtině)
        {"name": "Robotika (Google News CZ)", "lang": "cs", "sub": "robotics",
         "url": "https://news.google.com/rss/search?q=robotika+OR+roboti+OR+robot&hl=cs-CZ&gl=CZ&ceid=CZ:cs"},
    ],

    "culture": [
        # Hudba (priorita 1)
        {"name": "Musicserver CZ", "url": "https://musicserver.cz/rss/zpravy/", "lang": "cs", "sub": "music"},
        {"name": "iRozhlas – Kultura", "url": "https://www.irozhlas.cz/rss/irozhlas/section/kultura", "lang": "cs", "sub": "music"},
        # Film (priorita 2)
        {"name": "Aktuálně – Kultura", "url": "https://magazin.aktualne.cz/rss/kultura/", "lang": "cs", "sub": "film"},
        {"name": "ČT24 – Kultura", "url": "https://ct24.ceskatelevize.cz/rss/rubrika/kultura-15", "lang": "cs", "sub": "film"},
        # Linkin Park + Oasis na konci (Google News v češtině)
        {"name": "Linkin Park (Google News CZ)", "lang": "cs", "sub": "linkin_park",
         "url": "https://news.google.com/rss/search?q=%22Linkin+Park%22&hl=cs-CZ&gl=CZ&ceid=CZ:cs"},
        {"name": "Oasis (Google News CZ)", "lang": "cs", "sub": "oasis",
         "url": "https://news.google.com/rss/search?q=%22Oasis%22+kapela+OR+reunion&hl=cs-CZ&gl=CZ&ceid=CZ:cs"},
    ],

    # Výjimka — anglické zdroje s překladem (český ekvivalent neexistuje)
    "good_news": [
        {"name": "Positive News", "url": "https://www.positive.news/feed/", "lang": "en"},
        {"name": "Good News Network", "url": "https://www.goodnewsnetwork.org/feed/", "lang": "en"},
        {"name": "Sunny Skyz", "url": "https://www.sunnyskyz.com/rss.php", "lang": "en"},
    ],
}

# Articles per tab (override default of 10)
LIMITS = {
    "world": 10,
    "czech": 10,
    "sport": 15,        # higher due to football priority
    "tech": 20,         # AI-focused, more content
    "culture": 10,
    "good_news": 10,
}

# Weather location
WEATHER_LOCATION = {
    "name": "Liberec",
    "latitude": 50.7663,
    "longitude": 15.0543,
}
