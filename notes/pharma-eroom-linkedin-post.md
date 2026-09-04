# Eroom's Law — LinkedIn assets

## What to upload

**One file: `notes/pharma-eroom-carousel.pdf`.** Post it as a LinkedIn document,
with the copy below as the body.

Five portrait slides, 4:5, same page size as the other carousels here. One idea
each: the hook, the claim, the two numbers, the AI answer, the caveat. Slide 1
is the ratio chart, so it is also the feed thumbnail and carries a headline of
its own. Rebuild with `python3 scripts/eroom_carousel.py`.

Standalone images if you would rather post images than a document:
`assets/linkedin/pharma-eroom.png` (the ratio) and
`assets/linkedin/pharma-approvals.png` (approvals, the AI answer).

**One link in the body:** `namikakmandev.github.io/pharma-eroom.html`

---

## Before posting

- [ ] The claim under test is Scannell, Blanckley, Boldon & Warrington (2012),
      *Nature Reviews Drug Discovery* 11, 191–200. Name the paper if challenged;
      it is a serious piece of work and this is not a takedown of it.
- [ ] **Do not say the paper was wrong.** Its own 1950–2010 window cannot be
      re-measured from open data. The finding is that the *rate did not
      continue*, which is a different and narrower claim.
- [ ] **Do not credit AI.** The step up finished in 2017;
      AI-designed molecules reached the clinic around 2020. The post says this
      explicitly because it is the first thing people will assume.
- [ ] The catch belongs in the post, not the comments: the ratio held up because
      approvals rose, not because spending fell.

---

## English

The deck does the explaining. The body only has to hook and hand off.

📊 &ldquo;Drug research gets worse every year.&rdquo; The most quoted number in
pharma.

A 2012 paper showed new drugs approved per billion dollars had halved every nine
years since 1950. Moore&rsquo;s Law backwards &mdash; Eroom&rsquo;s Law.

Its data stops in 2010. It is still on slides.

📈 I rebuilt it from the FDA&rsquo;s own records. Since 2008 it has not
fallen at all. The law says 0.17 new drugs per billion by 2021. It was
0.55.

🤖 Was it AI? No. The step up finished in 2017. AI-designed
molecules reached the clinic around 2020.

⚠️ The catch: approvals rose, spending did not fall. An approvals story,
not an efficiency story.

✅ If the nine-year halving goes in a business case, date it: 1950&ndash;2010.

🔗 namikakmandev.github.io/pharma-eroom.html

---

## Türkçe

📊 &ldquo;İlaç araştırması her yıl kötüleşiyor.&rdquo; Sektörde en çok
alıntılanan rakam.

2012 tarihli bir makale, milyar dolar başına onaylanan yeni ilaç sayısının
1950&rsquo;den beri her dokuz yılda yarıya indiğini gösterdi. Moore
Yasası&rsquo;nın tersi &mdash; Eroom Yasası.

Verisi 2010&rsquo;da bitiyor. Hâlâ sunumlarda.

📈 FDA&rsquo;nın kendi kayıtlarından yeniden kurdum. 2008&rsquo;den beri hiç
düşmemiş. Yasaya göre 2021&rsquo;de milyar dolar başına 0.17 olmalıydı.
0.55 oldu.

🤖 Sebep yapay zekâ mı? Hayır. Sıçrama 2017&rsquo;de bitti.
Yapay zekâ molekülleri kliniğe 2020 civarında ulaştı.

⚠️ İşin püf noktası: onaylar arttı, harcama düşmedi. Verimlilik hikâyesi
değil, onay hikâyesi.

✅ Dokuz yılda yarılanma bir iş gerekçesine girecekse tarihini yazın:
1950&ndash;2010.

🔗 namikakmandev.github.io/pharma-eroom.html

---

## Pinned comment

The data is open and both scripts are stdlib-only Python, so anyone can re-run
this and get the same numbers:

- FDA Drugs@FDA bulk archive (approvals) → fda.gov
- Eurostat rd_e_berdindr2, NACE C21 (R&D) → ec.europa.eu/eurostat
- Scripts → github.com/namikakmandev/namikakmandev.github.io/tree/main/scripts

The approvals count reproduces the FDA's own published novel-approval figures
almost exactly: 2015 45 against 45, 2016 22 against 22, 2023 55 against 55.

---

## If someone challenges it

**"So the paper was wrong."** No, and the post does not say that. Its
1950–2010 window cannot be re-measured — no open R&D series reaches back that
far, which three probe rounds established. The finding is that the published
*rate* did not continue after 2008.

**"Your denominator is not what they used."** Correct, and the page says so.
Eurostat's series is R&D *performed in* the US; the paper used global spend by
pharma firms. Different object. If a global series ever shows the ratio still
falling, the conclusion narrows to "the US stopped declining".

**"Fourteen points is nothing."** For a subtle effect, yes. Halving every nine
years is not subtle: it implies a slope of -0.0770 a year, and
the 95% interval here is [-0.0129, +0.0543]. It is not
close. Residual autocorrelation is negative, so that interval is conservative
rather than too narrow.

**"Approvals are not the same as good drugs."** Agreed, and that is the sharpest
limitation. A count of molecules says nothing about whether they work better,
cost less, or treat anything that mattered. It is on the page.

**"Isn't this just AI?"** No — the step finished in 2017,
years before AI-designed molecules reached the clinic.
