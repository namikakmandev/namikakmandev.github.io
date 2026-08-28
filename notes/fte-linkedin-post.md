# FiveThirtyEight calibration — LinkedIn assets

**Chosen format: text post + the one chart image + one link.** The image is
`assets/linkedin/fte-calibration.png` (regenerate any time with
`python3 scripts/fte_chart.py`). The link is the receipts page, which carries
the full numbers tables, method, limitations, and all three scripts verbatim:

- `namikakmandev.github.io/fte-calibration.html` — receipts page (the link in the post)
- `github.com/fivethirtyeight/checking-our-work-data` — 538's surviving archive (pinned comment)

Every number in the copy comes from `scripts/fte_calibration.py` (seeded,
stdlib-only, deterministic): overall calibration slope 0.990, CI [0.982, 0.997],
n = 255,057 independent calls from 3,101,140 published rows; politics slope
1.026; competitive political races slope 1.292, CI [1.201, 1.383], n = 1,122
across 557 races; Brier skill +19.1% overall, +41.6% on competitive politics;
82.2% of political forecasts sat outside the 10–90% band.

---

## Before posting

- [ ] Check your employer's external communications policy.
- [ ] Rewrite the copy in your own words if anything feels off.
- [ ] Attach the chart image; open the receipts link on your phone once.
- [ ] **Tagging.** FiveThirtyEight no longer exists as an organisation, and its
      LinkedIn page may be dormant or gone — check before relying on a tag. The
      people worth tagging are the ones who built and defended the record:
      Nate Silver (founder, now Silver Bulletin) and G. Elliott Morris (who ran
      the models after him). Verify each account exists on LinkedIn and is
      active before tagging; if only one is, tag only that one. Tag in the POST
      body once, not in every comment. Realistic expectation: a reply is
      unlikely, but this is a genuinely friendly result about work they are
      publicly proud of, and it is the kind of thing that gets reshared.
- [ ] Framing is tribute, not gotcha — the finding VALIDATES them, and the one
      criticism (underconfidence) is the flattering direction. Keep it that way
      in replies too.
- [ ] Do not mimic 538's visual style, typeface, or logo in the image; cite
      them by name, keep your own house style. (The chart already does this.)
- [ ] Do not claim to have tested the famous 71% national 2016 forecast. It is
      not in the archive. The copy says "state-level and down" — keep it there.
- [ ] This is not investment or political advice — decline prediction requests
      in replies (template below).

---

## Post copy — English

In March 2025, ABC shut down FiveThirtyEight and pulled the website offline.

Before that, 538 did something almost nobody in media does. They published
their own report card. Every forecast they ever made — 3.1 million published
probabilities — with the outcome attached, so that anyone could grade them.

That file is still sitting on GitHub. So I graded them.

Three findings:

📊 The claim holds. 538's line was always "when we say 70%, it happens about
70% of the time." Across 255,057 independent calls, it does. Every ten-point
band lands within about two points of where it should. Being that honest about
uncertainty, in public, for seventeen years, is rarer than it sounds.

📊 "It said 71% and it was WRONG" was never a criticism. If a forecaster says
70% and is never wrong, the forecaster is lying. In the races where 538 gave a
favourite around 70%, that favourite lost about a quarter of the time — which
is roughly what is supposed to happen. But being calibrated is a low bar on its
own: saying "50-50, always" is perfectly calibrated and perfectly useless. The
number that actually defends them is the skill score, and it is comfortably
positive.

📊 The surprise: they were too CAUTIOUS. Strip out the political forecasts that
were never in doubt — 82% of them were safe seats at 1% or 99% — and look only
at the races that were genuinely close. There, 538's favourites won MORE often
than 538 said they would. Where the model said 75%, the thing happened 88% of
the time. Everyone remembers 538 as overconfident. On the calls that were hard,
the record says the opposite: they hedged.

📊 How did I test it? With the open statistics toolkit I built for my own work.
Most of the job was refusing free wins. The raw file says n = 3.1 million; it
isn't. The same House race was re-forecast daily for months, every game had
in-play probabilities that are trivially easy once someone is 30 points up, and
each race was run through three model variants. Strip all of that and 3.1
million honest-looking rows become 255,057 real ones. Every excluded slice made
538 look better. That is exactly why they are excluded.

