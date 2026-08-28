# The 4% rule, replicated — LinkedIn assets

**Chosen format: text post + the one chart image + one link.** The image is
`assets/linkedin/four-percent-rule.png` (regenerate with
`python3 scripts/retire_chart.py`). The link is the receipts page, which carries
the replication table, the retest, the sensitivity tables, limitations, and all
three scripts verbatim:

- `namikakmandev.github.io/four-percent-rule.html` — receipts page (the link in the post)
- `github.com/datasets/s-and-p-500` — the open mirror of Shiller's data (pinned comment)

Every number comes from `scripts/retire_4pct.py` (stdlib-only, deterministic):
replication 92.7% (50/50) and 95.1% (75/25) against published 95% and 98%;
a 0.5% credit spread reproduces the first, 1.5% reproduces both; SAFEMAX 3.60%
on government bonds, unchanged across 1926–1995, 1926–2022 and 1871–2022;
3.91% if you withdraw at year end instead; 3.18% after a 1% fee; all six
failures in 152 years began 1964–1969; 68 overlapping windows contain 3
non-overlapping ones; of 62 successes, 29 ended poorer in real terms than they
started.

---

## Before posting

- [ ] Check your employer's external communications policy.
- [ ] **This one is personal finance. The not-advice line is not optional** —
      keep it in the post body, not only on the page. Do not let the comments
      turn into "so what should I withdraw?" (template below).
- [ ] Rewrite the copy in your own words if anything feels off.
- [ ] Attach the chart image; open the receipts link on your phone once.
- [ ] **Tagging.** This is a replication of named living authors' work, which is
      a different tagging situation from the Big Mac and 538 posts. Options, in
      order of sense: **William Bengen** (author of the 1994 paper, still active
      and still writing on this), and **Wade Pfau**, who is the most active
      public researcher on safe withdrawal rates and whose summary is the source
      for the published Trinity figures I replicate against. Verify each account
      exists on LinkedIn and is active before tagging. The Trinity authors
      (Cooley, Hubbard, Walz) are Trinity University academics and may not have
      active accounts — credit them by name in the body regardless, which the
      copy does.
- [ ] Framing is replication, not debunking. The papers hold up. The finding is
      about what the rule quietly assumes, not about the authors being wrong.
      Keep that tone in replies — an author reading this should recognise it as
      fair.
- [ ] Do not imply you tested the rule outside the US. You did not; the page
      cites Pfau and Estrada for that and says explicitly it is cited, not
      reproduced.

---

## Post copy — English

The most quoted number in personal finance is the 4% rule: draw 4% of your
savings in year one, raise it with inflation, and 30 years of history says you
will not run out.

It comes from two real papers — Bengen (1994) and the Trinity Study (Cooley,
Hubbard & Walz, 1998). Both are honest, careful pieces of work. So I re-ran
them, line by line, on Robert Shiller's open data, 1871 to 2022.

Four things came out:

📉 It replicates. The Trinity Study published a 95% success rate for a 50/50
portfolio. I get 93%. That is one retirement out of 41 — close, but not exact,
and the gap turned out to be interesting.

📉 The gap is credit risk. They held long-term CORPORATE bonds. The only public
series is government bonds. Add the missing credit spread back — half a point —
and their number reproduces exactly. So the famous 95% is real, with a condition
nobody attaches when they quote it: you have to hold corporate credit for thirty
years, and keep holding it through every recession in them.

📉 On government bonds, the number isn't 4%. The highest rate that never failed
is 3.60%. And here is the uncomfortable part: whether you take the withdrawal at
the start of the year or the end — a pure modelling choice, nothing to do with
markets — moves that from 3.60% to 3.91%. A 1% annual fee moves it to 3.18%. The
spread between those numbers is not economics. It's spreadsheet convention and
what you pay your fund manager.

📉 The whole rule rests on six retirements. In 152 years, every single failure
began between 1964 and 1969 — high valuations, then the 1970s. And "68
historical periods" sounds like 68 tests, but consecutive 30-year windows share
29 of their 30 years. There are three genuinely non-overlapping ones. The rule
is not backed by a century of independent evidence. It's backed by about three
retirements, one of which went badly.

