# Inflation paid the debt — LinkedIn assets

Part two of the bond study. Part one (`bonds.html`, "Five per cent") was about
the yields; this post is about the debt, so it should not repeat the yield
charts or the US interest bill.

## What to upload

**One file: `notes/debt-carousel.pdf`.** Post it as a LinkedIn document, with
the copy below as the body.

Seven portrait slides, 4:5, same page size as the other carousels here:

1. The hook: every debt ratio fell or held, and every one rises once inflation is taken out.
2. The five forces, 2021–25: budgets added, inflation subtracted.
3. The same split, 2026–31 (IMF): interest is the biggest force in 6 of 9.
4. Interest as a share of revenue, 1990–2031: the US at 11.8%, Italy's 1993 peak for scale.
5. How fast yields reach the debt: 5-year half-life, and who crosses r > g by 2031.
6. The budget gap at today's yields: US 4.6 points of GDP, Italy 0.1, Spain covered.
7. Three things to say and one not to, with the link and sources.

LinkedIn does not take HTML as a document. The deck is also on the site as
`notes/debt-carousel.html`, for the comments:
namikakmandev.github.io/notes/debt-carousel.html

Standalone images if you would rather post images than a document, all in
`assets/linkedin/`: `debt-without-inflation.png` (the hook, the best single
image), `debt-forces-2021-25.png`, `debt-forces-2026-31.png`,
`debt-interest-revenue.png`, `debt-rates-2031.png`, `debt-budget-gap.png`.

Rebuild everything with:

```
python3 scripts/debt_study.py
python3 scripts/debt_carousel.py --proof
```

Every number on the slides is read from `data/debt-study.json`. The copy
below is typed, so re-check it against the slides after a new IMF release
(the October WEO will move all of it).

**One link in the body:** `namikakmandev.github.io/debt.html`

---

## Before posting

- [ ] **Say "inflation", not "inflation paid it off".** Debt was not repaid.
      The ratio fell because GDP, the denominator, rose faster. The nominal
      debt went up everywhere.
- [ ] **"Primary deficit over 2021–25 as a whole".** Italy ran primary
      surpluses in 2024 and 2025. "Nobody ran a surplus" is wrong. "All nine ran
      deficits over the five years taken together" is right.
- [ ] **The "r > g by 2031" line is arithmetic, not a forecast.** It holds
      today's ten-year yield for six years and uses the historical repricing
      speed. Say "if yields stay where they are".
- [ ] **The 5-year half-life is an estimate.** It is 13% a year (s.e. 2.3
      points) on 233 country-years. An IV check gives 17%, which is faster, so five
      years is the slow end. Do not quote it as a fact about any one country.
- [ ] **Net interest.** Japan's, Australia's and the Netherlands' numbers are
      net of large asset income. Canada and Korea are out because theirs is
      negative. If someone quotes Japan's gross interest bill, they are right
      that it is bigger.
- [ ] **US revenue share**: 11.8% is general government (federal + state +
      local), net interest over total revenue, IMF definitions. Federal-only
      figures quoted in the US press are higher. Do not mix them.
- [ ] Open the link on your phone once before posting.

---

## English

The deck does the explaining. The body only has to hook and hand off.

📉 After the pandemic, rich-world debt ratios fell. Japan's by 22 points of GDP, Italy's by 17, Spain's by 19.

🧾 Nobody paid it down. Across nine economies, all ran primary deficits over 2021–25 taken together.

🔥 Inflation did it. It took 11 to 25 points of GDP off every one of the nine debt ratios. Take the inflation term out and every ratio would have risen: the US by 16 points, Britain by 17.

📈 That help is fading. On the IMF's own projections, interest becomes the biggest force pushing debt up in 6 of the 9 by 2031, ahead of the budget deficit.

🇺🇸 The US already spends 11.8% of its government revenue on net interest. That is twice its 2015 share, and it reaches 14% by 2031 on the IMF's path.

⏳ The part that gets less attention: how fast a higher bond yield reaches the interest bill. Thirty years of data put the half-life at about 5 years.

⚠️ At that speed, if yields stay where they are, the US, Britain, France and Italy pay more on their debt than their economies grow by 2031. The IMF's path has only Italy there.

🧮 To hold its debt ratio steady at today's yields, the US would need a budget 4.6 points of GDP tighter than the IMF projects. Italy needs 0.1.