All the numbers, how I did it, what it can NOT tell you (including: the famous
2016 national forecast is not in the archive, so this does not test it), and the
code to re-run the whole thing:
→ namikakmandev.github.io/fte-calibration.html

They published the receipts knowing someone would eventually do this. The
receipts hold up.

---

## Post copy — Türkçe

Mart 2025'te ABC, FiveThirtyEight'ı kapattı ve siteyi tamamen yayından
kaldırdı.

Kapanmadan önce 538, medyada neredeyse hiç kimsenin yapmadığı bir şey yaptı:
kendi karnesini yayımladı. Yaptıkları her tahmini — 3,1 milyon olasılık —
sonucuyla birlikte açık veri olarak koydular ki isteyen not verebilsin.

O dosya hâlâ GitHub'da duruyor. Ben de not verdim.

Üç sonuç:

📊 İddia doğru çıktı. 538'in savunması hep şuydu: "%70 dediğimizde, o şey
yaklaşık %70 oranında gerçekleşiyor." 255.057 bağımsız tahmin üzerinde
gerçekten öyle. Her on puanlık bant, olması gereken yerin yaklaşık iki puan
yakınına düşüyor. Belirsizlik konusunda on yedi yıl boyunca alenen bu kadar
dürüst olmak, kulağa geldiğinden daha nadir.

📊 "%71 dedi ve YANILDI" hiçbir zaman bir eleştiri değildi. Bir tahminci %70
diyorsa ve hiç yanılmıyorsa, o tahminci yalan söylüyordur. 538'in favoriye
%70 civarı verdiği yarışlarda favori, zamanın yaklaşık dörtte birinde
kaybetti — yani olması gerektiği kadar. Ama tek başına kalibre olmak düşük bir
eşik: "hep 50-50" demek de mükemmel kalibredir ve tamamen işe yaramazdır. Onları
asıl savunan sayı beceri skoru, ve o rahatça pozitif.

📊 Sürpriz: fazla TEMKİNLİLER. Baştan belli olan siyasi tahminleri ayıklayın —
tahminlerin %82'si %1 ya da %99'luk garanti koltuklardı — ve yalnızca gerçekten
yakın yarışlara bakın. Orada 538'in favorileri, 538'in söylediğinden DAHA sık
kazanmış. Model %75 dediğinde, o şey zamanın %88'inde gerçekleşmiş. Herkes
538'i aşırı özgüvenli diye hatırlıyor. Zor olan tahminlerde kayıt tam tersini
söylüyor: çekingen davranmışlar.

📊 Peki nasıl test ettim? Kendi işlerim için geliştirdiğim açık istatistik araç
setiyle. İşin çoğu, bedava puanları reddetmekti. Ham dosya n = 3,1 milyon
diyor; değil. Aynı Temsilciler Meclisi yarışı aylarca her gün yeniden tahmin
edilmiş, her maçta biri 30 sayı öndeyken bilinmesi çok kolay olan canlı
olasılıklar var, ve her yarış üç ayrı model varyantından geçirilmiş. Bunların
hepsini çıkarınca dürüst görünen 3,1 milyon satır, 255.057 gerçek satıra
iniyor. Çıkardığım her dilim 538'i daha iyi gösteriyordu. Zaten tam bu yüzden
çıkarıldılar.

Bütün sayılar, nasıl yaptığım, neyi SÖYLEYEMEYECEĞİ (bu arada: ünlü 2016 ulusal
tahmini arşivde yok, dolayısıyla bu çalışma onu test etmiyor) ve her şeyi baştan
çalıştıracak kod:
→ namikakmandev.github.io/fte-calibration.html

Birinin er ya da geç bunu yapacağını bilerek makbuzları yayımlamışlar.
Makbuzlar sağlam.

---

## Comment to pin (both languages, pick one)

