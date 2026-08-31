# Forecaster skill — LinkedIn assets

## What to upload

Upload **three images, in this order.** All three regenerate with
`python3 scripts/ecb_forecaster_skill.py`.

| # | File | Size | Why it is there |
|---|---|---|---|
| 1 | `assets/linkedin/ecb-forecaster-hero.png` | 1600&times;1600, 125 KB | The one people see in the feed without tapping. Square, big type. |
| 2 | `assets/linkedin/ecb-forecaster-skill.png` | 1600&times;1314, 114 KB | The full grid. Tap to zoom. |
| 3 | `assets/linkedin/ecb-forecaster-ranges.png` | 1600&times;1188, 123 KB | Best vs worst, year by year. The width story. |

**Plus one link in the body:** `namikakmandev.github.io/ecb-forecaster-skill.html`

Nothing else. No PDF, no document post, no video.

### Why the hero image exists

The grid is 64 rows by 26 columns. LinkedIn renders a feed image at roughly
500px wide on a phone, so a 1600px chart shrinks by more than 3&times; and every
label in it becomes about 5px tall &mdash; unreadable. Checked, not assumed:
rendered at 500px the colour pattern still reads (the red columns are obvious)
but the years and percentages are gone.

So image 1 carries the point on its own at feed size, and images 2 and 3 are
for the people who tap. Do not post the grid first.

### Alt text (LinkedIn asks; it matters for reach)

1. Bar chart of the share of the ECB forecaster panel whose own 80% range
   contained that year's euro-area inflation, 2000 to 2025. Four bars sit at
   zero: 2008, 2021, 2022 and 2023.
2. A grid of 64 anonymous ECB forecasters by 26 years. Green means inflation
   landed inside the range that forecaster published, red means it did not. The
   2008 and 2021 to 2023 columns are solid red.
3. The published 80% ranges of the best and the worst forecaster on the panel,
   year by year, against actual inflation. The best one's ranges are twice as
   wide.

Every number: 64 forecasters with 10+ scored years, 1,184 one-year-ahead
forecasts, euro-area inflation 2000&ndash;2025.

---

## Before posting

- [ ] **Never name or guess a forecaster.** The ECB publishes panellists only by
      number. #016 and #101 stay numbers.
- [ ] Tag **@European Central Bank** once, in the body. Their open data, used as
      intended.
- [ ] Do not say this tests the ECB's own staff projections. It doesn't — the SPF
      is a survey of outside institutions.
- [ ] Lead with the width caveat if anyone pushes back. It's the honest part.

---

## English

I price for a living. Which means every year I build a plan on top of somebody
else's inflation forecast.

In 2022 euro-area inflation came in at 8.4%. Not one of the ECB's fifty
forecasters had that inside the range they had published.

So I went back and checked all 26 years. The ECB publishes each forecaster
separately, not just the average everyone quotes.

[ image 2 &mdash; the grid ]

Green = inflation landed inside the range that forecaster published.
Red = it didn't.

2008. Then 2021, 2022, 2023. Nobody. The years I most needed a range were the
years the range was worthless.

[ image 3 &mdash; best vs worst ]

And the best of the 64? His ranges are twice as wide as the worst one's. Width
alone explains 47% of the score.

So half of being good at this is just admitting you don't know.

It changed how I read a forecast. Now I ask two things instead of one: how often
were you inside your range, and how wide did the range have to be.

1 of 64 ever cleared their own 80% bar.

Every number and the code → namikakmandev.github.io/ecb-forecaster-skill.html
Data: @European Central Bank Survey of Professional Forecasters, published openly.

---

## Türkçe

Fiyatlama yapıyorum. Yani her yıl, başkasının enflasyon tahmininin üstüne plan
kuruyorum.

2022'de euro bölgesi enflasyonu %8,4 geldi. ECB'nin elli tahmincisinden tek
birinin bile yayımladığı aralığın içinde değildi.

Ben de 26 yılın hepsine baktım. ECB herkesin alıntıladığı ortalamayı değil, her
tahminciyi ayrı ayrı yayımlıyor.

[ görsel 2 &mdash; ızgara ]

Yeşil = enflasyon o tahmincinin açıkladığı aralığın içine düştü.
Kırmızı = düşmedi.

2008. Sonra 2021, 2022, 2023. Hiç kimse. Aralığa en çok ihtiyaç duyduğum
yıllarda aralık işe yaramıyordu.

[ görsel 3 &mdash; en iyi ve en kötü ]

Peki 64 kişinin en iyisi? Aralıkları en kötününkinin iki katı geniş. Skorun
%47'sini tek başına genişlik açıklıyor.

Yani bu işte iyi olmanın yarısı, bilmediğini kabul etmek.

Bir tahmini okuma şeklimi değiştirdi. Artık tek soru değil iki soru soruyorum:
kaç kez aralığın içinde kaldın, ve aralık bunun için ne kadar geniş olmak
zorunda kaldı.

64 tahminciden yalnızca 1'i kendi %80 çıtasını tutturdu.

Bütün sayılar ve kod → namikakmandev.github.io/ecb-forecaster-skill.html
Veri: @European Central Bank Survey of Professional Forecasters, açık kaynak.

---

## Pinned comment

The data is open and the code is stdlib-only Python, seeded, so anyone can
re-run it and get the same file byte for byte:

- ECB Survey of Professional Forecasters, individual responses → data.ecb.europa.eu
- Script → github.com/namikakmandev/namikakmandev.github.io/blob/main/scripts/ecb_forecaster_skill.py

Companion study, the panel scored as a whole (their 80% ranges hold 53% of the
time): namikakmandev.github.io/ecb-forecasts.html

---

## If someone challenges it

**"Isn't the wide-range forecaster just cheating?"** Half right, and it's in the
post. Width explains 47%. The rest survives three cuts: split the panel at the
median width and the spread is still 10.7pp among the narrow ones; strip width
out of the persistence test and r = 0.28 holds at p = 0.037; drop every forecast
touching an open-ended bucket and the correlation doesn't move (0.691 vs 0.689).
Marginal, and the page says so.

**"Which bank is #016?"** Nobody outside the ECB knows, and I'm not guessing.
The numbers are stable identities, which is what makes a 26-year record possible
without ever knowing whose it is.

**"Ten years is a short record."** Agreed. Only 15 of the 64 sit outside the
luck band; the other 49 are individually indistinguishable from average. The
panel-level spread is solid, any single row is not. That's on the page too.

**"This is hindsight."** Every forecast is scored against what an average
forecaster facing *that forecaster's own years* would have managed — nobody gets
credit for sitting out 2008.
