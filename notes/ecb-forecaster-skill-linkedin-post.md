# Forecaster skill — LinkedIn assets

## What to upload

Two ways to post this. Pick one.

### A. Document post (carousel) &mdash; recommended

Upload **one file**: `notes/ecb-forecaster-carousel.pdf`

Seven portrait slides, 4:5, the same page size as the earlier carousels in this
folder. LinkedIn renders a document larger than a feed image and lets people
swipe and zoom, which is what the 64&times;26 grid needs. Rebuild with
`python3 scripts/ecb_carousel.py`.

### B. Three images

| # | File | Size |
|---|---|---|
| 1 | `assets/linkedin/ecb-forecaster-hero.png` | 1600&times;1600 |
| 2 | `assets/linkedin/ecb-forecaster-skill.png` | 1600&times;1314 |
| 3 | `assets/linkedin/ecb-forecaster-ranges.png` | 1600&times;1188 |

In that order. Image 1 is the one that has to work without a tap.

**Either way, one link in the body:**
`namikakmandev.github.io/ecb-forecaster-skill.html`

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

📊 I work in pricing. Every plan I build rests on an inflation forecast.

So it matters who makes them.

Every quarter the ECB asks about 50 banks and research institutes across Europe
the same question. Not just &ldquo;what will inflation be&rdquo; &mdash; but
&ldquo;give us a range you are 80% sure about.&rdquo;

That is a promise you can check. If you say you are 80% sure, then over 20 years
the answer should land inside your range about 16 times.

⚠️ In 2022 inflation came in at 8.4%. Of the 58 who answered that round,
not one had it inside their range.

So I went back and scored all 26 years, one forecaster at a time.

[ image 2 &mdash; the grid ]

🟩 Green: inflation landed inside that forecaster's range.
🟥 Red: it did not.

Four whole columns are red: 2008, 2021, 2022 and 2023. In those years nobody on
the panel was inside their own range.

⬇️ And they were all wrong the same way. Every single one was <b>short</b>. 178
forecasts across those four years, 178 underestimates, zero overestimates.

When this panel fails completely, it does not see costs coming.

Then I found the catch.

[ image 3 &mdash; best vs worst ]

🤔 A range can be right just by being huge.

If your supplier says &ldquo;costs will rise between 0% and 10%&rdquo;, they will
almost always be right. And they have told you nothing you can price on.

That is what separates the best forecaster here from the worst. The best one's
ranges are 2.5&times; wider. Width alone explains 47% of the gap between them.
So about half of being good at this is just being vague.

✅ Which means you should score a forecast twice, not once:

1. How often was the answer inside the range?
2. How wide did the range have to be?

The first number can be bought. Only the second tells you whether they actually
know something.

And then the last number.

📉 1 of 64 forecasters hit their own 80% standard.

Not my standard. Theirs. They said 80%, and 63 of 64 delivered less.

So: everyone's ranges are too tight &mdash; and the ones who look best are
mostly just the least tight.

🔗 namikakmandev.github.io/ecb-forecaster-skill.html
Data: @European Central Bank Survey of Professional Forecasters.

---

## Türkçe

📊 Fiyatlama yapıyorum. Kurduğum her plan bir enflasyon tahminine
dayanıyor.

O yüzden bu tahminleri kimin yaptığı önemli.

ECB her çeyrek Avrupa'daki 50 kadar bankaya ve araştırma kurumuna aynı soruyu
soruyor. Sadece &ldquo;enflasyon ne olacak&rdquo; değil &mdash; &ldquo;%80 emin
olduğunuz bir aralık verin.&rdquo;

Bu, kontrol edilebilir bir söz. %80 eminseniz, 20 yılda cevabın aralığınızın
içine yaklaşık 16 kez düşmesi gerekir.

⚠️ 2022'de enflasyon %8,4 geldi. O turda cevap veren 58 tahmincinin
hiçbirinde bu, kendi aralığının içinde değildi.

Ben de 26 yılın hepsini, tahminci tahminci puanladım.

[ görsel 2 &mdash; ızgara ]

🟩 Yeşil: enflasyon o tahmincinin aralığının içine düştü.
🟥 Kırmızı: düşmedi.

Dört sütun tamamen kırmızı: 2008, 2021, 2022 ve 2023. O yıllarda panelde kendi
aralığının içinde kalan tek bir kişi yok.

⬇️ Ve hepsi aynı yönde yanıldı. Hepsi <b>düşük</b> tahmin etti. O dört yılda 178
tahmin, 178 eksik tahmin, sıfır fazla tahmin.

Bu panel tamamen şaşırdığında, maliyetlerin geldiğini göremiyor.

Sonra işin püf noktasını buldum.

[ görsel 3 &mdash; en iyi ve en kötü ]

🤔 Bir aralık, sırf çok geniş olduğu için de doğru çıkabilir.

Tedarikçiniz &ldquo;maliyetler %0 ile %10 arasında artacak&rdquo; derse
neredeyse her zaman haklı çıkar. Ve size fiyat kurabileceğiniz hiçbir şey
söylememiştir.

Buradaki en iyi tahminciyi en kötüden ayıran şey de bu. En iyinin aralıkları 2,5
kat daha geniş. Aradaki farkın %47'sini tek başına genişlik açıklıyor. Yani bu
işte iyi olmanın yarısı, muğlak kalmak.

✅ Bu da şu demek: bir tahmini bir değil, iki kez puanlayın.

1. Cevap kaç kez aralığın içinde kaldı?
2. Aralık bunun için ne kadar geniş olmak zorunda kaldı?

Birinci sayı satın alınabilir. Gerçekten bir şey bilip bilmediklerini size
yalnızca ikincisi söyler.

Ve son sayı.

📉 64 tahminciden 1'i kendi %80 standardını tutturdu.

Benim standardım değil. Kendilerininki. %80 dediler, 64'ün 63'ü daha azını
verdi.

Yani: herkesin aralıkları fazla dar &mdash; ve en iyi görünenler de aslında
sadece en az dar olanlar.

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
