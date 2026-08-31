# Forecaster skill — LinkedIn assets

**Format: two images + short text + one link.** Nothing else.

| | |
|---|---|
| Image 1 | `assets/linkedin/ecb-forecaster-skill.png` — the 64 × 26 grid |
| Image 2 | `assets/linkedin/ecb-forecaster-ranges.png` — best vs worst, year by year |
| Link | `namikakmandev.github.io/ecb-forecaster-skill.html` |
| Regenerate | `python3 scripts/ecb_forecaster_skill.py` |

Every number: 64 forecasters with 10+ scored years, 1,184 one-year-ahead
forecasts, euro-area inflation 2000–2025.

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

[ image 1 ]

Green = inflation landed inside the range that forecaster published.
Red = it didn't.

**Down the columns:** 2008, then 2021, 2022 and 2023. Not one forecaster on the
panel was inside their own range. Four years where everybody missed together.

**Across the rows:** they are not interchangeable. Best to worst is 57
percentage points — far too wide to be luck.

[ image 2 ]

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

[ görsel 1 ]

Yeşil = enflasyon o tahmincinin kendi açıkladığı aralığın içine düştü.
Kırmızı = düşmedi.

**Sütunlara bakın:** 2008, sonra 2021, 2022 ve 2023. Paneldeki tek bir tahminci
bile kendi aralığının içinde değil. Herkesin birlikte ıskaladığı dört yıl.

**Satırlara bakın:** hepsi aynı değil. En iyi ile en kötü arasında 57 puan fark
var — şansla açıklanamayacak kadar büyük.

[ görsel 2 ]

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
