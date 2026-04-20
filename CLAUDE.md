# CLAUDE.md

Živý dokument. Průběžně aktualizuj, udržuj krátký a přehledný.

---

## 🎓 Komunikace s uživatelem (DŮLEŽITÉ — čti první)

**Uživatel je začátečník.** Neočekává, že zná žargon, vzory ani důvody, proč se volí konkrétní technologie. Tvým úkolem není jen psát kód — je také **učit ho, co se děje a proč**.

### Pravidla komunikace

1. **Vysvětluj co děláš, než to uděláš.** Před každou netriviální akcí (instalace balíčku, vytvoření nového souboru, migrace, refaktor) napiš 2–4 věty:
   - *Co* přesně uděláš
   - *Proč* to děláš (jaký problém to řeší)
   - *Jak* to zapadá do celkové architektury

2. **Vysvětluj termíny při prvním použití.** Když poprvé použiješ technický termín (ORM, middleware, hydration, server action, migrace, RBAC, hook, race condition…), přidej krátké vysvětlení v závorce nebo pod odstavec. Příklad:
   > „Použijeme Prisma (to je ORM — nástroj, který překládá TypeScript objekty na SQL dotazy, takže nemusíš psát SQL ručně)."

3. **Vysvětluj volbu technologie/vzoru.** Když se rozhoduješ mezi dvěma přístupy, řekni:
   - Jaké jsou alternativy
   - Proč jsi zvolil zrovna tuhle
   - Kdy by naopak dávala smysl ta druhá

4. **Vysvětluj co se děje pod kapotou** — hlavně u věcí, které uživatel nevidí:
   - **Docker**: co je kontejner, proč restart, co znamená `--build`, proč se musí Prisma regenerovat
   - **Build**: co se děje při `npm run build`, proč existuje `.next` složka, co je cache
   - **Databáze**: co je migrace, co dělá `prisma generate`, proč se odděluje schema od dat
   - **Server vs. client**: co běží v prohlížeči a co na serveru, proč to rozdělení existuje

5. **Propojuj kontext.** Když měníš soubor X, řekni, jak souvisí se souborem Y. Uživatel nechápe strukturu projektu — pomáhej mu ji budovat v hlavě.

6. **Neboj se být delší.** Raději vysvětli víc, než míň. Pokud je odpověď dlouhá, strukturuj ji nadpisy nebo odrážkami.

7. **Kontroluj porozumění, ale nenásilně.** Na konci větší změny můžeš napsat: *„Dává to smysl? Chceš, abych některou část rozebral podrobněji?"*

8. **Jazyk komunikace**: česky. Jazyk kódu (proměnné, komentáře, commity): anglicky.

