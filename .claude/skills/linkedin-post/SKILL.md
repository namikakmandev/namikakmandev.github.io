---
name: linkedin-post
description: How to turn a data finding into a LinkedIn post that gets liked, shared and argued over, the way the best data posts on the feed do. Use this whenever a post, carousel, chart image, video or caption for LinkedIn is being drafted, reviewed or rebuilt, whenever someone asks "what should I post", "make this a post", "write the copy", "is this post good", or pastes a post draft, even if they do not say LinkedIn. Also use it before building any image, deck or video whose destination is a social feed, because the format decides most of the reach before a word is written.
---

# LinkedIn posts that travel

The reference point is a post that did 1,397 likes, 102 comments and 41
reposts on a Tuesday feed: "Anthropic vs SaaS", one image, two bar charts,
four numbers. It is dissected in `references/anatomy-of-a-hit.md`, with the
screenshot in `assets/`. Read that file once; everything below is the method
distilled from it and from the twelve posts already in `notes/`.

The thing to hold on to: **a post is one comparison that makes a sceptic want
to argue, drawn so it can be read in two seconds with the sound off.** Every
rule below serves that sentence.

## 1. Find the one comparison

Before any chart or copy, write the claim as one sentence with two numbers:

> Anthropic is worth more than 35 SaaS companies combined, on a quarter of
> their revenue.

> Three of the four biggest data-centre builders spent more cash than they
> made last quarter.

Tests the sentence has to pass:

- **Someone wants to argue with it.** "That's not fair, SaaS is mature" is the
  comment thread that carried the example to 102 comments. If the claim is
  merely true, it is a report. If it is true and provocative, it is a post.
- **It has an underdog or a villain**, named. "Hyperscalers" is abstract;
  "Alphabet's first negative quarter since 2004" is a character.
- **It is tied to this week.** An IPO filing, an earnings release, a rate
  decision. The example opens with "Anthropic is preparing for an IPO". A
  timeless finding needs a timely peg or it waits for one.
- **The two numbers are the same kind of thing**, so the contrast is honest.
  Market cap against market cap, revenue against revenue, never a stock
  against a flow in one bar. If the honest comparison is less dramatic than
  the dishonest one, post the honest one and say so; the comment thread will
  find the other version anyway.

If the finding does not survive these four, it is content for `explore.html`
or a note, not a post. Posting it anyway costs the next post's reach.

## 2. Verify before anything is drawn

Run the `data-integrity` skill's checklist on both numbers. The one incident
this repository has: a draft that carried Alphabet's quarter under Microsoft's
name, with a Microsoft line that matched no filing at all. It read fluently.
It would have been corrected in the comments by the second reply.

- Company figures come from the filing (the Econ Data server's `sec`
  provider, or the 10-Q via Bigdata.com), never from a news paragraph.
- Name the period on every figure. Oracle's quarter ends in August when the
  others end in June; say so once, in small type, on the image.
- Write the figure check into the post's note (template below). Every number
  in the image and the copy sits in that table with its source.

## 3. The image carries the post

On the feed the image is seen by everyone and the text by a fifth of them. So
the finding lives in the image, and the text is the caption. Build it like
the example:

- **Headline inside the image, enormous**: "Anthropic vs SaaS" at a size that
  reads as a thumbnail. Below it, the finding as one sentence with the
  numbers. The text above the image is not where the claim lives.
- **One chart, at most five numbers.** The example has four: $2.0T, $948B,
  $53.4B, $11.5B. A chart with eight numbers is a slide, not a post. If the
  data is four companies with two bars each, show the four results, not the
  eight inputs; the inputs go in the note and in the first comment.
- **Two panels of the same thing, flipped**, is the strongest shape: left the
  measure where the subject wins, right the measure where it loses, same
  companies in both. The reader does the arithmetic and feels clever.
- **Logos or names as the texture.** A stacked bar made of company logos is a
  "find yours" game: people zoom, tag colleagues, comment "we're in there".
  Where logos are not available, the names in a readable size do most of it.
- **Numbers on the bar ends only.** No gridline labels, no axis titles if the
  bars are labelled. Recessive grid, thin marks, one accent colour against
  neutral; the `dataviz` skill has the palette and the mark specs.