One more thing the rule doesn't say. "Success" means the portfolio didn't hit
zero. It does not mean it held its value. Of the 62 retirements that succeeded,
29 ended with less real money than they started with — one finished with a
quarter of it, another with five times. All of them count as a success.

None of this makes the papers wrong. They said what they said, carefully, and it
holds up. It's the folklore that dropped the conditions.

Every number, the method, seven limitations I could not resolve, and the code:
→ namikakmandev.github.io/four-percent-rule.html

Not financial advice — this is a replication of two papers about what happened
in the past, in one country, to a mechanical rule. A historical success rate is
not a probability that applies to your retirement.

---

## Post copy — Türkçe

Kişisel finansta en çok alıntılanan sayı %4 kuralı: birikiminizin ilk yıl
%4'ünü çekin, her yıl enflasyon kadar artırın, ve 30 yıllık tarih diyor ki
paranız bitmez.

Bu kural iki gerçek makaleden geliyor — Bengen (1994) ve Trinity Çalışması
(Cooley, Hubbard & Walz, 1998). İkisi de dürüst, özenli işler. Ben de ikisini
satır satır yeniden çalıştırdım: Robert Shiller'ın açık verisi, 1871–2022.

Dört sonuç çıktı:

📉 Replike oluyor. Trinity Çalışması 50/50 portföy için %95 başarı oranı
yayımlamıştı. Ben %93 buluyorum. 41 emeklilikten biri fark — yakın ama birebir
değil, ve farkın sebebi ilginç çıktı.

📉 Fark, kredi riski. Onlar uzun vadeli ŞİRKET tahvili tutuyorlardı. Açık olan
tek seri devlet tahvili. Eksik kredi marjını geri ekleyin — yarım puan — ve
sayıları birebir çıkıyor. Yani meşhur %95 gerçek, ama kimsenin alıntılarken
eklemediği bir şartla: otuz yıl boyunca şirket kredi riski taşıyacaksınız, ve
aradaki her resesyonda taşımaya devam edeceksiniz.

📉 Devlet tahviliyle sayı %4 değil. Hiç batmayan en yüksek oran %3,60. Ve rahatsız
edici kısmı şu: parayı yılın başında mı yoksa sonunda mı çektiğiniz — piyasayla
hiç ilgisi olmayan, tamamen modelleme tercihi — bu sayıyı %3,60'tan %3,91'e
taşıyor. Yıllık %1 komisyon %3,18'e indiriyor. Bu sayılar arasındaki fark
ekonomi değil. Excel kuralı ve fon yöneticinize ödediğiniz ücret.

📉 Bütün kural altı emekliliğe dayanıyor. 152 yılda batan her emeklilik 1964 ile
1969 arasında başlamış — yüksek değerlemeler, sonra 70'ler. Ve "68 tarihsel
dönem" kulağa 68 test gibi geliyor ama ardışık 30 yıllık pencereler 30 yılın
29'unu paylaşıyor. Gerçekten örtüşmeyen üç tane var. Kuralın arkasında bir
yüzyıllık bağımsız kanıt yok. Yaklaşık üç emeklilik var, biri de kötü gitmiş.

Kuralın söylemediği bir şey daha. "Başarı", portföyün sıfırlanmaması demek.
Değerini koruması demek değil. Başarılı sayılan 62 emekliliğin 29'u, başladığından
daha az reel parayla bitmiş — biri dörtte biriyle, bir diğeri beş katıyla. Hepsi
başarı sayılıyor.

Bunların hiçbiri makaleleri yanlış çıkarmıyor. Ne dediyseler özenle dediler ve
sağlam duruyor. Şartları düşüren, etrafında oluşan halk bilgisi.

Bütün sayılar, yöntem, çözemediğim yedi kısıt ve kod:
→ namikakmandev.github.io/four-percent-rule.html

Yatırım tavsiyesi değildir — bu, mekanik bir kurala tek bir ülkede geçmişte ne
olduğunu inceleyen iki makalenin replikasyonudur. Tarihsel bir başarı oranı,
sizin emekliliğiniz için bir olasılık değildir.

---

## Comment to pin (both languages, pick one)