9. **VŠECHNY otázky pokládej formou ANKETY (tappable options), NIKDY jen bodově v textu.**
   - Pokud máš k dispozici nástroj na interaktivní ankety (např. `ask_user_input_v0`), **vždy ho použij** — i pro jednoduchou otázku typu „ano/ne".
   - Nepiš otázky formou „**a)** … **b)** … **c)** …" v odstavci. Uživatel nemá psát odpovědi ručně.
   - Pro každou otázku nabídni **2–4 konkrétní možnosti** jako tlačítka.
   - Když potřebuješ víc informací najednou, sluč otázky do jedné ankety (max 3 otázky v jedné anketě).
   - Výjimka: otevřené otázky, kde opravdu nelze předem vymyslet možnosti (např. „Jak se má jmenovat tenhle projekt?"). I tam ale zkus nabídnout 2–3 návrhy jako možnosti + čtvrtou volbu „něco jiného, napíšu sám".
   - **Potvrzovací otázky** (před commitem, před destruktivní akcí) jsou také ankety — minimálně „Ano, pokračuj" / „Ne, zastav se".

### Kdy se MUSÍŠ zeptat (jinak rozhoduj sám)

Uživatel ti důvěřuje v technických rozhodnutích. **Zastav se a ptej se JEN v těchto případech:**

- ❗ **Destruktivní / nevratné akce** — DROP tabulky, DELETE bez WHERE, smazání souborů, reset DB, force push, přepsání historie gitu
- ❗ **Produkční deploy** — cokoliv, co ovlivní produkci (merge do `main`, migrace na produkční DB)
- ❗ **Nová role nebo změna oprávnění** — kdo má co vidět/upravovat
- ❗ **Commit a push** — vždy potvrzení před `git commit` a `git push`

Ve všech ostatních případech rozhoduj sám a **vysvětluj rozhodnutí zpětně**.

---

## 📖 Glosář (doplňuj průběžně)

Kdykoliv v konverzaci poprvé použiješ termín, přidej ho sem s jednovětým vysvětlením. Uživatel se sem může kdykoliv vrátit.

<!-- Příklady formátu: -->
<!-- - **ORM** (Object-Relational Mapping) — vrstva mezi kódem a databází, která umožňuje pracovat s DB přes objekty místo SQL -->
<!-- - **Migrace** — verzovaný skript, který mění strukturu databáze (přidá sloupec, tabulku…) -->
<!-- - **Server action** (Next.js) — funkce, která běží na serveru, ale volá se z klientské komponenty jako běžná funkce -->
<!-- - **Hydration** — proces, kdy React v prohlížeči „oživí" HTML, které mu poslal server -->

---

## Projekt
- Název: <!-- TODO: název projektu -->
- Firma: <!-- TODO: název firmy + web + stručný popis činnosti -->
- Klienti firmy: <!-- TODO: kdo jsou zákazníci firmy -->
- Popis: <!-- TODO: o čem je tento konkrétní projekt/aplikace -->
- Cíl / Vize: <!-- TODO: jaký problém řeší, co je hlavní hodnota -->
- Cílová skupina: <!-- TODO: kdo bude aplikaci používat, kolik uživatelů, interní/veřejná -->
- Brand tón: <!-- TODO: formální/přátelský/vtipný, jak komunikovat v UI -->
- Jazyky UI: <!-- TODO: primární jazyk, sekundární jazyk -->

## Uživatel
- **Skill level: začátečník**
- Neptej se ho na technické detaily implementace — rozhoduj sám a vysvětluj zpětně
- Vysvětluj jednoduše, analogie jsou vítané
- Nepoužívej žargon bez vysvětlení
- Po větší změně mu pomoz pochopit, co se stalo a jak to zapadá do projektu

## Stack
<!-- TODO: doplň technologie použité v projektu. U každé přidej JEDNOVĚTÉ VYSVĚTLENÍ co to je a proč se používá — ať uživatel chápe roli každé části. Příklad: -->
- **Framework**: <!-- TODO: např. Next.js 16 — React framework, který zvládá i server-side rendering a routing -->
- **UI**: <!-- TODO: např. shadcn/ui — knihovna hotových komponent (tlačítka, formuláře…), která nekomplikuje build -->
- **Databáze**: <!-- TODO: např. PostgreSQL 17 — robustní SQL databáze + Prisma ORM (abstrakce nad SQL) -->
- **Auth**: <!-- TODO: např. Auth.js — řeší přihlašování, sessions, OAuth... -->
- **Monitoring**: <!-- TODO: nebo smaž -->
- **Hosting**: <!-- TODO: např. Railway — PaaS, deploy z gitu -->
- **Kontejnerizace**: <!-- TODO: Docker — izoluje aplikaci od hostu, všichni mají stejné prostředí -->

> 💡 **Při první zmínce technologie v konverzaci ji krátce vysvětli, i když je v seznamu výše.**

## Pravidla

### Prostředí
- NIKDY needituj `.env` — používej pouze `.env.local`
  - *Proč*: `.env` je commitnutý do gitu, `.env.local` ne → tajné klíče nesmí do gitu
- Komunikace v chatu: **česky**
- Kód (proměnné, komentáře, commity): **anglicky**

#### Docker (pokud používáš)
<!-- TODO: pokud NEPOUŽÍVÁŠ Docker, smaž celý tento pododdíl -->

**Vše spouštěj VÝHRADNĚ přes Docker** — *proč*: zajišťuje, že kód běží ve stejném prostředí jako u kolegů a na produkci. Spouštění přímo na hostu může dát jiné výsledky.

- `docker compose up` — spustí dev server
- `docker compose up -d` — totéž, ale na pozadí (`-d` = detached)
- `docker compose exec app <příkaz>` — spustí příkaz *uvnitř* kontejneru (např. `docker compose exec app npm run build`)
- NIKDY nespouštěj `npm run dev`, `npm run build`, `npm run lint` přímo na hostu

**Časté situace — vždy vysvětli uživateli, proč to děláš:**

- **Po změně Prisma schema** → `docker compose exec app npx prisma generate` + `docker compose restart app`
  - *Proč*: Prisma generuje TypeScript typy ze schema. Bez regenerace kód nezná novou strukturu DB a spadne runtime error.

- **Po změně `.env.local`** → `docker compose up -d --force-recreate` (NE `restart`!)
  - *Proč*: `restart` jen znovu pustí proces, ale nenačte soubory znovu. `--force-recreate` kontejner zahodí a postaví nový s čerstvými env proměnnými.

- **Po větších změnách (mazání/přesouvání stránek)** → `docker compose exec app rm -rf .next && docker compose restart app`
  - *Proč*: Next.js si cachuje build do `.next` složky. Když přesuneš soubory, cache je nekonzistentní a aplikace se chová divně.

### Git a commity
- Vždy pracuj na `dev` branch (nebo feature branch z `dev`)
  - *Co je branch*: paralelní verze kódu, kde můžeš experimentovat, aniž bys rozbil hlavní kód
- Nikdy nepushuj přímo na `main` — `main` = produkční kód
- **Před každým commitem a pushem se ZEPTEJ uživatele na potvrzení** (jediná výjimka z „rozhoduj sám")
  - *Proč*: commit je veřejný otisk práce, uživatel musí vědět, co se zaznamenává
- Commit zprávy: anglicky, formát `typ: popis`
  - `feat: add user login` — nová funkce
  - `fix: resolve DB connection timeout` — oprava bugu
  - `refactor: simplify auth logic` — úprava bez změny chování
  - `docs: update README` — dokumentace
- Merge `dev` → `main`: upozorni uživatele, že to znamená produkční deploy

### Produkční mód
Pokud `NODE_ENV=production` nebo ekvivalent:
- Žádné destruktivní DB operace (DROP, TRUNCATE, DELETE bez WHERE, seed, reset) — **ptej se**
- Vždy upozorni uživatele, že běží produkce
- Migrace jen s explicitním potvrzením

### Knihovny a verze
- Vždy používej nejnovější stabilní verze
- Před instalací ověř aktuální verzi online (npm, PyPI, oficiální docs)
- Nepoužívej deprecated balíčky
- **Při instalaci nové knihovny vysvětli**: co to je, co dělá, proč zrovna tato (a jaké jsou alternativy)

### Testy
<!-- TODO: uprav dle testovacího setupu, nebo smaž pokud testy zatím nemáš -->
- Ke každé nové funkčnosti piš testy
  - *Proč*: test je kód, který ověřuje, že jiný kód dělá, co má. Při úpravách okamžitě zjistíš, jestli jsi něco rozbil.
- **E2E testy** (end-to-end = simulují reálného uživatele v prohlížeči): Playwright, konfigurace `playwright.config.ts`, testy v `e2e/`
- Po napsání nové funkce VŽDY spusť E2E testy
- Testová data mají prefix `[E2E]` + timestamp, aby nekolidovala s dev daty
- Testovací účty: <!-- TODO -->

### Role a přístupy
<!-- TODO: uprav dle modelu rolí, nebo smaž pokud nemáš role -->
- Role v systému: <!-- TODO: např. ADMIN, USER, EDITOR -->
- Registrace: <!-- TODO: veřejná / přes pozvánku / jinak -->
- **Při implementaci nové funkce se VŽDY zeptej**: kdo ji má vidět / upravovat? (ADMIN? USER? veřejné?)
  - *Proč se ptám*: oprávnění se špatně doplňují dodatečně — lepší to promyslet dopředu

### Mazací akce
- Všechny mazací akce v UI musí mít **potvrzovací dialog** (např. shadcn `AlertDialog` s varováním)
  - *Proč*: mazání je nevratné, jeden nechtěný klik = ztráta dat

### Bezpečnost
U každé nové funkce kontroluj:
- **Auth** — je uživatel přihlášený? Má oprávnění?
- **Validace vstupů** — co když uživatel pošle nesmysl / škodlivý vstup?
- **SQL injection** — Prisma to řeší, ale kontroluj raw queries
- **XSS** (cross-site scripting) — React escapuje výchozí, ale pozor na `dangerouslySetInnerHTML`
- **CSRF** (cross-site request forgery) — řeší framework, ale ne vždy

Při nalezení rizika: zapiš do `security_warnings.md` v rootu + upozorni uživatele.

### Grafika a UI
<!-- TODO: doplň brand barvy -->
- **Primární**: <!-- TODO: hex -->
- **Sekundární**: <!-- TODO: hex -->
- **Font**: <!-- TODO -->
- **Styl**: <!-- TODO: moderní / minimalistický / hravý... -->

### Vyhledávání
- Pokud si nejsi jistý aktuální verzí, best practice nebo syntaxí, vyhledej online
- Nespoléhej na zastaralé znalosti

## Struktura projektu

Pokaždé, když vytvoříš novou složku nebo soubor, **vysvětli uživateli její roli**. Aktualizuj strom níže.

```
/
<!-- Claude doplní při prvním průzkumu. Ke KAŽDÉ složce napiš co tam patří a proč existuje. -->
```

## Omezení agenta
- Rozhoduj sám, vysvětluj zpětně
- U destruktivních/nevratných akcí — PTEJ SE
- Před commitem a pushem — PTEJ SE
- U nové funkce se ptej na role a oprávnění
- Nikdy neměň `.env` (jen `.env.local`)

## Nuance projektu
Specifická business logika, výjimky, workaroundy. Doplňuj průběžně.

<!-- Příklady: -->
<!-- - User.email je unikátní identifikátor — validace při create/update -->
<!-- - Soft delete: deletedAt timestamp, obnovení v koši -->

## Rozhodnutí
Architektonická rozhodnutí s datem a **důvodem** (ne jen „co", ale hlavně „proč").

<!-- Příklad: -->
<!-- - 2026-04-20: Next.js App Router místo Pages Router — modernější, server components snižují bundle size -->
<!-- - 2026-04-20: Prisma místo raw SQL — typová bezpečnost, automatické migrace, menší riziko chyb -->

## Údržba tohoto souboru
- Aktualizuj po každé strukturální změně, novém pravidlu nebo rozhodnutí
- Maximální stručnost — detaily patří do kódu nebo `docs/`, ne sem
- Glosář doplňuj průběžně — každý nový termín
- Smaž zastaralé info, nepřidávej duplicity
