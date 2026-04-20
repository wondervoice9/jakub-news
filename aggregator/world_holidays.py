"""Světové a české státní svátky + mezinárodní dny OSN.
Only fixed-date observances. Movable (Easter etc.) not included for simplicity.
"""

WORLD_HOLIDAYS = {
    # January
    "01-01": "Nový rok · Světový den míru",
    "01-04": "Světový den Braillova písma",
    "01-24": "Mezinárodní den vzdělávání",
    "01-27": "Mezinárodní den památky obětí holocaustu",

    # February
    "02-02": "Světový den mokřadů",
    "02-04": "Světový den boje proti rakovině",
    "02-06": "Světový den bezpečnějšího internetu",
    "02-11": "Mezinárodní den žen a dívek ve vědě",
    "02-13": "Světový den rádia",
    "02-14": "Valentýn",
    "02-20": "Světový den sociální spravedlnosti",
    "02-21": "Mezinárodní den mateřského jazyka",

    # March
    "03-01": "Den nulové diskriminace",
    "03-03": "Světový den divoké přírody",
    "03-08": "Mezinárodní den žen (MDŽ)",
    "03-14": "Den čísla Pí · Mezinárodní den matematiky",
    "03-15": "Světový den spotřebitelských práv",
    "03-17": "Den svatého Patrika",
    "03-20": "Mezinárodní den štěstí · První den jara",
    "03-21": "Mezinárodní den lesů · Světový den básní",
    "03-22": "Světový den vody",
    "03-23": "Světový den meteorologie",
    "03-24": "Světový den boje proti tuberkulóze",
    "03-27": "Mezinárodní den divadla",

    # April
    "04-02": "Mezinárodní den dětské knihy",
    "04-07": "Světový den zdraví",
    "04-12": "Mezinárodní den letu člověka do vesmíru",
    "04-15": "Světový den umění",
    "04-17": "Mezinárodní den hemofilie",
    "04-20": "Mezinárodní den češtiny (4/20) · Den čínského jazyka (UN) · Cannabis Day (4/20) · Patriots' Day (USA, Boston Marathon)",
    "04-22": "Den Země",
    "04-23": "Světový den knihy",
    "04-25": "Světový den boje proti malárii",
    "04-26": "Světový den duševního vlastnictví",
    "04-28": "Světový den BOZP",
    "04-29": "Mezinárodní den tance",
    "04-30": "Mezinárodní den jazzu · Pálení čarodějnic",

    # May
    "05-01": "Svátek práce",
    "05-03": "Světový den svobody tisku",
    "05-04": "Star Wars Day (May the 4th)",
    "05-05": "Cinco de Mayo",
    "05-08": "Den vítězství · Mezinárodní den Červeného kříže",
    "05-12": "Mezinárodní den ošetřovatelství",
    "05-15": "Mezinárodní den rodiny",
    "05-17": "Mezinárodní den proti homofobii",
    "05-20": "Světový den včel",
    "05-21": "Světový den kulturní rozmanitosti",
    "05-22": "Mezinárodní den biologické rozmanitosti",
    "05-25": "Africký den · Ručníkový den (Douglas Adams)",
    "05-29": "Mezinárodní den mírových sil OSN",
    "05-31": "Světový den bez tabáku",

    # June
    "06-01": "Mezinárodní den dětí (MDD)",
    "06-04": "Mezinárodní den nevinných dětských obětí agrese",
    "06-05": "Světový den životního prostředí",
    "06-08": "Světový den oceánů",
    "06-12": "Světový den boje proti dětské práci",
    "06-14": "Světový den dárců krve",
    "06-17": "Světový den boje proti suchu a rozšiřování pouští",
    "06-20": "Světový den uprchlíků",
    "06-21": "Mezinárodní den jógy · Letní slunovrat",
    "06-23": "Mezinárodní den OSN",
    "06-26": "Mezinárodní den proti zneužívání drog",

    # July
    "07-01": "Mezinárodní den vtipu",
    "07-05": "Den slovanských věrozvěstů Cyrila a Metoděje",
    "07-06": "Den upálení mistra Jana Husa",
    "07-11": "Světový den populace",
    "07-17": "Světový den emoji · Světový den mezinárodní spravedlnosti",
    "07-18": "Mezinárodní den Nelsona Mandely",
    "07-30": "Mezinárodní den přátelství",

    # August
    "08-08": "Mezinárodní den kočky",
    "08-09": "Mezinárodní den domorodých obyvatel",
    "08-12": "Mezinárodní den mládeže",
    "08-19": "Světový humanitární den",
    "08-26": "Mezinárodní den psů",

    # September
    "09-05": "Mezinárodní den charity",
    "09-08": "Mezinárodní den gramotnosti",
    "09-10": "Světový den prevence sebevražd",
    "09-15": "Mezinárodní den demokracie",
    "09-16": "Mezinárodní den ochrany ozonové vrstvy",
    "09-21": "Mezinárodní den míru · Světový den Alzheimera",
    "09-22": "Světový den bez aut",
    "09-26": "Evropský den jazyků",
    "09-27": "Světový den cestovního ruchu",
    "09-28": "Den české státnosti · Sv. Václav",
    "09-29": "Světový den srdce",
    "09-30": "Mezinárodní den překladu",

    # October
    "10-01": "Mezinárodní den seniorů · Světový den kávy",
    "10-02": "Mezinárodní den nenásilí",
    "10-04": "Světový den zvířat",
    "10-05": "Světový den učitelů",
    "10-08": "Světový den zraku",
    "10-09": "Světový den pošty",
    "10-10": "Světový den duševního zdraví",
    "10-11": "Mezinárodní den dívek",
    "10-15": "Mezinárodní den bílé hole · Světový den mytí rukou",
    "10-16": "Světový den výživy · Den chleba",
    "10-17": "Mezinárodní den boje proti chudobě",
    "10-24": "Den OSN",
    "10-28": "Den vzniku samostatného Československa",
    "10-29": "Světový den psoriázy · Světový den internetu",
    "10-31": "Halloween",

    # November
    "11-01": "Svátek Všech svatých",
    "11-02": "Památka zesnulých (Dušičky)",
    "11-05": "Bonfire Night (UK)",
    "11-11": "Den válečných veteránů · Den sv. Martina",
    "11-14": "Světový den diabetu",
    "11-16": "Mezinárodní den tolerance",
    "11-17": "Den boje za svobodu a demokracii",
    "11-19": "Mezinárodní den mužů · Světový den toalet",
    "11-20": "Světový den dětí (UNICEF)",
    "11-21": "Světový den televize",
    "11-25": "Mezinárodní den proti násilí na ženách",
    "11-29": "Black Friday (obvykle poslední pátek)",

    # December
    "12-01": "Světový den boje proti AIDS",
    "12-03": "Mezinárodní den osob se zdravotním postižením",
    "12-05": "Mikulášská nadílka · Mezinárodní den dobrovolníků",
    "12-10": "Den lidských práv",
    "12-11": "Mezinárodní den hor",
    "12-18": "Mezinárodní den migrantů",
    "12-20": "Mezinárodní den lidské solidarity",
    "12-24": "Štědrý den",
    "12-25": "1. svátek vánoční",
    "12-26": "2. svátek vánoční · Sv. Štěpán",
    "12-31": "Silvestr",
}


def get_world_holiday(month: int, day: int) -> str:
    key = f"{month:02d}-{day:02d}"
    return WORLD_HOLIDAYS.get(key, "")