This is part two of my bond-yield study. The IMF data, the method and the scripts are all open:
🔗 namikakmandev.github.io/debt.html

---

## Türkçe

📉 Pandemiden sonra zengin ülkelerin borç oranları düştü. Japonya'nınki GSYH'nin 22 puanı, İtalya'nınki 17, İspanya'nınki 19 puan.

🧾 Kimse borcu ödemedi. Dokuz ekonominin hepsi 2021–25 toplamında faiz dışı açık verdi.

🔥 Bunu enflasyon yaptı. Dokuz ülkenin her birinin borç oranından GSYH'nin 11 ila 25 puanını sildi. Enflasyonu çıkarın, dokuzunun da oranı artardı: ABD'ninki 16 puan, İngiltere'ninki 17.

📈 Bu destek zayıflıyor. IMF'nin kendi projeksiyonlarına göre 2031'e kadar dokuz ülkenin altısında borcu en çok artıran kalem faiz oluyor. Bütçe açığını geride bırakıyor.

🇺🇸 ABD şimdiden kamu gelirinin %11,8'ini net faize harcıyor. Bu, 2015'teki payının iki katı. IMF patikasında 2031'de %14'e çıkıyor.

⏳ Daha az konuşulan kısım şu: yükselen tahvil faizi faiz faturasına ne hızla yansıyor? Otuz yıllık veri yarı ömrü yaklaşık 5 yıl olarak veriyor.

⚠️ Bu hızla, faizler bugünkü seviyede kalırsa ABD, İngiltere, Fransa ve İtalya 2031'de borçlarına ekonomilerinin büyümesinden fazla faiz ödüyor olacak. IMF'nin patikasında yalnızca İtalya bu durumda.

🧮 Bugünkü faizlerle borç oranını sabit tutmak için ABD'nin bütçesinin IMF projeksiyonundan GSYH'nin 4,6 puanı kadar sıkı olması gerekir. İtalya'nın 0,1 puan.

Tahvil faizi çalışmamın ikinci bölümü. IMF verisi, yöntem ve kodlar açık:
🔗 namikakmandev.github.io/debt.html

---

## Pinned comment

The data is public and the scripts are stdlib Python, so anyone can re-run this:

- IMF World Economic Outlook, via the IMF Data API: gross debt, overall and primary balance, revenue, nominal and real GDP
- OECD ten-year government bond yields via FRED (IRLTLT01..M156N; GS10 for the US)
- Scripts: github.com/namikakmandev/namikakmandev.github.io/tree/main/scripts (`debt_study.py`, `debt_carousel.py`)
- Part one, the yields: namikakmandev.github.io/bonds.html
- The deck as a web page: namikakmandev.github.io/notes/debt-carousel.html

Net interest = primary balance − overall balance. The split of each debt ratio is the standard identity: primary deficit + interest − real growth − inflation + residual. The residual is printed for every country.

---

## If someone challenges it

**"Inflation reducing debt ratios is textbook."** Yes. The post doesn't
claim it's new. It measures how much inflation did, country by country, and
shows that the help shrinks from here. The new number is the repricing speed.

**"The IMF assumes yields fall."** Possibly. The WEO does not publish its
rate path in this dataset. The post says "if yields stay where they are" and
shows both paths side by side. If the October WEO raises the rate on the
debt, the gap closes, and the fetch picks the new release up automatically.

**"Maturity has lengthened, so repricing is slower now."** A fair point, and
it's on the page. The estimate is 1996–2025, so it averages across shorter
and longer maturities. A slower speed pushes the crossing later. It doesn't
remove it, because the market rate is already above the IMF's 2031 growth in
all nine.

**"Japan's interest bill is far bigger than 0.2% of GDP."** On a gross basis,
yes. This is net interest, and Japan's government earns large income on
its assets. That is why Japan is kept out of the pooled speed estimate and
flagged on every chart.

**"Gross debt is the wrong measure."** It is the measure the IMF, the EU
rules and the press use, and it's what the bonds are issued against. Net debt
is in the imf-weo file (GGXWDN_NGDP), but the page does not use it because
several countries' net figures are small or break definitionally. That
point is on the page, not hidden.

**"Why is Spain fine?"** On the IMF's numbers, Spain's nominal growth is 4.1%
in 2031 and it runs a small primary surplus. That combination covers today's
3.6% ten-year yield. It is the only one of the nine where it does.
