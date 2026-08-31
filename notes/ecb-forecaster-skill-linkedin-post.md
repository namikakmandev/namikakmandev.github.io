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

The ECB asks about fifty banks and research houses the same question every
quarter, then averages the answers into the number everybody quotes.

It also publishes the fifty answers separately.

So I followed each one — anonymously, they're only numbers — for 26 years.

[ image 2 &mdash; the grid ]

Green = inflation landed inside the range that forecaster published.
Red = it didn't.

**Down the columns:** 2008, then 2021, 2022 and 2023. Not one forecaster on the
panel was inside their own range. Four years where everybody missed together.

**Across the rows:** they are not interchangeable. Best to worst is 57
percentage points — far too wide to be luck.

[ image 3 &mdash; best vs worst ]

Here's the part I nearly got wrong.

The best forecaster publishes ranges twice as wide as the worst. Width alone
explains 47% of the score. Take it out and the "skill" drops from r = 0.46 to
r = 0.28.

So half of being right is just a habit of admitting you don't know.

Still a habit worth copying. It just isn't foresight.

**What I'd do with it:** if you buy a forecast from anyone — a broker, an
analyst, a supplier's demand plan — score them on two columns, not one. How
often were they inside their range, and how wide did the range have to be.
Only the second one tells you whether they know anything.

1 of 64 ever cleared their own 80% bar.

Method, every number and the full script → namikakmandev.github.io/ecb-forecaster-skill.html
Data: @European Central Bank Survey of Professional Forecasters, published openly.

---

## Türkçe

Avrupa Merkez Bankası her çeyrek elli kadar bankaya aynı soruyu soruyor, sonra
cevapların ortalamasını alıyor. Herkesin alıntıladığı sayı o ortalama.

Ama elli cevabı ayrı ayrı da yayımlıyor.

Ben de her birini — isimsiz, sadece numaralar — 26 yıl boyunca takip ettim.

[ görsel 2 &mdash; ızgara ]

Yeşil = enflasyon o tahmincinin kendi açıkladığı aralığın içine düştü.
Kırmızı = düşmedi.

**Sütunlara bakın:** 2008, sonra 2021, 2022 ve 2023. Paneldeki tek bir tahminci
bile kendi aralığının içinde değil. Herkesin birlikte ıskaladığı dört yıl.

**Satırlara bakın:** hepsi aynı değil. En iyi ile en kötü arasında 57 puan fark
var — şansla açıklanamayacak kadar büyük.

[ görsel 3 &mdash; en iyi ve en kötü ]

Ve neredeyse yanlış anlatacağım kısım.

En iyi tahmincinin aralıkları en kötününkinin iki katı geniş. Skorun %47'sini
tek başına genişlik açıklıyor. Onu çıkarınca "yetenek" r = 0,46'dan r = 0,28'e
düşüyor.

Yani haklı çıkmanın yarısı, bilmediğini kabul etme alışkanlığı.

Yine de kopyalanmaya değer bir alışkanlık. Sadece öngörü değil.

**Ne yapmalı:** birinden tahmin alıyorsanız — aracı kurum, analist, tedarikçinin
talep planı — tek sütunla değil iki sütunla puanlayın. Kaç kez aralığın içinde
kaldılar, ve aralık bunun için ne kadar geniş olmak zorunda kaldı. Bir şey bilip
bilmediklerini size ikincisi söyler.

64 tahminciden yalnızca 1'i kendi %80 çıtasını tutturdu.

Yöntem, bütün sayılar ve kodun tamamı → namikakmandev.github.io/ecb-forecaster-skill.html
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
