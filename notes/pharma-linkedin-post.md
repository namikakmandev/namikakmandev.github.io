# LinkedIn post — The Pharma States of Europe

Study page: https://namikakmandev.github.io/pharma-gdp-share.html
Attach: `assets/pharma-study/01_share_trajectories.png` (or post the link and let
the OG card render — the page's preview image is the same chart).

---

## ★ FINAL POST (ready to publish) — the full-arc version

> Copy the block below. Best as a 3-image carousel: 05 (world ranking),
> 07 (EU product mix), 08 (Korea biologics). Or post the link alone and let
> the preview card render chart 01.

How big is the pharmaceutical industry inside a national economy?

I pulled 35 years of data across 41 countries to find out. The answer broke
into three surprises.

1️⃣ For most economies, pharma is tiny — and stuck. In the median country it's
about 0.5% of GDP, and it hasn't moved in 30 years. Even the United States —
home of the world's biggest drug companies — holds pharma manufacturing at
0.87% of its economy. From Washington to Tokyo, every large economy keeps it
near 1%, decade after decade. It looks almost like a law of large economies.

2️⃣ The exceptions aren't big — they're small. Ireland 16.7%. Denmark 8.7%,
where pharma is now nearly HALF of all manufacturing. Switzerland ~7%. These
aren't pharma superpowers; they're small economies that let one industry
become the economy. In 2023 Germany and Denmark produced almost the same euro
value of pharma — a rounding error in Germany (0.6% of GDP), the national
growth engine in Denmark (6.5%). Concentration, not pharma, is the phenomenon.

3️⃣ What they actually make is a third story. Trade data splits "pharma" into
industries that barely resemble each other: a biologics belt (Ireland,
Belgium, the Netherlands — half their exports are vaccines and antibody
drugs) and a finished-pill belt (France, Italy, Spain). And the single most
striking line in the whole study:

🇰🇷 97% of what South Korea now ships to the EU is biologics — up from under
20% in 2013. Samsung Biologics and Celltrion came online and a country
rewired what it exports in under five years. The customs data caught the
strategy before it ever showed up in a GDP figure.

The lesson I keep coming back to: "pharma's share of GDP" is a single number
that hides three completely different questions — how big, how concentrated,
and what kind. Answer all three and the same industry looks like a rounding
error, a national strategy, and a bet on the future — depending on where you
stand.

Full study, all 41 countries, every chart and the open data pipeline:
https://namikakmandev.github.io/pharma-gdp-share.html

(P.S. — for the folks in my network in Türkiye: we sit at 0.35% of GDP, flat
for two decades while Korea, a fair peer, built biosimilar champions from a
similar start. The gap is strategy, not statistics.)

#pharma #economics #biologics #dataanalysis #healthcare #Korea #Türkiye

Data cut: 4 Aug 2026 · Eurostat nama_10_a64 + nama_10_gdp · 30 countries, 1995–2025
· plus OECD STAN (DF_STAN_2025) for the world extension — 41 countries total.
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

## World-extension draft (EN) — 41 countries

Is pharma's ~1% weight a European quirk? I extended the study to the
Americas and Asia-Pacific with OECD data — same industry (ISIC C21), same
denominator, 41 countries, each at its most recent published year (labelled
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

Full study, all 41 countries, sources and caveats: [link]

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

## Product-mix draft (EN) — "what kind of medicine"

We measured how BIG pharma is in 42 economies. But that never says WHAT
they make. Trade data does — every shipment is filed under a product code —
and it splits "pharma" into industries that barely resemble each other:

💉 The biologics belt. Ireland, Belgium, the Netherlands, Austria — roughly
half of what they export is vaccines and antibody drugs (grown in living
cells, not synthesised). Belgium's share is essentially GSK's vaccine
plants; Ireland's is the mRNA and monoclonal build-out.

💊 The finished-pill belt. France, Italy, Spain, Poland — 70%+ of exports
are packaged, measured-dose medicines. Formulate-and-fill, the classic
pharma most people picture.

🧪 The ingredient suppliers. China's exports to the EU are ~28% antibiotics
and 16% hormones — the upstream active ingredients the pill-makers depend
on. India ships 76% finished generics.

And the single most striking line in the whole study:

🇰🇷 97% of what South Korea ships to the EU is biologics — up from under
20% in 2013. Samsung Biologics and Celltrion came online and a country
rewired what it exports in under five years. The customs data caught the
strategy before it ever showed up in a GDP number.

🇩🇰 Denmark's tell: a 9% hormones slice most countries don't have — the
visible edge of the insulin-and-GLP-1 franchise now driving the whole
economy.

Big honesty note: this is TRADE, a proxy for production, not production
itself. Export value is gross (imported ingredients included), and
distribution hubs re-export goods they didn't make — Slovenia's numbers
were so inflated by routing that I left it out. Details and caveats on the
page.

Full study — size, concentration, and product mix for 41 countries: [link]

#pharma #biologics #economics #Korea #dataanalysis #trade

---

## Posting notes

- The strongest single visual is chart 01 (trajectories). Chart 03 (share of
  manufacturing) is the strongest *second* image if posting a carousel.
- Carousel: `notes/pharma-carousel.pdf` — 7 slides, upload via "Add a
  document". Slide 5 is the Denmark/Ireland comparison, the strongest single
  page. Regenerate with `python3 scripts/pharma_carousel.py`.
- For the world-extension post, lead with chart 05 (41-country ranking, years
  labelled per bar) and follow with 06 (big-economy trajectories).
- For the product-mix post, lead with chart 07 (EU export mix) or go
  straight to 08 (Korea biologics) as the single hook; 09 is the world mix.
- Product mix is TRADE not production: gross export value, re-exports
  inflate hubs (Slovenia dropped), HS 2937/3004 split GLP-1 and insulin.
- Honesty items already handled on the page, keep them if quoting numbers
  elsewhere: C21 is manufacturing only; Ireland suppressed after 2014;
  Iceland excluded (negative GVA); Türkiye 2023-only; Danish GVA includes
  production contracted abroad; 2024–25 first releases may be revised.
- Do not present the 8.7% (2025) and the ranked 6.54% (2023) as the same
  number — they are different years, both labelled on the charts.
