# ECB forecasters — LinkedIn assets

**Chosen format: text post + the one chart image + one link.** The image is
`assets/linkedin/ecb-forecasts.png` (regenerate with
`python3 scripts/ecb_chart.py`). The link is the receipts page:

- `namikakmandev.github.io/ecb-forecasts.html` — receipts page (the link in the post)
- `data.ecb.europa.eu` — the ECB's open microdata (pinned comment)

Every number comes from `scripts/ecb_spf_calibration.py` (stdlib-only,
deterministic): 1,369 individual one-year-ahead distributions, 110 forecasters,
2000–2025; outcome inside the forecaster's own 80% range 53.1% of the time
(31.1% above, 15.8% below); zero coverage in 2008, 2021, 2022 and 2023;
2021-Q4 mean P(inflation ≥4%) for 2022 = 0.50%, 33 of 48 said exactly zero,
most worried forecaster 6%, actual 8.36%; era split 75.8% / 30.0% / 49.4%;
excluding open-ended edge cases 54.9% (the one bias that flatters the finding,
worth 1.8pp).

---

## Before posting

- [ ] Check your employer's external communications policy.
- [ ] Rewrite the copy in your own words if anything feels off.
- [ ] Attach the chart image; open the receipts link on your phone once.
- [ ] **Tagging.** The @European Central Bank page is active on LinkedIn and this
      is their own open data being used exactly as intended — tag them once, in
      the post body. Do NOT tag or name any individual forecasting institution:
      the ECB anonymises panellists by number and the post must keep it that
      way. Naming a bank you think you have identified would be both wrong and
      a genuine problem.
- [ ] Framing is about **uncertainty, not competence**. The panel updated
      brilliantly fast once data arrived — 0.5% to 85% in six months. The
      criticism is narrow and specific: their stated ranges are too tight. Keep
      that distinction in replies; it is the whole point.
- [ ] Do not claim this tests the ECB's own staff projections. It does not.
      The SPF is a survey of outside institutions that the ECB collects.

---

## Post copy — English

In October 2021, the European Central Bank asked around fifty banks and
research houses a simple question: what are the odds that euro-area inflation
next year goes above 4%?

Two-thirds of them answered: zero.

The most worried forecaster in Europe said 6%.

Inflation came in at 8.4%.

That's the number that wrecked your input costs, your energy bill and your
customers' budgets. And the people whose job is to see it coming had ruled it
out.

But the interesting part isn't that they were wrong. It's what the full record
shows when you check all 26 years:

📊 Their confidence ranges are too narrow — always. The ECB doesn't just collect
a number; it collects a probability distribution from each forecaster. So you
can check something better than "was the forecast right?" You can check "was
their stated uncertainty honest?" Across 1,369 individual forecasts, when these
people mark out a range they are 80% sure about, the answer lands inside it 53%
of the time.

📊 They fail together, not separately. In 2008, 2021, 2022 and 2023, NOT ONE
forecaster in the panel had the outcome inside their own range. Not one, out of
about fifty, in four separate years. These aren't independent errors that cancel
out in an average. The whole room is wrong at the same time.

📊 And they're most accurate when it matters least. In 2007, 2018 and 2025
nearly every forecaster nailed it — calm years when the answer was "about the
same as last year." The forecast is precise exactly when you don't need it, and
fails in unison exactly when you do.

📊 They weren't stubborn, either. Watch the panic: 0.5% in October 2021, 9% by
March 2022, 85% by June. They updated faster than almost anyone would have. The
failure wasn't refusing to change their minds. It was that nothing in their
models put any weight on it until it was already happening.

One detail I can't stop thinking about: the survey's top answer box was
"4.0% or more." That was the widest outcome the ECB thought worth asking about.
The questionnaire physically could not express what happened.

The practical lesson, and the reason I ran this: a consensus forecast range is
not a risk range. It tells you what a well-informed room considers normal. It
tells you nothing about the years that hurt — because in those years, the room
is unanimous and unanimously wrong.

So if you are setting a budget, a hedge or a supply contract: take your bad case
from what has actually happened, including 2008 and 2022, not from the range the
forecasters give you — which excluded both. And when every forecast you read
agrees, treat that as information about the forecasters, not about the world.

