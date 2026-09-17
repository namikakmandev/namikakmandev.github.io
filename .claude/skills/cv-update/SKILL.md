---
name: cv-update
description: Tailors Namık Akman's CV to a job posting and judges the fit. Use when asked whether a job is a good match, to update, prepare or tailor the CV or resume for a posting, to write a motivation or cover letter, or to produce the CV as DOCX or PDF. The canonical CV facts live in this skill; never rebuild them from the portfolio site or from memory.
---

# CV updates

Every rule here comes from a session that went wrong. Read `master-cv.md` before
writing a word: it is the only trustworthy source of employers, titles, dates,
numbers and education. The portfolio site describes tools, not a career; Gmail
attachments cannot be downloaded through the connector; earlier sessions' files are
gone with their containers.

## 1. Facts are fixed, framing is not

- Never invent, estimate or "placeholder" a job, date, employer, figure or degree.
  If a fact is missing from `master-cv.md`, ask for it in one line and continue with
  everything else.
- Every job, bullet, number and date in `master-cv.md` stays verbatim unless the
  owner corrects it. Corrections go back into `master-cv.md` in the same commit.
- Tailoring touches only: headline, professional summary, core competencies (regroup
  and rename, do not add claims), the order of bullets inside a role, the portfolio
  section (pick and order, from the list in `master-cv.md`), and the order of the
  skills line. Adding a tool or platform to the skills line needs the owner's yes;
  say which ones were added when handing over.

## 2. Keep the domain: business leader who can build

The owner is a commercial transformation and execution-excellence leader in pharma
and animal health who happens to be technically able. Do not rewrite the CV as a
technical or engineering profile, whatever the posting asks for.

- Headline pattern: `Commercial Transformation & Execution Excellence Leader —
  Pharma / Animal Health · <short tag aimed at the posting>`. Change the tag, not
  the identity.
- Summary paragraph two is the tailoring paragraph. It leads with transformation
  and execution accountability (agenda, roadmaps, governance rhythms, KPI cadences,
  measured impact, the SAP S/4HANA workstream), then places the posting's theme as
  something the owner decides on and can build himself. Building is proof of
  ability, never the job.
- The words "consultant", "engineer", "developer", "data scientist" do not appear in
  the headline unless the owner asks.

## 3. Voice

The owner rejected a draft as "too AI". What passed: plain first person, short
sentences, one concrete example per claim, no stacked abstract nouns.

- Cut: "leverage", "drive", "orchestrate", "seamless", "cutting-edge", "passionate",
  "synergy", triads of adjectives, colon-plus-list sentences inside a paragraph.
- Keep: the specific tool, the specific number, the specific market.
- Read every summary sentence aloud; if it could be on any CV, rewrite it.

## 4. Workflow for a posting

1. Get the posting text. Workday, careers.ing.com and most job boards are blocked
   from the sandbox; `WebSearch` snippets give the outline, and the owner pastes the
   full text when asked. Do not guess requirements.
2. Score the fit before writing. One table: requirement, evidence from
   `master-cv.md`, fit (Strong / Medium / Weak). Give one honest number with the
   reasons that keep it below the next band. Seniority mismatch (the owner leads a
   cluster; many postings are individual-contributor roles) and missing sector
   experience are the recurring gaps, name them plainly.
3. Tailor per section 1 and 2. Put the draft where the owner can annotate: a Claude
   Doc via the docs connector (`anthropic-skills:docs`) when available, otherwise
   an HTML file sent with `SendUserFile`. Fold comments back into the same doc and
   into the DOCX/PDF.
4. Build the files with `scripts/build_cv.js` (section 5). Deliver DOCX and PDF with
   `SendUserFile`; name them `Namik_Akman_Resume_<Company>.docx/.pdf`.
5. Motivation letter only when asked or when the posting requires one. One page,
   same voice, answers "why this move from leading a commercial organisation" and
   "why this city" when relocation is involved.
6. Do not commit tailored CVs or contact details to this public repository.
   Files go to the scratchpad and to the owner. Only `master-cv.md` and the scripts
   live here, and `master-cv.md` carries no phone number on purpose.

## 5. Building DOCX and PDF

```bash
cd .claude/skills/cv-update/scripts && npm install docx --silent
node build_cv.js content.json out/Namik_Akman_Resume_Company   # writes .docx and .html
/opt/pw-browsers/chromium-1194/chrome-linux/chrome --headless=new --no-sandbox \
  --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=out/Namik_Akman_Resume_Company.pdf "file://$PWD/out/Namik_Akman_Resume_Company.html"
```

`content.json` follows `content.example.json` (same fields as `master-cv.md`, with
the tailored summary and competencies). LibreOffice is installed but refuses to
open files in the sandbox; Chromium is the PDF route. Check the page count with
`grep -c '/Type /Page' file.pdf` and the look with a Chromium `--screenshot`.
Two A4 pages is the target; three means cut, not shrink.

## 6. Version log

Keep `master-cv.md`'s log current: date, target company and role, what was
reframed. It lets the next session answer "what did we send Pfizer" without the
Gmail attachment.
