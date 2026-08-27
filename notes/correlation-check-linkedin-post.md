# Correlation & Regression Check — LinkedIn assets

**Chosen format: text post + one link.** The tool itself is the demo — every
claim in the copy is one click to verify, on real public data, in the
reader's own browser. No image needed; the link preview carries the card.

The three real-data examples load from the site's own committed datasets, so
the post cannot contradict the data:

- `correlation-check.html?real=corn` — BLS cattle vs corn PPIs, 1971–2026
- `correlation-check.html?real=parity` — US vs EU cattle margins
- `correlation-check.html?real=vet` — Eurostat vet spend vs FAOSTAT herd
- `group-check.html?real=bigmac2` — Big Mac index, rich vs emerging, Jul 2026

---

## Before posting

- [ ] Check your employer's external communications policy.
- [ ] Rewrite the copy in your own words if anything feels off.
- [ ] The cattle examples overlap your professional domain — as with the
      vet-CPI post, decline commentary on market direction in replies; the
      post is about statistical method, not cattle markets.
- [ ] Open all four links on your phone once before posting.

---

## Post copy — English

For 55 years, US cattle and corn prices have correlated at r = 0.59, with
p = 10⁻⁶³.

That p-value says the odds of this being luck are about one in a number with
63 digits. It is also almost completely meaningless.

667 monthly observations of two slow-moving price indexes carry roughly 8
independent facts between them — each month is mostly a copy of the last, and
the textbook formula has no idea. Count the evidence honestly and the
"overwhelming" correlation is not even significant. What survives in
year-on-year changes is r = 0.09: real, and explaining 1% of the variance.

I kept catching versions of this mistake in my own published work. So I built
a checker that catches it for me — and put it on my site, free, with the same
public data I got burned on wired in as one-click examples:

→ A correlation of 0.59 that is mostly inflation (BLS, 55 years)
→ One that survives every test — US and EU cattle margins, an ocean apart,
  significant AND cointegrated (BLS + European Commission)
→ A famous r = −0.94 from my own field that, checked honestly, does not
  exist at all (Eurostat + FAOSTAT)

Every result shows the naive p-value next to the honest one, the effect size
next to the p-value, and a shuffle test that assumes nothing. There's a
regression layer with autocorrelation-robust errors, a confounder control,
and a "Show as Python" button that emits the same analysis as a runnable
pandas/statsmodels script — validated to four decimals against the real
libraries.

Everything runs in your browser. Your data never leaves the page.

[link: namikakmandev.github.io/correlation-check.html?real=corn]

If you work with time series and have ever put a correlation in a slide, try
the corn example first. It takes ten seconds and it may change what you quote
on Monday.

---

## Post copy — Türkçe

ABD'de sığır ve mısır fiyatları 55 yıldır r = 0,59 korelasyonla hareket
ediyor; p = 10⁻⁶³.

Bu p-değeri, "şans olma ihtimali 63 haneli bir sayıda bir" diyor. Ve aynı
zamanda neredeyse tamamen anlamsız.

İki yavaş hareket eden fiyat endeksinin 667 aylık gözlemi, aralarında
yaklaşık 8 bağımsız bilgi taşıyor — her ay büyük ölçüde bir önceki ayın
kopyası, ve ders kitabındaki formülün bundan haberi yok. Kanıtı dürüstçe
sayınca o "ezici" korelasyon anlamlı bile değil. Yıllık değişimlerde geriye
kalan r = 0,09: gerçek, ama varyansın %1'ini açıklıyor.

Kendi yayımlanmış çalışmalarımda bu hatanın farklı kılıklarını yakalayıp
durdum. Ben de benim yerime yakalayan bir araç yaptım — siteme koydum,
ücretsiz, ve beni yanıltan kamu verilerini tek tıklık örnekler olarak içine
gömdüm:

→ Çoğu enflasyondan ibaret bir 0,59 korelasyonu (BLS, 55 yıl)
→ Her testten geçen bir ilişki — ABD ve AB sığır marjları, okyanus ötesinden,
  anlamlı VE eşbütünleşik (BLS + Avrupa Komisyonu)
→ Kendi alanımdan ünlü bir r = −0,94 — dürüstçe bakınca hiç yok
  (Eurostat + FAOSTAT)

Her sonuçta naif p-değeri dürüstünün yanında, etki büyüklüğü p-değerinin
yanında, ve hiçbir varsayım yapmayan bir karıştırma testi. Üstüne
otokorelasyona dayanıklı hatalarla regresyon katmanı, karıştırıcı değişken
kontrolü ve aynı analizi çalışır bir pandas/statsmodels betiği olarak veren
"Show as Python" düğmesi var — gerçek kütüphanelere karşı dört ondalığa
kadar doğrulandı.

Her şey tarayıcınızda çalışıyor. Veriniz sayfadan çıkmıyor.

[link: namikakmandev.github.io/correlation-check.html?real=corn]

Zaman serisiyle çalışıyorsanız ve bir slayta korelasyon koyduysanız, önce
mısır örneğini deneyin. On saniye sürüyor ve pazartesi neyi alıntıladığınızı
değiştirebilir.

---

## Comment to pin (both languages, pick one)

EN: The companion tool for group comparisons is live too — the Big Mac index,
rich vs emerging economies, with the effect size the p-value hides:
namikakmandev.github.io/group-check.html?real=bigmac2

TR: Grup karşılaştırmaları için kardeş araç da yayında — Big Mac endeksi,
gelişmiş vs gelişmekte olan ekonomiler, p-değerinin sakladığı etki
büyüklüğüyle: namikakmandev.github.io/group-check.html?real=bigmac2

---

## Reply templates

- "Which test should I use?" → The tool's answer: run all three routes
  (formula, ranks, shuffle) — when they agree the label doesn't matter, when
  they disagree the disagreement tells you what's wrong with the data.
- "Isn't n_eff too conservative?" → It is one standard correction
  (Bartlett/Quenouille); the block bootstrap and Newey–West lines in the tool
  are the other two, and they agree. The naive p is the outlier, not the
  honest ones.
- Requests for market commentary on cattle → decline per the note above;
  the post is about method.
