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

In 1986, The Economist invented an economic indicator as a joke.

Compare the price of a Big Mac around the world, they said, and you can
tell which currencies are too cheap or too expensive.

40 years later, people still quote it in meetings. So I tested it — on
The Economist's own published data (@The Economist). 55 countries, 26
years of burger prices.

Three findings:

🍔 The joke actually works. When a Big Mac in a country gets unusually
expensive or unusually cheap COMPARED TO THAT COUNTRY'S OWN PAST, the
price drifts back to normal. About half of the gap closes within 3 years.
And here is the fun part: serious economists, using far fancier price
data, find the same 3-year answer for exchange rates. A hamburger matches
the textbooks.

🍔 But most people read it wrong. The common take is: "Burgers are cheap
in country X, so its currency will rise." That version barely works.
Burgers are cheap in poorer countries for a permanent reason — wages,
rent, everything is cheaper there. Cheap countries mostly just stay
cheap. The index is good at comparing a country to its own history, and
bad at comparing countries to each other.

🍔 How did I test it? With the open statistics toolkit I built for my
own work. It has one job: take a finding and try everything to kill it
(swap the base currency, split the years into different eras, drop the
most extreme countries, rerun the numbers on thousands of reshuffled
samples). The 3-year result survived every attempt. My first attempt
didn't: it said 1 year, because my formula had quietly peeked into the
future. The toolkit caught that. It is exactly what it is for.

All the numbers, how I did it, what it can NOT tell you, and the code
that lets anyone re-run the whole thing:
→ namikakmandev.github.io/bigmac-halflife.html

Happy 40th birthday to the best joke in economics. It holds up — if you
read it right.

---

## Post copy — Türkçe

1986'da The Economist şaka olsun diye bir ekonomik gösterge icat etti.

Dediler ki: dünyanın her yerinde Big Mac fiyatını karşılaştırın, hangi
para birimlerinin fazla ucuz ya da fazla pahalı olduğunu görürsünüz.

40 yıl sonra insanlar hâlâ toplantılarda bunu alıntılıyor. Ben de test
ettim — The Economist'in kendi yayımladığı veriyle (@The Economist).
55 ülke, 26 yıllık burger fiyatı.

Üç sonuç:

🍔 Şaka gerçekten çalışıyor. Bir ülkede Big Mac, O ÜLKENİN KENDİ
GEÇMİŞİNE GÖRE alışılmadık biçimde pahalanır ya da ucuzlarsa, fiyat
normale geri dönüyor. Açığın yaklaşık yarısı 3 yıl içinde kapanıyor. İşin
güzel tarafı: ciddi iktisatçılar, çok daha sofistike fiyat verileriyle,
döviz kurları için aynı 3 yıllık cevabı buluyor. Bir hamburger, ders
kitaplarıyla aynı sonucu veriyor.

🍔 Ama çoğu kişi endeksi yanlış okuyor. Yaygın yorum şu: "X ülkesinde
burger ucuz, demek ki kuru değerlenecek." Bu versiyon neredeyse hiç
çalışmıyor. Burger, yoksul ülkelerde kalıcı bir sebepten ucuz — ücretler,
kiralar, her şey orada daha ucuz. Ucuz ülkeler çoğunlukla ucuz kalıyor.
Endeks bir ülkeyi kendi geçmişiyle karşılaştırmakta iyi, ülkeleri
birbiriyle karşılaştırmakta kötü.

🍔 Peki nasıl test ettim? Kendi işlerim için geliştirdiğim, sitemde açık
duran istatistik araç setiyle. Tek bir görevi var: bir bulguyu alıp onu
öldürmek için her yolu denemek (baz para birimini değiştir, yılları
farklı dönemlere böl, en uç ülkeleri çıkar, hesabı binlerce karıştırılmış
örneklem üzerinde yeniden çalıştır). 3 yıl sonucu her denemeden sağ
çıktı. İlk denemem çıkamadı: 1 yıl diyordu, çünkü formülüm sessizce
geleceğe bakmıştı. Bunu araç seti yakaladı. Zaten tam bunun için var.

Bütün sayılar, nasıl yaptığım, neyi SÖYLEYEMEYECEĞİ ve herkesin baştan
çalıştırabileceği kod:
→ namikakmandev.github.io/bigmac-halflife.html

Ekonominin en iyi şakasına nice 40 yıllara. Ayakta duruyor — doğru
okursanız.

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

---

## Prepared replies — expert challenges (from adversarial pre-mortem)

Post-publication, three agents stress-tested the post: a cold reader (8/10
clarity), a fact-checker (all claims verified against the script), and a
hostile econometrician. The strongest expert attacks, each with a ready
reply. Concede what should be conceded; the receipts page now carries a
limitations bullet for every one of these.

1. "The gap closes through inflation, not the currency — this says nothing
   about FX." → Fair, and the sharpest comment here. What reverts is the
   burger-based REAL exchange rate — nominal rate plus relative prices —
   which is exactly the object the academic 3–5y half-life describes;
   "for exchange rates" in my post was loose shorthand for that. In
   high-inflation cases the gap closes through prices, agreed — which is
   why the conclusion is "how to read the indicator," not "the currency
   will rise." It's in the limitations on the page.

2. "Country clustering ignores common time shocks — your CI is too
   narrow." → Correct, and the page now says so. Partial pushback: the
   USD-base rerun gives the same slope (−0.378 vs −0.382), so it isn't one
   base currency's cycle, and both subperiods agree, so it isn't one
   global episode. But a country×time scheme would be stricter and the
   interval is honestly labelled "if anything, too narrow."

3. "Your code counts rows, not calendar time — early data is annual." →
   You found a real approximation, and I re-ran it your way: pairing each
   date with the observation closest to exactly 2.0 years later (n=1395,
   mean span 2.01y) gives slope −0.359, CI [−0.539, −0.183], half-life
   3.1 years — slightly LONGER than the headline, same conclusion. Script
   is on the page (bigmac_caltime_check.py). The 2013–2026 row is also a
   clean-spacing check: perfectly regular data, 2.8y.

4. "This is just stationarity / mechanical reversion to a mean." → Yes —
   that is literally the claim: the burger real exchange rate is
   stationary with the same half-life the broad-index PPP literature
   finds, which was genuinely contested for a one-good index. On
   measurement noise: noise reverses immediately, so it would make the
   1-year-implied half-life much shorter than the 3-year one; instead they
   run 2.5 / 2.9 / 3.2 years — the signature of slow real decay.

5. "Survivorship: McDonald's leaves exactly when currencies blow up
   (Russia 2022, Sri Lanka 2024, Iceland never)." → Legitimate, and now
   on the page: exit correlates with crisis and censors the very episodes
   most likely to show non-reversion. Two exits out of 55 currencies, so
   the pooled slope barely moves — but the honest scope is "reversion
   holds among countries stable enough to keep a McDonald's."

6. "Your drop-the-extremes check dropped zero countries." → Caught
   fairly: the |dev|>100% threshold binds nothing — the max deviation is
   98% (Venezuela) — so that row is a disclosure, not a surviving test.
   The largest observed deviations (Venezuela, Lebanon) do revert in the
   predicted direction, and the page now says the row was a no-op in as
   many words.
