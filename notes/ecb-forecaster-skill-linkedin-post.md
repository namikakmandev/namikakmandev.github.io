# Forecaster skill — LinkedIn assets

## What to upload

**One file: `notes/ecb-forecaster-carousel.pdf`.** Post it as a LinkedIn
document, with the copy below as the body.

Six portrait slides, 4:5, same page size as the earlier carousels in this
folder. Slide 1 is the grid, so the grid is also the thumbnail in the feed &mdash;
it carries a headline of its own for that reason. Rebuild with
`python3 scripts/ecb_carousel.py`.

The copy below has no image cues in it. The deck carries the visuals; the text
stands on its own underneath.

**Three standalone images** are still built if you would rather post images than
a document: `assets/linkedin/ecb-forecaster-hero.png` (square, the one that has
to work without a tap), then `-skill.png` (the grid), then `-ranges.png`.

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

The deck carries the explanation. The body only has to hook and hand off.

📊 I work in pricing. Every plan I build rests on an inflation forecast.

⚠️ In 2022 inflation came in at 8.4%. Of the 58 ECB forecasters who
answered that round, not one had it inside their own range.

So I scored all 26 years, one at a time.

🟥 Four years are solid red: 2008, 2021, 2022, 2023. Nobody was inside
their range.

⬇️ And all of them were short. 178 forecasts, 178 underestimates, zero
overestimates.

🤔 But the catch: &ldquo;costs will rise 0&ndash;10%&rdquo; is almost
never wrong and almost never useful. The best forecaster's ranges are
2.5&times; wider than the worst's.

✅ So score a forecast twice: how often it was right, and how wide it had
to be.

1 of 64 hit their own 80% standard.

🔗 namikakmandev.github.io/ecb-forecaster-skill.html
Data: @European Central Bank Survey of Professional Forecasters.

---

## Türkçe

📊 Fiyatlama yapıyorum. Kurduğum her plan bir enflasyon tahminine
dayanıyor.

⚠️ 2022'de enflasyon %8,4 geldi. O turda cevap veren 58 ECB tahmincisinin
hiçbirinde bu, kendi aralığının içinde değildi.

26 yılın hepsini tek tek puanladım.

🟥 Dört yıl tamamen kırmızı: 2008, 2021, 2022, 2023. Kimse kendi
aralığının içinde değil.

⬇️ Ve hepsi düşük tahmin etti. 178 tahmin, 178 eksik, sıfır fazla.

🤔 Ama işin püf noktası: &ldquo;maliyetler %0&ndash;10 artacak&rdquo;
demek neredeyse hiç yanlış çıkmaz ve neredeyse hiç işe yaramaz. En iyi
tahmincinin aralıkları en kötününkinin 2,5 katı geniş.

✅ O yüzden bir tahmini iki kez puanlayın: kaç kez doğru çıktı, ve ne kadar
geniş olmak zorunda kaldı.

64 tahminciden 1'i kendi %80 standardını tutturdu.

🔗 namikakmandev.github.io/ecb-forecaster-skill.html
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