- **A creator strip at the bottom**: handle, site. The example's
  "@SergeyCYW · SergeyCYW.substack.com" travels with every screenshot and
  repost. Use `namikakmandev.github.io` and the LinkedIn handle.
- **A source line in small type**: publisher and period. It is what lets the
  post survive the first hostile comment.
- **Format: a single image, 4:5 or 1:1**, 1080 wide or more. 4:5 (1080×1350)
  takes the most feed height. Landscape 1600×1000, the older convention in
  `assets/linkedin/`, loses a third of the screen on phones. Build with the
  existing tools: an SVG rendered through `scripts/fte_chart.py`'s
  `render_png`, or a canvas scene through `scripts/render_canvas_film.js
  --stills` (which gives any frame as a PNG at 1080×1350).

**Which format when.** A single image for reach: it autoplays nothing, zooms,
and is reposted whole. A document (PDF carousel) when there are three or more
distinct charts, because saves and dwell time reward it, and the repo's
carousel scripts already make them. Video last, and only for a story with
motion in it: LinkedIn autoplays muted, a chart cannot be zoomed, and a
63-second film of four bars is a four-bar image that takes a minute to read.

## 4. The copy is a caption, not the argument

- **First line under twelve words, with the number or the name in it.** It is
  the only line shown before "…more", so it is the whole text for most
  readers. "Anthropic is preparing for an IPO. Its revenue reached $4.73B…"
  is the example's; it names the peg and a number and stops.
- **Under 150 words total.** Numbers as digits, one idea per line, blank lines
  between them. Icons at the start of lines are fine as bullets (🔴 🟢 📉); not
  mid-sentence, not as decoration.
- **Say what the chart does not**: the caveat the pedant will raise (Oracle's
  fiscal calendar, finance leases in Microsoft's capex) in one clause, so the
  correction never gets to be the top comment.
- **End with the open question**, not the conclusion. "Worth watching which
  happens first" invites agreement; "Which side of the bar is your company
  on?" invites a comment. Comments in the first hour decide the reach.
- **No external link in the body.** LinkedIn throttles posts that lead off
  the platform. The chart link, the note, the data page go in the first
  comment, posted right after.
- **Three hashtags at most**, specific ones. Hashtags are not reach any more;
  they are a mild topic signal.

Hooks that have worked in this repository, for the register: "In 1986, The
Economist invented an economic indicator as a joke." "Did meat get
expensive, or did everything?" "Who insures the herd? Two schemes, two
continents, one pattern." A date, a question, or a quoted claim about to be
tested.

## 5. The note that goes with every post

Every post gets `notes/<slug>-linkedin-post.md`, from
`assets/post-note-template.md`. It is the record the comments get answered
from: what to upload, the before-posting checklist with the pedant's
objections already written, the copy, the figure check with sources, and the
rebuild command. The image and any carousel or video sit next to it under
`notes/` or `assets/linkedin/`.

## 6. Before posting, score it

Ten checks. Fewer than eight passes means it is not ready, whatever the
deadline.

| # | Check | Pass when |
|---|---|---|
| 1 | One sentence, two numbers | The claim fits one line and someone would dispute it |
| 2 | Timely peg | The first line names something from this week or this quarter |
| 3 | Verified | Every figure in the image and copy is in the note's figure check with a filing or dataset as source |
| 4 | Periods named | Every number carries its quarter or year somewhere on the image |
| 5 | Headline in the image | Readable as a 300px thumbnail |
| 6 | Five numbers or fewer on the image | Count them |
| 7 | Feed format | Single image 4:5 or 1:1, or a PDF carousel; video only with motion in the story |
| 8 | First line | Under twelve words, contains a number or a name |
| 9 | Copy under 150 words, no link in the body | Link in the first comment |
| 10 | The pedant's line | The main caveat is in the copy or on the image |

## 7. After posting

Reply to every comment in the first hour, with a number where possible; a
reply is a second post to the commenter's network. Post the first comment
with the link and the figure table immediately. Repost nothing of your own
for 24 hours. Post Tuesday to Thursday, 08:00 to 10:00 in the audience's
time zone; the example went up on a Tuesday morning CET. Record the result
(likes, comments, reposts at 24 h and at 7 days) at the bottom of the note so
the next post learns from it.
