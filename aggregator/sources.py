"""
RSS feed sources configuration for all tabs.
Each source has: name, url, lang (cs/en), category (subsection within tab).
"""

SOURCES = {
    "world": [
        {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "lang": "en"},
        {"name": "Guardian World", "url": "https://www.theguardian.com/world/rss", "lang": "en"},
        {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "lang": "en"},
        {"name": "NPR World", "url": "https://feeds.npr.org/1004/rss.xml", "lang": "en"},
        {"name": "NYT World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "lang": "en"},
        {"name": "DW World", "url": "https://rss.dw.com/xml/rss-en-world", "lang": "en"},
    ],

    "czech": [
        {"name": "Seznam Zprávy", "url": "https://www.seznamzpravy.cz/rss", "lang": "cs"},
        {"name": "E15", "url": "https://www.e15.cz/rss", "lang": "cs"},
        {"name": "ČT24", "url": "https://ct24.ceskatelevize.cz/rss", "lang": "cs"},
        {"name": "iRozhlas", "url": "https://www.irozhlas.cz/rss/irozhlas", "lang": "cs"},
        {"name": "Forbes CZ", "url": "https://forbes.cz/feed/", "lang": "cs"},
    ],

    "sport": [
        # Czech first league (football) — Google News with targeted query
        {"name": "Česká liga (fotbal)", "lang": "cs", "sub": "football",
         "url": "https://news.google.com/rss/search?q=%22Chance+Liga%22+OR+%22Fortuna+Liga%22+OR+%22%C4%8Desk%C3%A1+fotbalov%C3%A1+liga%22&hl=cs-CZ&gl=CZ&ceid=CZ:cs"},
        # Czech national football team
        {"name": "Česká fotbalová reprezentace", "lang": "cs", "sub": "football",
         "url": "https://news.google.com/rss/search?q=%22%C4%8Desk%C3%A1+fotbalov%C3%A1+reprezentace%22&hl=cs-CZ&gl=CZ&ceid=CZ:cs"},
        # English Premier League — use BBC (football-only feed)
        {"name": "BBC Football (Premier League)", "url": "https://feeds.bbci.co.uk/sport/football/premier-league/rss.xml", "lang": "en", "sub": "football"},
        {"name": "Guardian Premier League", "url": "https://www.theguardian.com/football/premierleague/rss", "lang": "en", "sub": "football"},
        {"name": "Sky Sports Premier League", "url": "https://www.skysports.com/rss/12040", "lang": "en", "sub": "football"},
        # International football (national teams)
        {"name": "BBC Football (international)", "url": "https://feeds.bbci.co.uk/sport/football/world/rss.xml", "lang": "en", "sub": "football"},

        # Czech hockey extraliga
        {"name": "Česká hokejová extraliga", "lang": "cs", "sub": "hockey",
         "url": "https://news.google.com/rss/search?q=%22Tipsport+extraliga%22+OR+%22hokejov%C3%A1+extraliga%22&hl=cs-CZ&gl=CZ&ceid=CZ:cs"},
        # Czech hockey national team
        {"name": "Česká hokejová reprezentace", "lang": "cs", "sub": "hockey",
         "url": "https://news.google.com/rss/search?q=%22%C4%8Desk%C3%A1+hokejov%C3%A1+reprezentace%22&hl=cs-CZ&gl=CZ&ceid=CZ:cs"},
        # NHL
        {"name": "NHL News", "lang": "en", "sub": "hockey",
         "url": "https://news.google.com/rss/search?q=NHL+hockey&hl=en-US&gl=US&ceid=US:en"},
        {"name": "BBC Ice Hockey", "url": "https://feeds.bbci.co.uk/sport/ice-hockey/rss.xml", "lang": "en", "sub": "hockey"},

        # Tennis
        {"name": "BBC Tennis", "url": "https://feeds.bbci.co.uk/sport/tennis/rss.xml", "lang": "en", "sub": "tennis"},

        # F1
        {"name": "BBC F1", "url": "https://feeds.bbci.co.uk/sport/formula1/rss.xml", "lang": "en", "sub": "f1"},
        {"name": "Autosport F1", "url": "https://www.autosport.com/rss/f1/news/", "lang": "en", "sub": "f1"},
    ],

    "tech": [
        # AI-focused (priority)
        {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "lang": "en", "sub": "ai"},
        {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "lang": "en", "sub": "ai"},
        {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "lang": "en", "sub": "ai"},
        {"name": "Wired AI", "url": "https://www.wired.com/feed/tag/ai/latest/rss", "lang": "en", "sub": "ai"},
        {"name": "Ars Technica AI", "url": "https://arstechnica.com/ai/feed/", "lang": "en", "sub": "ai"},
        {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "lang": "en", "sub": "startups"},
        # Startups
        {"name": "TechCrunch Startups", "url": "https://techcrunch.com/category/startups/feed/", "lang": "en", "sub": "startups"},
        # Robotics
        {"name": "IEEE Spectrum Robotics", "url": "https://spectrum.ieee.org/feeds/topic/robotics.rss", "lang": "en", "sub": "robotics"},
        # Czech tech
        {"name": "Lupa.cz", "url": "https://www.lupa.cz/rss/clanky/", "lang": "cs", "sub": "ai"},
        {"name": "Živě.cz", "url": "https://www.zive.cz/rss/sc-47/default.aspx", "lang": "cs", "sub": "ai"},
        {"name": "CzechCrunch", "url": "https://cc.cz/feed/", "lang": "cs", "sub": "startups"},
    ],

    "culture": [
        # Music (priority 1)
        {"name": "Rolling Stone", "url": "https://www.rollingstone.com/music/music-news/feed/", "lang": "en", "sub": "music"},
        {"name": "NME Music", "url": "https://www.nme.com/news/music/feed", "lang": "en", "sub": "music"},
        {"name": "Musicserver CZ", "url": "https://musicserver.cz/rss/zpravy/", "lang": "cs", "sub": "music"},
        {"name": "Pitchfork", "url": "https://pitchfork.com/rss/news/", "lang": "en", "sub": "music"},
        # Film (priority 2)
        {"name": "Variety", "url": "https://variety.com/feed/", "lang": "en", "sub": "film"},
        {"name": "IndieWire", "url": "https://www.indiewire.com/feed", "lang": "en", "sub": "film"},
        {"name": "The Film Stage", "url": "https://thefilmstage.com/feed/", "lang": "en", "sub": "film"},
        {"name": "Empire", "url": "https://www.empireonline.com/feed/", "lang": "en", "sub": "film"},
        # Linkin Park + Oasis (at the end)
        {"name": "Linkin Park News", "url": "https://news.google.com/rss/search?q=%22Linkin+Park%22&hl=en-US&gl=US&ceid=US:en", "lang": "en", "sub": "linkin_park"},
        {"name": "Oasis News", "url": "https://news.google.com/rss/search?q=%22Oasis+band%22+OR+%22Oasis+reunion%22&hl=en-US&gl=US&ceid=US:en", "lang": "en", "sub": "oasis"},
    ],

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
