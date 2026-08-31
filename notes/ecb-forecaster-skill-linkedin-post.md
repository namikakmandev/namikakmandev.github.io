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

I work in pricing. Every plan I build sits on an inflation forecast.

So it is worth knowing where that forecast comes from. Each quarter the ECB
surveys around fifty banks and research institutes across Europe. It asks each
one not for a number but for a probability distribution: where will inflation
land, and how confident are you. Those answers become the consensus figure most
of us quote.

In 2022 euro-area inflation reached 8.4%, the highest in the euro's history.
None of the fifty had it inside the range they had published.

The ECB publishes each forecaster separately, so I scored all 26 years.

[ image 2 &mdash; the grid ]

Green: the outcome landed inside that forecaster's range. Red: it did not.

Four columns are entirely red: 2008, 2021, 2022 and 2023. In those years the
stated confidence carried no information.

[ image 3 &mdash; best vs worst ]

The forecasters are not interchangeable. But the best also publishes ranges
twice as wide as the worst, and width alone explains 47% of the score. Roughly
half of what looks like skill is a willingness to admit uncertainty.

Useful, but not the same as accuracy.

The practical point: score a forecast on two measures, not one. How often the
outcome fell inside the stated range, and how wide that range had to be.

Only 1 of 64 met their own 80% standard.

Method and code: namikakmandev.github.io/ecb-forecaster-skill.html
Data: @European Central Bank Survey of Professional Forecasters.

---

## Türkçe

Fiyatlama alanında çalışıyorum. Kurduğum her plan bir enflasyon tahmininin
üzerine oturuyor.

Bu yüzden o tahminin nereden geldiğini bilmekte fayda var. ECB her çeyrek
Avrupa'da elli kadar banka ve araştırma kurumuna anket yapıyor. Her birinden tek
bir sayı değil, bir olasılık dağılımı istiyor: enflasyon nereye gelir, ve ne
kadar eminsiniz. Bu cevaplar çoğumuzun alıntıladığı konsensüs rakamına
dönüşüyor.

2022'de euro bölgesi enflasyonu %8,4'e ulaştı; euronun tarihindeki en yüksek
seviye. Elli tahmincinin hiçbirinde bu, yayımladıkları aralığın içinde değildi.

ECB her tahminciyi ayrı ayrı da yayımlıyor, ben de 26 yılın tamamını puanladım.

[ görsel 2 &mdash; ızgara ]

Yeşil: sonuç o tahmincinin aralığının içine düştü. Kırmızı: düşmedi.

Dört sütun tamamen kırmızı: 2008, 2021, 2022 ve 2023. Bu yıllarda beyan edilen
güven aralığı hiçbir bilgi taşımıyordu.

[ görsel 3 &mdash; en iyi ve en kötü ]

Tahminciler birbirinin yerine geçmiyor. Ama en iyisi aynı zamanda en kötünün iki
katı geniş aralıklar yayımlıyor ve skorun %47'sini tek başına genişlik
açıklıyor. Yetenek gibi görünen şeyin kabaca yarısı, belirsizliği kabul etme
isteği.

Değerli, ama isabet ile aynı şey değil.

Pratik sonuç: bir tahmini tek ölçüyle değil iki ölçüyle puanlayın. Sonuç kaç kez
beyan edilen aralığın içinde kaldı, ve o aralık ne kadar geniş olmak zorunda
kaldı.

64 tahminciden yalnızca 1'i kendi %80 standardını tutturdu.

Yöntem ve kod: namikakmandev.github.io/ecb-forecaster-skill.html
Veri: @European Central Bank Survey of Professional Forecasters.

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
