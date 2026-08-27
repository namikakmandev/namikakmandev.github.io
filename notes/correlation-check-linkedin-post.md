# Correlation & Regression Check — LinkedIn assets

**Chosen format: text post + one link.** The tool itself is the demo — every
claim in the copy is one click to verify, on real public data, in the
reader's own browser. No image needed; the link preview carries the card.

The real-data examples load from the site's own committed datasets, so the
post cannot contradict the data:

- `correlation-check.html?real=btcgold` — Bitcoin vs gold (Yahoo, monthly 2014–)
- `correlation-check.html?real=btcnasdaq` — Bitcoin vs Nasdaq
- `correlation-check.html?real=co2` — CO₂ vs global temperature (OWID)
- `correlation-check.html?real=pump` — US pump prices vs WTI (FRED)
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
- [ ] Open the example links on your phone once before posting (at least
      btcgold, btcnasdaq, co2 and the pinned bigmac2).

---

## Post copy — English

"Bitcoin is digital gold."

It is the most repeated claim in crypto, and it is testable in ten seconds.
Since 2014, Bitcoin and gold in LEVELS correlate at r = 0.86 — impressive,
until you learn two independent random walks do the same. Month to month,
where a real relationship would live: r = 0.06, indistinguishable from zero.
Bitcoin and the NASDAQ, month to month? r = 0.34, highly significant.

Bitcoin is not digital gold. It is a tech-adjacent risk asset — and one
honest statistical check settles it.

I kept catching versions of the same mistake in my own published work
(a correlation of −0.94 I once believed simply is not there). So I built a
checker that catches it for me, put it on my site free, and wired in real
public data as one-click examples:

→ Bitcoin vs gold — the claim, tested (Yahoo Finance, monthly since 2014)
→ Bitcoin vs Nasdaq — what it actually moves with
→ CO₂ vs global temperature — where the naive check fails in BOTH
  directions, and the cointegration test gets it right
→ Pump prices vs crude oil — how much of a barrel reaches your tank
→ 55 years of US cattle vs corn — a p-value of 10⁻⁶³ that means nothing

Every result shows the naive p-value next to the honest one, the effect
size next to the p-value, and a shuffle test that assumes nothing. A
"Show as Python" button emits the same analysis as a runnable
pandas/statsmodels script, validated to four decimals against the real
libraries. Everything runs in your browser; your data never leaves the page.

[link: namikakmandev.github.io/correlation-check.html?real=btcgold]

If you have ever put a correlation in a slide, try the Bitcoin-gold
example first. Ten seconds, and it may change what you quote on Monday.

---

## Post copy — Türkçe

"Bitcoin dijital altındır."

Kriptonun en çok tekrarlanan iddiası — ve on saniyede test edilebilir.
2014'ten beri Bitcoin ile altın SEVİYEDE r = 0,86 korelasyonda; etkileyici,
ta ki iki bağımsız rastgele yürüyüşün de aynısını yaptığını öğrenene kadar.
Gerçek bir ilişkinin yaşayacağı yerde, aydan aya: r = 0,06 — sıfırdan
ayırt edilemez. Bitcoin ile NASDAQ, aydan aya? r = 0,34, fazlasıyla anlamlı.

Bitcoin dijital altın değil. Teknolojiye yaslanan bir risk varlığı — ve tek
bir dürüst istatistik kontrolü bunu bitiriyor.

Aynı hatanın farklı kılıklarını kendi yayımlanmış işlerimde yakalayıp durdum
(bir zamanlar inandığım −0,94'lük bir korelasyon aslında yok). Ben de benim
yerime yakalayan bir araç yaptım, siteme ücretsiz koydum ve gerçek kamu
verilerini tek tıklık örnekler olarak içine gömdüm:

→ Bitcoin vs altın — iddianın testi (Yahoo Finance, 2014'ten beri aylık)
→ Bitcoin vs Nasdaq — gerçekte neyle hareket ettiği
→ CO₂ vs küresel sıcaklık — naif kontrolün İKİ yönde de yanıldığı,
  eşbütünleşme testinin doğru bildiği örnek
→ Pompa fiyatı vs ham petrol — varilin ne kadarı depoya ulaşıyor
→ 55 yıllık ABD sığır vs mısır — hiçbir anlamı olmayan 10⁻⁶³'lük p-değeri

Her sonuçta naif p-değeri dürüstünün yanında, etki büyüklüğü p-değerinin
yanında, hiçbir varsayım yapmayan bir karıştırma testi de cabası. "Show as
Python" düğmesi aynı analizi çalışır bir pandas/statsmodels betiği olarak
veriyor — gerçek kütüphanelere karşı dört ondalığa kadar doğrulandı. Her şey
tarayıcınızda; veriniz sayfadan çıkmıyor.

[link: namikakmandev.github.io/correlation-check.html?real=btcgold]

Bir slayta korelasyon koyduysanız, önce Bitcoin-altın örneğini deneyin.
On saniye — ve pazartesi neyi alıntıladığınızı değiştirebilir.

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
- Crypto price predictions or "so should I buy BTC?" → same posture: the
  post tests a statistical claim, not an investment thesis. The tool shows
  co-movement, not causes and not forecasts.
- "Correlation changed after 2020 / during ETF approval" → agree — the
  split-half row in the robustness table shows exactly that instability;
  invite them to click it.