Every number, the method, seven limitations, and the code:
→ namikakmandev.github.io/ecb-forecasts.html

Credit where it's due: none of this would be checkable if the ECB didn't publish
every individual response. They do. (@European Central Bank)

---

## Post copy — Türkçe

Ekim 2021'de Avrupa Merkez Bankası, elli kadar bankaya ve araştırma kuruluşuna
basit bir soru sordu: gelecek yıl euro bölgesi enflasyonunun %4'ün üzerine
çıkma ihtimali nedir?

Üçte ikisi şu cevabı verdi: sıfır.

Avrupa'nın en endişeli tahmincisi %6 dedi.

Enflasyon %8,4 geldi.

Girdi maliyetlerinizi, enerji faturanızı ve müşterilerinizin bütçesini
darmadağın eden sayı buydu. Ve bunu önceden görmek işi olan insanlar, ihtimal
dışı bırakmıştı.

Ama ilginç olan yanıldıkları değil. 26 yılın tamamını kontrol edince kayıt şunu
gösteriyor:

📊 Güven aralıkları her zaman fazla dar. AMB sadece bir sayı toplamıyor; her
tahminciden bir olasılık dağılımı istiyor. Yani "tahmin doğru muydu?"dan daha
iyi bir şeyi kontrol edebiliyorsunuz: "belirttikleri belirsizlik dürüst
müydü?" 1.369 bireysel tahmin boyunca, bu insanlar %80 emin oldukları bir
aralık çizdiğinde, sonuç o aralığın içine zamanın %53'ünde düşüyor.

📊 Ayrı ayrı değil, birlikte yanılıyorlar. 2008, 2021, 2022 ve 2023'te panelde
TEK BİR tahminci bile sonucu kendi aralığının içinde tutamadı. Elli kişiden bir
tanesi bile, dört ayrı yılda. Bunlar ortalamada birbirini götüren bağımsız
hatalar değil. Bütün oda aynı anda yanılıyor.

📊 Ve en çok, en az önemli olduğunda isabetliler. 2007, 2018 ve 2025'te
neredeyse herkes tutturdu — cevabın "aşağı yukarı geçen yılki gibi" olduğu
sakin yıllar. Tahmin, tam da ihtiyacınız olmadığında hassas; tam da ihtiyacınız
olduğunda hep birlikte çöküyor.

📊 İnatçı da değillerdi. Paniğe bakın: Ekim 2021'de %0,5, Mart 2022'de %9,
Haziran'da %85. Neredeyse herkesten hızlı güncellediler. Hata fikirlerini
değiştirmemek değildi. Modellerinde hiçbir şeyin, olay çoktan olurken bile
buna ağırlık vermemesiydi.

Aklımdan çıkmayan bir ayrıntı: anketin en üst cevap kutusu "%4 ve üzeri"ydi.
AMB'nin sormaya değer gördüğü en geniş sonuç buydu. Anket formu, olanı fiziksel
olarak ifade edemiyordu.

Pratik ders, ve bu çalışmayı yapma sebebim: konsensüs tahmin aralığı bir risk
aralığı değildir. Size iyi bilgilenmiş bir odanın neyi "normal" saydığını
söyler. Canınızı yakan yıllar hakkında hiçbir şey söylemez — çünkü o yıllarda
oda hemfikirdir ve hep birlikte yanılır.

Bütün sayılar, yöntem, yedi kısıt ve kod:
→ namikakmandev.github.io/ecb-forecasts.html

Hakkını teslim edelim: AMB her bir bireysel cevabı yayımlamasaydı bunların
hiçbiri kontrol edilemezdi. Yayımlıyorlar. (@European Central Bank)

---

## Comment to pin

EN: The ECB publishes every individual forecaster's full probability
distribution — data.ecb.europa.eu, Survey of Professional Forecasters. Not a
consensus number, not a summary: every response, anonymised by number, going
back to 1999. Publishing the data that lets strangers grade you is rarer than
it should be, and it is the only reason this check was possible.

