# Big Mac half-life — LinkedIn assets

**Chosen format: text post + the one chart image + one link.** The image is
`assets/linkedin/bigmac-halflife.png` (regenerate any time with
`python3 scripts/bigmac_chart.py`). The link is the receipts page, which
carries the full numbers table, method, limitations, and the reproducible
script:

- `namikakmandev.github.io/bigmac-halflife.html` — receipts page (the link in the post)
- `namikakmandev.github.io/group-check.html?real=bigmac2` — interactive cross-check (pinned comment)
- `github.com/TheEconomist/big-mac-data` — The Economist's open data (pinned comment)

Every number in the copy comes from `scripts/bigmac_reversion.py` (seeded,
deterministic): honest slope −0.38 per 2 years, CI [−0.58, −0.18], n = 1461,
half-life ≈ 2.9y vs own history, ≈ 6.4y raw cross-country, look-ahead
version ≈ 1.1y.

---

## Before posting

- [ ] Check your employer's external communications policy.
- [ ] Rewrite the copy in your own words if anything feels off.
- [ ] Attach the chart image; open the receipts link on your phone once.
- [ ] Tagging The Economist: type `@The Economist` and pick the company page
      when LinkedIn suggests it. Tag them in the POST body once, not in
      every comment. Realistic expectation: the main account will not reply,
      but their data team maintains the open dataset and has engaged with
      community analyses of it before — the pinned comment crediting the
      dataset is what they would actually see and appreciate.
- [ ] Framing is tribute, not gotcha — the finding VALIDATES the index. Keep
      it that way in replies too.
- [ ] Do not mimic The Economist's visual style, typeface, or logo in the
      image; cite them by name, keep your own house style. (The chart
      already does this.)
- [ ] This is not investment or FX advice — decline forecast requests in
      replies (template below).

---

## Post copy — English

In 1986 The Economist invented an economic indicator as a joke: compare Big
Mac prices across countries and you can see which currencies are cheap.

Forty years later, everyone still quotes it — so I tested it. All of it:
55 countries, every semi-annual reading since 2000, 1,461 currency-episodes
(open data published by The Economist itself — @The Economist).

Three things fell out.

1️⃣ The joke index works. When a currency's burger price drifts away from
its OWN historical normal, the gap closes — reliably. About half of it
disappears within 3 years (95% CI roughly 1.5 to 7). That is not a burger
fact: 3–5 years is the same half-life the academic literature finds for
purchasing-power parity using far fancier price data. A hamburger
reproduces the peer-reviewed number.

2️⃣ But not the way people read it. The popular reading — "burgers are
cheap in country X, so its currency must rise" — is much weaker. Raw
cross-country gaps have a half-life of 6+ years, because a large part of
each gap is permanent: poor countries are structurally cheaper (economists
call it the Penn effect). Cheap countries mostly just stay cheap. The index
tells you where a currency stands versus its own history, not which
countries are bargains.

3️⃣ And my first result was wrong. My first run said the gap closes in
about 1 year — suspiciously good. It was look-ahead bias: I had defined
each currency's "normal" using its full history, including the future. Fix
that (each date may only see its own past) and the honest answer is 3
years, not 1. Most too-good-to-be-true backtests die exactly there.

Every number, the method, its limitations, and a script that reproduces the
whole thing to the last decimal:
→ namikakmandev.github.io/bigmac-halflife.html

Consider this a 40th-birthday compliment to the best joke in economics: it
holds up — just read it the right way.

---

## Post copy — Türkçe

1986'da The Economist şaka olsun diye bir ekonomik gösterge icat etti:
ülkeler arasında Big Mac fiyatlarını karşılaştırın, hangi para birimlerinin
ucuz olduğunu görün.

Kırk yıl sonra herkes hâlâ alıntılıyor — ben de test ettim. Hepsini:
55 ülke, 2000'den beri her altı aylık okuma, 1.461 kur-dönemi (verinin
kaynağı The Economist'in kendi açık veri seti — @The Economist).

Üç sonuç çıktı.

