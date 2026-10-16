# The AI boom stopped paying for itself — LinkedIn assets

Post on the hyperscalers' cash: operating cash flow against capital
expenditure in each company's latest reported quarter, as of 16 October 2026.

## What to upload

**One file: `notes/tech-scalers-post.mp4`**, a 48-second silent video, 4:5
(1080×1350), with the copy below as the body. Nine beats: the hook, the
arithmetic (cash in, minus capex, equals free cash flow), one card per company
with both bars on one $0 to $60B scale and the free cash flow figure, a
four-row summary around zero, the 2026 estimate for all five hyperscalers
against their operating cash flow with the financing that fills the gap, and
the closing two sentences with the source line.

It is silent by design: LinkedIn autoplays muted and every figure is on
screen. Rebuild it with:

```
node scripts/render_canvas_film.js film/tech-scalers.html notes/tech-scalers-post.mp4
```

The scene is `film/tech-scalers.html`, a deterministic canvas animation
(`window.__seek(t)` draws any frame). Open it in a browser and press space to
preview. Its figures are typed in the `CO` block at the top of the script;
change them there and re-render. `--stills 3.5,15.5 <dir>` writes PNG frames
for a check, and any of those frames works as a static image post. Fonts:
Inter and Inter Display, the only families installed on the render machine.

**One link in the body, if any:** none. The post stands on company filings.

---

## Before posting

- [ ] **The draft had Microsoft and Alphabet swapped.** The figures the draft
      gave for Microsoft ($39B in, ~$45B out, FCF –$5.9B, first negative quarter)
      are Alphabet's for April–June 2026. Microsoft's June quarter was
      $55.4B in, $35.8B out, FCF +$19.6B. The draft's Alphabet line ($1.75B,
      down from $9B) matches no filing. The copy below is corrected; the
      headline "three of four" survives, the names did not.
- [ ] **Say which quarter.** The four quarters are not the same calendar
      quarter: Alphabet, Amazon and Microsoft report April–June 2026, Oracle
      reports June–August 2026 (its fiscal Q1 2027). The copy names the months
      so nobody has to ask.
- [ ] **Microsoft's "capex" is two numbers.** Microsoft reports capital
      expenditure including finance leases ($41.0B) and cash paid for property
      and equipment ($35.8B). Its own free cash flow uses the cash figure, so
      the copy does too. If a comment quotes $41B, both are right.
- [ ] **Oracle's cash in is not all operations.** $11.4B of its $23.1B
      operating cash flow was customer prepayments with a significant financing
      component. Without them the quarter would be roughly $11.7B in against
      $28.5B out. The copy says so in half a line.
- [ ] **The 2026 total is an estimate, and the draft's range was low.** The
      draft said $700–750 billion. Current estimates for the five hyperscalers
      (the four above plus Meta) run $768B (AllianceBernstein, June), about
      $800B (Goldman Sachs and Morgan Stanley, September–October) and $820B
      (UBP, September, against roughly $750B of operating cash flow). The copy
      says "roughly $800 billion" and "about equal to their operating cash
      flow", which is what Bank of America also finds (capex near 100% of
      operating cash flow in 2026, from about 70% in 2025).
- [ ] **"First negative quarter" is a press claim for Alphabet.** Alphabet's
      own trended table only goes back to Q3 2024. The Globe and Mail (11 Oct
      2026) and others call it the first since the 2004 listing. Say "since it
      listed in 2004" rather than "ever", and be ready to concede the point if
      someone finds an earlier one.
- [ ] Microsoft reports its July–September quarter in late October 2026. If
      the post goes out after that, re-check the Microsoft line.
- [ ] Check your employer's external communications policy.

---

## Post copy (corrected, ~230 words)

The AI boom just stopped paying for itself.

For two decades, big tech ran on a simple formula: the core business threw off so much cash that even enormous investments left billions in free cash flow. That era is ending this year.

Free cash flow, what is left of operating cash flow after capital expenditure, has turned negative at three of the four biggest data-centre investors in their latest reported quarters:

Alphabet (Apr–Jun 2026): $39.1B operating cash flow, $44.9B capex. FCF –$5.9B, its first negative quarter since it listed in 2004.

Amazon (Apr–Jun 2026): $45.4B in, $54.2B out. FCF –$8.8B, alongside $13.6B of new long-term debt in the quarter.

Oracle (Jun–Aug 2026): $23.1B in, $28.5B out. FCF –$5.4B, the fifth negative quarter in a row. Half the cash in was customer prepayments.

Microsoft (Apr–Jun 2026) is the exception: $55.4B in, $35.8B out, FCF +$19.6B, down 23% on a year earlier.

Across the five hyperscalers (these four plus Meta), 2026 capital spending is estimated at roughly $800 billion, about equal to their operating cash flow. The gap is being closed with new debt and equity, not cash from operations: in one quarter Alphabet raised $49.6B of equity and $20.3B of bonds, and Oracle sold $19.9B of stock.