EN: Credit where it is due. Robert Shiller has published his monthly US market
and CPI series openly for decades — github.com/datasets/s-and-p-500 — which is
the only reason a replication like this can be done by anyone with a laptop.
Bengen and the Trinity authors also described their method clearly enough to be
re-run thirty years later. That is the standard.

TR: Hakkını teslim edelim. Robert Shiller aylık ABD piyasa ve TÜFE serisini
onlarca yıldır açık yayımlıyor — github.com/datasets/s-and-p-500 — bu tür bir
replikasyonun dizüstü bilgisayarla yapılabilmesinin tek sebebi bu. Bengen ve
Trinity yazarları da yöntemlerini otuz yıl sonra yeniden çalıştırılabilecek
kadar açık anlatmışlar. Standart budur.

---

## Reply templates

- **"So what should my withdrawal rate be?"** → Decline. This is a replication of
  what happened to a mechanical rule in US history, not advice about anyone's
  savings. Point at the sensitivity table on the page and note that the answer
  depends on horizon, fees, taxes and what else you have coming in — none of
  which the rule models.
- "So the 4% rule is dead / debunked?" → No, and the post says so. The papers
  replicate. What does not survive is the folklore version that drops the
  conditions — corporate bonds, 30 years, before fees, US only.
- "3.6% vs 4% is a rounding difference, who cares?" → On a €1m portfolio it is
  €4,000 a year for thirty years. But the real point is not the level, it is that
  a third of a point comes from where you put the withdrawal in the spreadsheet.
  If a modelling convention moves your answer that much, quoting it to two
  decimals is the mistake.
- "Why government bonds when they used corporate?" → Because the corporate
  series is not public and I would rather show the gap than fake it. Stage 1 on
  the page quantifies exactly what the spread is worth and reproduces their
  numbers with it.
- "Your data stops in 2022." → Yes, and the page says so: the public mirror's
  dividend and CPI columns lag, so the last complete 30-year window begins in
  1993. Every retirement that started later is still running anyway, which is
  the same reason the 1998 authors could not test the 1966 cohort.
- "What about outside the US?" → Not tested here, and I say that explicitly. The
  published international work (Pfau 2010, Estrada 2017) finds materially lower
  safe rates in most other developed markets. No comparable long-run
  international total-return series is openly available, so I cite it rather than
  claim it.
- Turkey/lira questions (likely) → The study is US-only and says nothing about a
  high-inflation currency. Decline rather than extrapolate; the honest answer is
  that the 1964–69 cohort failed on 1970s US inflation alone, which should tell
  you how a rule like this behaves under worse.

---

## Prepared replies — expert challenges

1. "Your bond proxy is a constant-maturity government bond built from one point
   on the curve — that isn't a real index." → Correct, and it is the study's
   main weakness, stated as limitation one. It is run at both 10 and 5 years
   (SAFEMAX 3.60% vs 3.80%) so the reader can see what the choice is worth, and
   stage 1 shows what closes the gap to the published corporate-bond numbers.
2. "Annual January-to-January steps understate sequence risk." → Agreed, and on
   the page. Real retirees withdraw monthly and retire in months other than
   January. Annual steps are what both original papers used, which is why the
   replication keeps them.
3. "You can't call three non-overlapping windows a sample size." → That is the
   point being made, not a claim being defended. It is also why no confidence
   interval appears anywhere on the page — an interval computed off 68
   overlapping windows would be theatre.
4. "Conditioning SAFEMAX on the worst single cohort is a degenerate statistic." →
   Fair. SAFEMAX is by construction a minimum over windows, so it is set by one
   episode and has no sampling distribution worth quoting. That is exactly why
   the page reports full success-rate tables beside it rather than leading on
   SAFEMAX alone.
5. "Bengen got 4%+ and you get 3.6% — did you replicate him or not?" → Bengen
   used intermediate Treasuries and started at 1926; the timing convention and
   bond maturity between us account for the difference, and both are shown as
   rows in the sensitivity table. His qualitative claim — no 30-year failure at
   4% in his sample and assumptions — is not contradicted here.
6. "Taxes would change everything." → Yes, and neither original paper modelled
   them either. Noted as a limitation; a taxable retiree's effective draw is
   above the headline rate.
