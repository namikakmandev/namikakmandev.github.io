# The 11% rule — LinkedIn assets

## What to upload

**One file: `notes/price-leverage-carousel.pdf`.** Post it as a LinkedIn document,
with the copy below as the body.

Six portrait slides, 4:5, same page size as the other carousels here. One idea
each: the hook on the regions chart, the famous number and why it is arithmetic,
the arithmetic worked on three margins, the year-by-year chart, the two numbers,
the two instructions. Slide 1 is the
feed thumbnail. Rebuild with `python3 scripts/price_leverage_carousel.py`.

Standalone images if you would rather post images than a document:
`assets/linkedin/price-leverage-regions.png` (by region) and
`assets/linkedin/price-leverage-series.png` (by year).

**One link in the body:** `namikakmandev.github.io/price-leverage.html`

---

## Before posting

- [ ] The claim under test is Marn & Rosiello, "Managing Price, Gaining Profit",
      *Harvard Business Review*, September–October 1992. Name it if challenged.
      It is a good article and this is not a takedown: the number was right
      for its sample.
- [ ] **Do not say the article was wrong.** Its sample is not published, so it
      cannot be re-measured. The finding is that the identity gives a different
      number today, and a different one in every region.
- [ ] **Do not say "the US left the rule".** No edition ever shows the US on it;
      the consistent series starts in 2014. Say "is not on it".
- [ ] **Say "operating margin", not "margin".** Gross margin gives a different
      and much smaller number, and someone will compute it.
- [ ] The catch belongs in the post: volume is held constant. The identity is
      the upper bound, which is exactly how the 1992 figure is quoted.

---

## English

The deck does the explaining. The body only has to hook and hand off.

📊 Every pricing deck has the line: a 1% price improvement = 11.1% more
operating profit. I&rsquo;ve put it on slides myself.

🗓️ It comes from Harvard Business Review, 1992. And it isn&rsquo;t a finding,
it&rsquo;s arithmetic: one over the operating margin. 11.1 is what a 9% margin
gives. It describes one sample of companies, 34 years ago.

🔁 So I recomputed it on Damodaran&rsquo;s industry tables. Eight regions, every
archived year.

🇺🇸 US today: 7.8%. Below 11 in every edition since 2014. Europe 8.6%.

🌍 Emerging markets: 11.0%. Within 1.1 points of the rule every year since 2012.

🇯🇵 Japan 13.1%. 🇨🇳 China 15.7%.

💊 Inside the US it runs from pharma at 3.4% to grocery retail at
44%. Same arithmetic, different margin:

Grocer: revenue 100, costs 97.7, operating profit 2.29. Price +1%, same
volume: revenue 101, costs 97.7, profit 3.29. That is +44%.
Pharma: revenue 100, costs 70.5, profit 29.5. Price +1%: profit 30.5.
That is +3.4%.

Everyone gains the same one point of margin. Thin margin, huge leverage.

✅ Stop quoting 11.1. Put 1 &divide; your operating margin in the deck. In emerging
markets the old number still works. In the US and Europe it flatters the price
lever.

🔗 namikakmandev.github.io/price-leverage.html

---

## Türkçe

📊 Her fiyatlandırma sunumunda o cümle var: fiyatta %1 iyileşme = faaliyet
kârında %11,1 artış. Ben de slaytlara koydum.

🗓️ Kaynağı Harvard Business Review, 1992. Ve bir bulgu değil, aritmetik:
faaliyet kâr marjının tersi. %9 marj, 11,1 verir. Yani 34 yıl önceki bir
şirket örneklemini anlatıyor.

🔁 Damodaran&rsquo;ın sektör tablolarıyla yeniden hesapladım. Sekiz bölge,
arşivdeki her yıl.

🇺🇸 ABD bugün: %7.8. 2014&rsquo;ten beri her yayında 11&rsquo;in altında. Avrupa %8.6.

🌍 Gelişmekte olan piyasalar: %11.0. 2012&rsquo;den beri her yıl kuralın 1.1 puan yakınında.

🇯🇵 Japonya %13.1. 🇨🇳 Çin %15.7.

💊 ABD içinde ilaçta %3.4&rsquo;ten gıda perakendesinde %44&rsquo;e
kadar. Aynı aritmetik, farklı marj:

Market: ciro 100, maliyet 97.7, faaliyet kârı 2.29. Fiyat +%1, aynı hacim:
ciro 101, maliyet 97.7, kâr 3.29. Yani +%44.
İlaç: ciro 100, maliyet 70.5, kâr 29.5. Fiyat +%1: kâr 30.5. Yani +%3.4.

Herkes aynı bir puan marjı kazanıyor. İnce marj, büyük kaldıraç.

✅ 11,1&rsquo;i alıntılamayı bırakın. Sunuma 1 &divide; kendi faaliyet kâr
marjınızı yazın. Gelişmekte olan piyasalarda eski sayı hâlâ işe yarıyor. ABD ve
Avrupa&rsquo;da fiyat kaldıracını olduğundan büyük gösteriyor.

🔗 namikakmandev.github.io/price-leverage.html

---

## Pinned comment

The data is open and the analysis is stdlib Python, so anyone can re-run this:

- Damodaran, NYU Stern, industry margin tables (margin.xls and the regional and
  archived files) → pages.stern.nyu.edu/~adamodar
- Scripts → github.com/namikakmandev/namikakmandev.github.io/tree/main/scripts

Price leverage = 1 / operating margin, revenue-weighted "Total Market" row of
each file, volume held constant. The article's other three levers (variable
cost, volume, fixed cost) need a cost split public accounts do not give, so
only the price lever is retested.

---

## If someone challenges it

**"This is obvious, it's just 1/margin."** Yes, and that is the point. The deck
quotes 11.1 as a constant. It is a formula, and the formula gives 7.8 for the
US aggregate, 3.4 for pharma and 44 for grocery retail.

**"Revenue-weighted aggregates are dominated by giants."** The median industry is
within 2.1 points of the aggregate in every region, and the same three regions
lead by either measure. Both are on the page.

**"Volume never holds constant."** Agreed. The identity is the upper bound,
which is exactly how the 1992 figure has always been quoted. The elasticity is
the whole job, and this number is where it starts.

**"You can't compare to a 1992 sample you don't have."** Correct, and the post
does not say the 1992 figure was wrong. It says the identity gives a different
number today, and a different one in every region.

**"What about the years before 2014 in the US?"** Damodaran's earlier US files
use another layout and column, and the level steps at the switch. They are kept
as a separate regime on the page; every one of them is also below 11.1.

**"Gross margin gives a different answer."** It does, and it is the wrong margin.
The article's lever is operating profit, so the divisor is the operating margin.