EN: Credit where it is due: 538 published this scorecard themselves —
github.com/fivethirtyeight/checking-our-work-data — under CC BY. The website is
gone; the archive is not. Publishing the data that lets strangers grade you is
the part of their legacy worth copying.

TR: Hakkını teslim edelim: bu karneyi 538'in kendisi yayımladı —
github.com/fivethirtyeight/checking-our-work-data — CC BY lisansıyla. Site
gitti; arşiv durmuyor değil. Yabancıların sizi notlandırmasına imkân veren
veriyi yayımlamak, mirasın kopyalanmaya değer kısmı.

---

## Reply templates

- "So 538 was right about 2016?" → This does not test the 2016 national
  forecast — it is not in the archive, which covers state-level presidential,
  Senate, House, governor and primaries. What it tests is the general
  calibration claim across their whole published record. Say so plainly rather
  than letting people assume otherwise.
- "So can I use this to predict the next election?" → No. This grades a
  forecaster's past record; it says nothing about any future race, and 538 no
  longer exists to forecast one.
- "Underconfident? That contradicts everything I've read." → It surprised me
  too, which is why the page shows it cut every way I could: it holds in all
  five political projects (slopes 1.17–1.34) and in seven of eight cycles. The
  exception is 2016 — slope 0.82, but on 30 races with an interval from 0.15 to
  1.49, too wide to conclude anything. The year everyone remembers is the year
  the data can't speak to.
- "n=1,122 is tiny compared to 3.1 million." → Correct, and that is the point of
  the third finding. The 3.1 million is repeat forecasts of the same events. The
  competitive political record really is about a thousand calls across roughly a
  dozen cycles. The page says so in the limitations.
- "Isn't picking the 10–90% band cherry-picking?" → It conditions on the
  forecast, never on the outcome — it asks "which calls were hard?" without
  knowing how any of them turned out. The full unfiltered table is on the page
  directly above it.
- "Sports aren't politics, why pool them?" → They are never pooled in any claim.
  Every table breaks politics and sports out separately, because 97% of the
  forecasts are sports and would otherwise drown the political result.
- "This is just Brier scores, nothing new." → Yes. The method is standard; what
  is new is running it on the flattery-removed sample and publishing what the
  removals cost. Most calibration takes of 538 use the raw pooled file.

---

## Prepared replies — expert challenges

The strongest attacks a forecasting or stats person could make, each with a
ready answer. Concede what should be conceded; the receipts page carries a
limitations bullet for every one of these.

1. "Your final-forecast choice is the most flattering snapshot — of course it
   is calibrated." → Fair, and tested: on the 1,818 contests carrying an earlier
   snapshot, re-running at ~30 days out gives an identical slope to three
   decimals (1.032 both ways) and skill falls only from +87.0% to +85.5%. Real
   caveat: the matched subsample is small and politics-heavy.
2. "Clustering by race should widen your interval, and yours got narrower —
   your standard errors are wrong." → It does get narrower, and the page says
   why in as many words: the two candidates in a race are mechanically
   anti-correlated, so their residuals cancel inside the cluster. That is a
   property of the estimator, not a claim of precision. The honest statement is
   the one on the page: the political result rests on 48 election dates,
   whatever the interval says.
3. "Calibration slope is a crude summary of a reliability curve." → Agreed,
   which is why the full binned table is on the page beside it — and the bins
   are where the underconfidence is actually visible (underdogs below 50% lost
   more than forecast, favourites above 50% won more).
4. "Selection: 538 chose which projects to publish scorecards for." → Conceded
   and on the page. This is the record they were willing to be graded on. It is
   still far more than any comparable outlet published.
5. "Skill vs a base-rate baseline is a soft comparison — beat a market." → Also
   conceded on the page. A +19.1% skill score says they beat a do-nothing
   forecaster, not a bookmaker or a rival model. The archive contains no
   competitor to compare against, so no such claim is made.
6. "Conditioning on 10–90% truncates the x-range and can bias a slope." → It
   restricts the range, which is why the finding is presented as a statement
   about that subgroup, cross-checked against the raw bin table, and cut by
   project and by cycle rather than resting on the single pooled slope.