1️⃣ Şaka endeks çalışıyor. Bir para biriminin burger fiyatı KENDİ tarihsel
normalinden uzaklaştığında, açık kapanıyor — güvenilir biçimde. Yaklaşık
yarısı 3 yıl içinde yok oluyor (%95 güven aralığı kabaca 1,5–7 yıl). Bu bir
burger tesadüfü değil: akademik literatür çok daha sofistike fiyat
verileriyle satın alma gücü paritesi için aynı 3–5 yıllık yarı ömrü
buluyor. Bir hamburger, hakemli dergideki sayıyı yeniden üretiyor.

2️⃣ Ama insanların okuduğu şekilde değil. Yaygın okuma — "X ülkesinde
burger ucuz, demek ki kuru değerlenecek" — çok daha zayıf. Ülkeler arası
ham farkların yarı ömrü 6+ yıl; çünkü her farkın büyük bir kısmı kalıcı:
yoksul ülkeler yapısal olarak daha ucuz (iktisatçılar buna Penn etkisi
diyor). Ucuz ülkeler çoğunlukla ucuz kalıyor. Endeks size bir kurun kendi
tarihine göre nerede durduğunu söylüyor — hangi ülkenin kelepir olduğunu
değil.

3️⃣ Ve ilk sonucum yanlıştı. İlk denemem açığın yaklaşık 1 yılda
kapandığını söyledi — şüphe uyandıracak kadar iyi. Sebep ileriye-bakma
hatasıydı (look-ahead bias): her kurun "normalini" geleceği de içeren tüm
tarihiyle tanımlamıştım. Düzeltince (her tarih yalnızca kendi geçmişini
görebilir) dürüst cevap 1 değil 3 yıl. Gerçek olamayacak kadar iyi
backtest'lerin çoğu tam burada ölür.

Bütün sayılar, yöntem, sınırlılıklar ve her şeyi son ondalığa kadar yeniden
üreten betik:
→ namikakmandev.github.io/bigmac-halflife.html

Bunu ekonominin en iyi şakasına 40. yaş günü iltifatı sayın: endeks ayakta
— yeter ki doğru okunsun.

---

## Comment to pin (both languages, pick one)

EN: Credit where due: The Economist publishes the entire Big Mac dataset as
open data — github.com/TheEconomist/big-mac-data — which is what made this
test possible. If you want to poke at the same data yourself in the
browser: namikakmandev.github.io/group-check.html?real=bigmac2

TR: Hakkını teslim edelim: The Economist, Big Mac veri setinin tamamını
açık veri olarak yayımlıyor — github.com/TheEconomist/big-mac-data — bu
test bu sayede mümkün oldu. Aynı veriyi tarayıcıda kendiniz kurcalamak
isterseniz: namikakmandev.github.io/group-check.html?real=bigmac2

---

## Reply templates

- "So should I trade on this?" → No. A 3-year half-life with R² ≈ 13% at
  the 3-year horizon is a slow, noisy statistical tendency, not a trading
  signal — and after real-world costs and risk it is not investment advice.
  The post is about how to read an indicator, not how to trade it.
- "Is currency X going to appreciate?" → Decline: the analysis is pooled
  across 55 currencies; it says nothing reliable about any single one. The
  receipts page shows the spread around the average.
- "Why euro-relative? Everything is quoted in dollars." → The Economist
  publishes both; I ran both. Dollar-base gives the same slope (−0.378 vs
  −0.382) — the finding does not depend on the base currency. Table on the
  receipts page.
- "Isn't this just PPP / already known?" → Yes — that is the point. The
  academic PPP consensus (3–5y half-life) comes from broad price indices;
  the fun part is that a single sandwich reproduces it. The Penn-effect
  caveat in layer 2 is also standard economics; the post packages both with
  receipts, not novelty claims.
- "What about GDP-adjusted index?" → The Economist's GDP-adjusted version
  is precisely their fix for the Penn effect in layer 2 — it asks "cheap
  relative to what income predicts" instead of "cheap outright." My layer-1
  result (vs own history) is a different, time-series fix for the same
  problem.
- "Your first result was wrong — why trust the second?" → Fair question,
  and the reason everything is published: seeded script, open data, every
  robustness row (base currency, subperiods, horizons, outliers) on the
  receipts page. Don't trust me — run it.
- Turkey/lira questions (likely, given TR audience) → Same posture as
  "currency X": pooled result, no single-currency claims, not advice.