That changes the risk profile. A self-funded buildout can slow down quietly. A leveraged one needs the AI revenue to actually show up, on a schedule.

Worth watching which happens first.

#AI #CapEx #FreeCashFlow

---

## Figure check (16 October 2026)

Every number in the copy, against the company's own filing or earnings
material. FCF = net cash from operating activities less cash paid for
property and equipment, each company's own definition.

| Company | Quarter | Operating cash flow | Capex (cash) | FCF | Draft said | Source |
|---|---|---|---|---|---|---|
| Alphabet | Apr–Jun 2026 (Q2 2026) | $39,069M | $44,924M | –$5,855M | attributed to Microsoft | Q2 2026 10-Q (filed 23 Jul 2026); earnings slides, trended FCF table |
| Amazon | Apr–Jun 2026 (Q2 2026) | $45,387M | $54,208M | –$8,821M | $45B / $54B / –$8.8B ✓ | SEC EDGAR XBRL, NetCashProvidedByUsedInOperatingActivities and PaymentsToAcquireProductiveAssets; long-term debt proceeds $13,557M (ProceedsFromIssuanceOfLongTermDebt) |
| Oracle | Jun–Aug 2026 (fiscal Q1 2027) | $23,103M | $28,499M | –$5,396M | $23B / $28.5B / –$5.4B ✓ | Q1 FY2027 10-Q (filed 11 Sep 2026), free cash flow reconciliation; SEC EDGAR XBRL agrees |
| Microsoft | Apr–Jun 2026 (fiscal Q4 2026) | $55,441M | $35,802M | +$19,639M | $1.75B, "down from $9B" ✗ | Q4 FY2026 earnings slides, cash flow reconciliation; capex incl. finance leases $41.0B |

Oracle's five negative quarters, from its Q1 FY2027 release: FY26 Q1 –$362M,
Q2 –$9,967M, Q3 –$11,484M, Q4 –$1,873M, FY27 Q1 –$5,396M. Its operating cash
flow includes $11,363M of customer prepayments with a significant financing
component (10-Q cash flow statement). Financing that quarter: $19,909M net
from the at-the-market stock programme.

Alphabet's trended table (Q3 2024 to Q2 2026, in $M): FCF 17,637 · 24,837 ·
18,953 · 5,301 · 24,461 · 24,551 · 10,116 · –5,855. Year-earlier quarter was
+$5,301M, not the draft's $9B. In June 2026 it issued stock and mandatory
convertible preferred for $49.6B net and senior notes for $20.3B net; long-term
debt stood at $98.2B at 30 June 2026 against about $16B a year earlier (CFO on
the Q2 call).

Microsoft reports capital expenditure two ways: $41.0B including finance
leases ($5.6B), $35.8B cash paid for property and equipment. Its FY2026 cash
from operations was $182.9B against $115.9B of property and equipment payments
(SEC EDGAR XBRL, fiscal year to June 2026). It guided to remaining free cash
flow positive in FY2027.

2026 group capex estimates (Microsoft, Amazon, Alphabet, Meta, Oracle):
$768B AllianceBernstein (29 Jun 2026); about $800B Goldman Sachs (via
Bloomberg, 25 Sep 2026) and Morgan Stanley (16 Oct 2026); $820B against about
$750B operating cash flow, UBP (16 Sep 2026). Bank of America: capex about 70%
of operating cash flow in 2025, near 100% in 2026 (1 Jul 2026). S&P Global
Ratings expects all of them plus SpaceX to run negative free operating cash
flow in 2026 and 2027 (21 Sep 2026).

Where the numbers came from: the Econ Data server's `sec` provider (EDGAR
XBRL company facts) for Amazon, Oracle and Microsoft's fiscal year; the
Bigdata.com filings and transcript index for the June-quarter figures that
EDGAR's quarterly derivation does not carry (Alphabet Q2, Microsoft fiscal Q4)
and for the estimates. Direct access to data.sec.gov is blocked from the
sandbox.

---

## The original draft, for the record

The draft as prepared in chat on 16 October 2026 read, in its figures
paragraph: "Microsoft: $39B operating cash flow, ~$45B capex. FCF –$5.9B, its
first negative quarter. Amazon: $45B in, $54B out. FCF –$8.8B, alongside $10B+
in new long-term debt. Oracle: $23B in, $28.5B out. FCF –$5.4B, the fifth
consecutive negative quarter. Alphabet is still positive, but barely: $1.75B,
down from $9B a year ago. In total, the hyperscalers are putting an estimated
$700–750 billion into AI infrastructure in 2026 — in some cases more than 90%
of their operating cash flow."

Changed: Microsoft and Alphabet lines (swapped and corrected), quarter named
on every line, the Oracle prepayment caveat, the 2026 total raised to the
current estimate range, the "90%" replaced by the group-level comparison, and
the Alphabet and Oracle financing figures added as the evidence for "closed
with new debt and equity". Everything else is the draft's wording.
