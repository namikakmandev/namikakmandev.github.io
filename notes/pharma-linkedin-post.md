# LinkedIn post — The Pharma States of Europe

Study page: https://namikakmandev.github.io/pharma-gdp-share.html
Attach: `assets/pharma-study/01_share_trajectories.png` (or post the link and let
the OG card render — the page's preview image is the same chart).

Data cut: 4 Aug 2026 · Eurostat nama_10_a64 + nama_10_gdp · 30 countries, 1995–2025
· plus OECD STAN (DF_STAN_2025) for the world extension — 42 countries total.
All numbers below are reproducible from `data/pharma-share.json` and
`data/pharma-share-stan.json`.

---

## Main draft (EN)

How big is pharma inside a national economy?

I pulled 30 years of national accounts for 30 European countries — pharma
manufacturing value added vs GDP, each in its own currency so no exchange
rate touches the ratio.

Two completely different Europes came out.

🔹 The flat mass. In the median country, pharma is ~0.5% of GDP — and it
hasn't moved in 30 years. Germany: 0.5% → 0.6% since 1995. France: 0.6% →
0.55%. Italy, Spain: same story. Three decades of blockbusters and COVID,
and pharma's weight in Europe's big economies is where it started.

🔹 The pharma states. Denmark went 0.8% → 8.7% of GDP — with most of the
jump in 2022–24, the GLP-1 years. Nearly HALF of Danish manufacturing is
now one industry. Between 2019 and 2024, pharma alone was roughly one in
four kroner of Denmark's entire nominal GDP growth. Switzerland climbed
2.1% → 6.7%. Ireland peaked at 12.8% back in 2002 (Eurostat stops
publishing its number after 2014 — the sector is so concentrated it's
confidential).

🔹 The paradox. In 2023 Germany and Denmark produced almost the same pharma
value added — €26bn vs €24bn. In one country that's a rounding error
(0.6% of GDP). In the other it's the national growth engine (6.5%).

🔹 And Türkiye? €3.6bn — bigger than Austria or Poland in absolute terms,
but 0.35% of GDP, bottom third of Europe by weight. One catch: TurkStat has
delivered this sector detail to Eurostat for a single year (2023). No
back-series, no trend, no trajectory. Before we argue about growing the
sector, we need the statistics that would let us see it.

Full study, charts, caveats and the open data pipeline: [link]

#pharma #economics #GDP #dataanalysis #Eurostat #Denmark #Türkiye

---

## World-extension draft (EN) — 42 countries

Is pharma's ~1% weight a European quirk? I extended the study to the
Americas and Asia-Pacific with OECD data — same industry (ISIC C21), same
denominator, 42 countries, each at its most recent published year (labelled
on every bar).

The answer surprised me with how clean it is:

🌍 No economy outside Europe reaches even 1%. The US — home of the largest
pharma companies on earth — keeps pharma MANUFACTURING at 0.87% of its
economy (2023). UK 0.95%, South Korea 0.77%, Japan 0.66%, Canada 0.27%,
Australia 0.17%. And that's not a snapshot: the big four hold a narrow band
around 1% for all 34 years of data. Through biologics, through COVID.

📈 The only clear riser outside Europe: South Korea, 0.52% (2013) → 0.83%
(2020), settling at 0.77% (2023) — the biosimilar strategy showing up in
national accounts.

🇹🇷 Bonus finding for Türkiye: OECD carries the back-series Eurostat lacks
(2003–2021), and it's flat at 0.3–0.5% for two decades. So the 2023
snapshot isn't a young sector ramping up — it's a plateau. The gap with
Korea is strategy, not statistics.

🚫 What the data honestly can't show: China, India, Brazil. Nobody
publishes pharma value added on a comparable national-accounts basis for
them — any "pharma share of China's GDP" number you've seen is a different
measure wearing the same name.

The conclusion sharpened: big economies hold pharma near 1% like a law of
nature. The 5–17% weights (Ireland 16.7%, Denmark 9.8%, Switzerland ~7%)
exist only in small economies that let one industry become the economy.
Concentration, not pharma, is the phenomenon.

Full study, all 42 countries, sources and caveats: [link]

#pharma #economics #OECD #dataanalysis #Korea #Türkiye #USA #Japan

---

## Shorter alternative (EN)

One chart, 30 countries, 30 years.

For the median European economy, pharma manufacturing is half a percent of
GDP — unchanged since 1995.

For Denmark it went from 0.8% to 8.7%. Nearly half of Danish manufacturing
is now pharma, and in 2019–24 the industry accounted for ~1 in 4 kroner of
all Danish nominal GDP growth. One industry — arguably one company.

Same industry, same continent: a rounding error in Germany (0.6% of GDP,
€26bn), the growth engine in Denmark (6.5%, €24bn).

Türkiye: €3.6bn, 0.35% of GDP — and only one year of published data, so
that's a snapshot, not a trend.

Full study with sources and caveats: [link]

---

## Posting notes

- The strongest single visual is chart 01 (trajectories). Chart 03 (share of
  manufacturing) is the strongest *second* image if posting a carousel.
- For the world-extension post, lead with chart 05 (42-country ranking, years
  labelled per bar) and follow with 06 (big-economy trajectories).
- Honesty items already handled on the page, keep them if quoting numbers
  elsewhere: C21 is manufacturing only; Ireland suppressed after 2014;
  Iceland excluded (negative GVA); Türkiye 2023-only; Danish GVA includes
  production contracted abroad; 2024–25 first releases may be revised.
- Do not present the 8.7% (2025) and the ranked 6.54% (2023) as the same
  number — they are different years, both labelled on the charts.