TR: AMB, her bir tahmincinin tam olasılık dağılımını yayımlıyor —
data.ecb.europa.eu, Survey of Professional Forecasters. Konsensüs sayısı değil,
özet değil: 1999'a kadar giden, numarayla anonimleştirilmiş her bir cevap.
Yabancıların sizi notlandırmasına imkân veren veriyi yayımlamak olması
gerekenden daha nadir, ve bu kontrolün mümkün olmasının tek sebebi bu.

---

## Reply templates

- **"So forecasters are useless?"** → No, and the post says the opposite. In calm
  years nearly all of them contain the outcome, and they updated from 0.5% to
  85% in six months once data arrived. The narrow, specific criticism is that
  their stated ranges are too tight — not that their central view is worthless.
- **"So what should I use instead?"** → Nothing here recommends a replacement.
  The usable takeaway is about how to READ a consensus range: treat it as
  "what this room considers normal", not as a risk bound. If you need a
  downside case for planning, the consensus interval is not it.
- "Isn't this hindsight? Nobody could have known." → That's the honest defence
  and largely true for 2022. Which is why the study doesn't rest on 2022: the
  ranges are too narrow across all 26 years, and still too narrow with every
  crisis year removed (65.5% vs 80%).
- "You're attacking the ECB." → The SPF is a survey of outside institutions
  that the ECB collects and publishes. The ECB's own staff projections are a
  different series and are not tested here. The ECB comes out of this well: they
  publish the microdata that makes the criticism possible.
- "Which bank was forecaster #016?" → I don't know and wouldn't say. The ECB
  anonymises panellists by number deliberately. Decline this every time.
- "Coverage is a crude measure." → Agreed, and it's in the limitations: a miss
  by 0.1pp and a miss by 6pp count the same. It's used because it maps directly
  onto the claim being tested — does an 80% range behave like one.
- "The top bucket is open-ended, so your 2022 test is unfair." → It's not a test
  of how far they were wrong, only whether the outcome was outside their range,
  which the open bucket does not affect. And the open bucket is itself in the
  findings: the form couldn't express 8.4%.

---

## Prepared replies — expert challenges

1. "Overlapping panels — you're pooling non-independent forecasters and years."
   → Correct, and no confidence interval is quoted anywhere for exactly that
   reason. The point of the year-by-year table is that it doesn't need pooled
   inference: 0 out of 48 is 0 out of 48.
2. "Linear interpolation within buckets is arbitrary." → Yes, and it's stated.
   It's also conservative: for the open end buckets the boundary is used, which
   widens the implied range and flatters the forecasters. The bias runs against
   the finding, not toward it.
3. "Bucket widths changed over the sample, so coverage isn't comparable across
   eras." → Real, and it's the weakest part of the era comparison. The ECB
   revised the answer options, including widening them after 2022. Ranges are
   built from whatever buckets were offered in that round.
4. "Density coverage is a weak test; use a proper scoring rule (CRPS, log
   score)." → A fair ask. Coverage was chosen because it maps one-to-one onto
   the claim in plain language — "when they say 80% sure". A proper scoring rule
   would rank forecasters against each other, which is a different study and
   would need the naming they're anonymised to prevent.
5. "Survivorship in the panel." → Panellists join and leave, so the era
   comparison tracks a changing group, not a fixed one. Stated in limitations.
6. "2008 and 2022 both show 0% but are very different events." → Agreed, and
   that's the blunt-instrument limitation. Coverage cannot distinguish a small
   miss from an enormous one.
7. "Your open-ended top bucket makes the ranges artificially narrow." → Correct,
   and it is the one bias that runs toward the finding rather than away, so it
   is measured rather than argued about: it affects 47 of 1,369 distributions
   (3.4%), all at the top. Excluding them moves the headline from 53.1% to
   54.9%. Still nowhere near 80%.
8. "Have they fixed it since?" → Possibly. Coverage was 81% in 2024 and 100% in
   2025, and the ECB widened the answer buckets after 2022. But 2005-2007 also
   looked fixed, right up until 2008. Calm years cannot distinguish a
   recalibrated panel from a fair-weather one; the next turbulent year can.
