# LinkedIn post — Dog Years, Properly

Companion page: `dog-years.html` — a poster card (screenshot for the image) PLUS
a live interactive "how old is your dog?" calculator below it. Answers the
user's earlier question ("can we make a calculator people can change?"): LinkedIn
can't embed one, but the page on your own site can, and the post drives traffic
to it.

Why this one: pet-focused, so zero overlap with the author's livestock work AND
zero country/market angle (the Poland-market concern that ruled out the
antibiotic ranking). Peer-reviewed science, universally shareable, warm topic.

---

## Post copy (EN)

🐕 Quick one that surprises almost everyone: your dog is significantly older than the "multiply by 7" rule says.

That rule was never science. In 2020, researchers at UC San Diego did something better — they read the chemical marks that accumulate on DNA over a lifetime (the "epigenetic clock") in dogs and in humans, and matched them up.

The result isn't a straight line. Dogs race through early life, then age slowly:

🔵 1-year-old dog → about 31 human years
🔵 4 years → about 53
🔵 7 years → about 62
🔵 15 years → about 74

So a "×7" 1-year-old should be 7. In reality it's already a young adult of ~31. And that same rule overshoots wildly at the other end.

The formula, if you like the maths: human age = 16 × ln(dog age) + 31.

Here's why this is more than a fun fact — it's a care calendar:

▪️ A puppy compresses three human decades into its first year. That's why the early decisions — vaccination, nutrition, socialisation, neutering timing — carry so much weight so fast.
▪️ A 7-year-old dog is already ~62 in human terms. Senior wellness screening should start earlier than most owners think to ask for it.

I built a little slider so you can check your own dog — link in the comments. 👇

What's your dog's age… and how old did it turn out to be? 🐾

Source: Wang et al., "Quantitative Translation of Dog-to-Human Aging," Cell Systems, 2020 (UC San Diego).

#PetHealth #Dogs #VeterinaryMedicine #AnimalHealth #PetCare #OneHealth #DogsOfLinkedIn #Science #Data

**First comment (post immediately after publishing):**
🐶 Check your own dog here: https://namikakmandev.github.io/dog-years.html
Drag the slider — it shows the science-based age, the old "×7" guess, and the life stage.

---

## Publishing the interactive part on LinkedIn

LinkedIn does **not** run interactive code in a post — no embedded widgets,
sliders or iframes, in feed posts or in articles. Three ways to deliver the
feeling of interactivity, in order of effectiveness:

1. **Video of the slider moving (BUILT — use this).**
   `assets/dog-years-reel.mp4` — 1080×1350, 17 s, H.264, ~1.2 MB, no audio.
   Video autoplays silently in the feed, so the numbers visibly animate as the
   age sweeps 2 months → 1 yr → 7 yr → 14 yr. Re-record any time from
   `dog-years-reel.html` (see command below). Post this as the media, with the
   calculator link in the first comment.
2. **Carousel / document post.** Upload a PDF; each swipe is a page (e.g. one
   page per dog age). LinkedIn favours document posts for dwell time. Slower to
   make, and the reader picks from fixed pages rather than any value.
3. **Static poster + link in comments.** The baseline — `dog-years.html`
   screenshot as the image, real calculator one tap away on the site.

Re-record the video (needs playwright + ffmpeg-static):

```bash
# 1. record the animation at 1080x1350
node -e "const{chromium}=require('playwright');(async()=>{
  const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});
  const c=await b.newContext({viewport:{width:1080,height:1350},
    recordVideo:{dir:'vid',size:{width:1080,height:1350}}});
  const p=await c.newPage();
  await p.goto('file://<repo>/dog-years-reel.html');
  await p.evaluate(()=>window.__reelDone); await c.close(); await b.close();})()"
# 2. transcode to LinkedIn-ready MP4
ffmpeg -y -i vid/*.webm -vf "fps=30,format=yuv420p" -c:v libx264 \
  -preset slow -crf 20 -movflags +faststart -an assets/dog-years-reel.mp4
```

**Important:** the calculator link only works once this branch is merged into
`main` — GitHub Pages serves the default branch. Merge, load
https://namikakmandev.github.io/dog-years.html once to confirm, then post.

## Integrity / accuracy notes

- Formula is verbatim from the peer-reviewed paper: human = 16·ln(dog) + 31
  (Wang et al., Cell Systems 11(2), 2020). Verified via search against the
  publisher (cell.com), UC San Diego, NHGRI and NIA coverage — consistent
  everywhere. Spot values: ln(1)=0 → 31; ln(7)=1.946 → 62.1; ln(15)=2.708 → 74.3.
- Stated limits on the artifact: single-breed (Labrador) derivation, so no
  breed-size adjustment; large breeds age faster. Undefined below ~1 month.
- The "×7" rule is correctly described as having no scientific basis.
- Life-stage bands in the calculator are an illustrative overlay, not from the
  paper — kept qualitative ("young adult", "senior") so no false precision.

## Design notes

- Poster is the screenshot target (4:5). The interactive calculator sits in a
  SEPARATE card below, deliberately outside the screenshot crop, so it lives on
  the site for the "link in comments" CTA.
- Two series (science curve vs myth line): the myth line is dashed, so identity
  survives colour-blindness (secondary encoding), and both are direct-labelled.
  Palette (blue #3987e5 / orange #d95926) passes the dataviz validator on dark.

## Series plan (updated)

1. **Dog Years, Properly** (this one) — pet, safe everywhere, has the calculator.
2. **Discount breakeven** — pricing craft, evergreen filler.
3. **Antibiotic Gap** — SHELVED: names Poland among high-users, and the author
   serves the Polish market. Do not publish.
4. **Vet Spend Index** — hold until after the internal meeting, then ask.
