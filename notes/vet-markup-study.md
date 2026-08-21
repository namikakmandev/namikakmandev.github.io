# Veterinary / distributor markups in Europe — study plan (draft, under construction)

Proposed output: **what is publicly known about markups in the veterinary
medicines channel, country by country** — who is allowed to dispense, where
margins have actually been measured, and where nothing is published.

**Scope boundary: this is a separate work item from the PPP study**
(`notes/eu-ppp-study.md`). The two are assessed independently — no combined
metric. A country's general price level and its vet-channel markup are
different objects; nothing here gets divided or multiplied by a PLI.

## The honest starting point

There is **no public dataset of veterinarian or distributor markups by
country**. Vet-medicine prices and margins are unregulated in most of
Europe (Regulation (EU) 2019/6 harmonises authorisation and distribution,
not prices), so no PPRI-style database exists for them. Any "markup per
country" table would be fabricated. What CAN be built honestly:

1. **A dispensing-rights map (all 36 countries).** Who may sell veterinary
   medicines — vet, pharmacy, both, differs per country and per category
   (POM vs OTC, food-producing vs companion animals). This is documentable
   from legislation and FVE overviews, and it is the single biggest reason
   "vet markup" is not one comparable object across countries.
2. **Measured-margin case studies (few countries, non-comparable).**
   Presented as boxes, never as a league table.
3. **The gap itself as the finding**: no European body measures veterinary
   distribution margins; the UK needed a two-year market investigation to
   produce one country's numbers.

## What exists publicly (evidence inventory)

| Source | Covers | What it actually contains | Status |
|---|---|---|---|
| UK CMA vet services market investigation, final report Mar 2026 + remedies (by Sep 2026) | UK | the only deep public margin evidence: practice medicine margins, margin squeeze on independents, £21 prescription-fee cap | TO EXTRACT — pin every figure to a report paragraph |
| FVE VETsurvey 2015 / 2018 / 2023 | ~24 FVE member countries | profession income and financial indicators — NOT medicine markups; useful context only | TO EXTRACT |
| WHO PPRI / GÖG Pharma Price Information | ~30 countries | regulated wholesale + pharmacy markups for HUMAN medicines only | PROXY ONLY — usable solely where pharmacies dispense vet meds, limitation must travel with every number |
| France: wholesale market sizing (~€1.57bn, 2022); purchasing-group discounts reported at 30–50% off list | FR | distributor-layer fragments, not a measured markup | TO VERIFY against primary source before use |
| National legislation / FVE dispensing-rights overviews | all 36 | who may dispense, per country | TO COMPILE — this is the map in deliverable 1 |

Rows marked TO VERIFY/TO EXTRACT carry **no numbers into any chart** until
pinned to a primary source with page/paragraph reference.

## Structural context datasets (fetched and verified 2026-08-20)

Committed via the standard pipeline — industry structure, not markups; they
size the channel, they do not measure a margin:

- **`data/eu-vet-sbs.json`** — Eurostat SBS, veterinary activities (NACE
  M75): enterprises, turnover, value added, persons employed, turnover per
  person, 39 geos, **2005–2020**. Legacy SBS series ends 2020; 2021+ needs
  the successor EBS dataset (open hunt). Sanity: DE 2020 = 10,652
  enterprises, €4.66bn turnover, 55,349 employed; EU-27 = 80,000
  enterprises.
- **`data/eu-vet-weight.json`** — HICP item weights CP0934 (pets and
  related products) + CP0935 (veterinary and other services for pets),
  per-mille of the consumption basket, 43 geos, **1996–2025**. 2025 vet+pet
  services weight: FR 5.49‰ (highest), EU-27 2.88‰, DE 2.61‰. **Türkiye
  transmits no CP0934/CP0935 weight at all** — a real gap, not an
  oversight. No 2026 in the dataset yet (ECOICOP2 rebase; successor to
  watch).

## Built output

`vet-sector.html` — interactive explorer over the two structural datasets,
listed on projects.html (card image `assets/vet-sector.png`). Three views:
basket-weight ranking (‰, EU-27 reference marker), industry structure
(absolutes labelled size-dependent; published and derived ratios labelled
as such, per-row reference years), and weight-over-time small multiples
with the EU-27 as a dashed reference line. Transmitted zero weights
(IE some years, XK throughout) render as "not reported", never as zero.
Each view carries its own metric definition box stating what the metric is
NOT (no prices, no margins). Shared mini-flags moved to `js/vet-flags.js`.

`vet-dispensing.html` — the dispensing-rights map below rendered as an
interactive page (card image `assets/vet-dispensing.png`): Europe map
colored by retail channel (vet practice sells / pharmacy channel sells /
prohibited for vets / to verify — three hues validated all-pairs against
the dark surface with the dataviz checker, plus neutral gray; the Italy
hatch was removed 2026-08-21 when D.Lgs. 218/2023 settled its
classification as pharmacy-led), a grouped
country list with TO VERIFY badges, a per-country detail panel quoting
the rule and its named source, and a full table view. States its own
limits: a legal map, not a metric; no margin sizes in the map itself;
LU/IS/CY/MT not compiled; Kosovo present in list and table but absent
from the basemap. Below the map, a **"one measured market" section**
(added 2026-08-21) charts the CMA's UK mark-up evidence on a single
% -of-manufacturer-list-price axis: what practices pay after rebates
(LVG ≈50, buying-group 50–60, unaffiliated 70–80) left of the list-price
line, what owners pay at the counter (150–200 LVG, 150–160 independent)
right of it — every bar a CMA-reported range (final Part A ¶11.201,
¶11.203), UK-only and labelled as such.

`vet-story.html` — the suite's master chart (card
`assets/vet-story.png`): one row per country, four separate facts side
by side, never combined into a score — PLI (GDP, 2024), vet & pet HICP
weight (‰, 2025), the **vet-price gap** (CP0935 vs CP00, both rebased
Jan 2020, derived and labelled; per-country end month — IE to 2023-12),
and the dispensing-channel chip linking to vet-dispensing.html. UK row
carries the CMA 100–400% badge. Sortable per column; dashes are "not
published" (TR no vet CPI; UK left HICP 2020; XK nearly empty;
IS/CY/MT/LU not in the dispensing map). The gap column's definition box
states it is consistent-with, not proof-of, pricing power, and points
out that the gap does NOT sort by channel model (decoupled SE high,
vet-banned ES low, but coupled FR/IE low too). Gap range at build:
BG +41% … EL −11%, EA20 +1.2%, sanity-checked in-session against the
raw series before publishing.

## Dispensing-rights map — fill rules

- One row per country; columns: may vets dispense? may pharmacies? online
  sale allowed? source (law or FVE doc + year).
- Every cell sourced or left blank — a blank cell is a finding ("not
  documented"), a guessed cell is a fabrication.
- First sourced rows (research pass 2026-08-20). Every claim below has a
  named source; unlisted countries remain TO COMPILE, not assumed.

| Country | May vets sell/supply meds? | Pharmacy role | Source |
|---|---|---|---|
| UK | YES — vets prescribe AND supply POM-V (coupled); SQPs limited to POM-VPS | pharmacies dispense POM-V against a vet's prescription | RCVS supporting guidance ch. 4 (rcvs.org.uk) + VMD guidance |
| France | YES — vets may dispense, without holding an open pharmacy, for animals under their care ("ayants droit") | pharmacies dispense too (dual channel) | Code de la santé publique art. L5143-2 (Légifrance) + Ordre national des vétérinaires, fiche "Délivrance" |
| Germany | YES — Dispensierrecht via the tierärztliche Hausapotheke (practice pharmacy, TÄHAV rules) | pharmacies a minor channel for vet meds | Bundestierärztekammer, "Das tierärztliche Dispensierrecht" (bundestieraerztekammer.de PDF) |
| Denmark | NO — prescribing and dispensing decoupled since the early 1990s; vets may not profit on medicine sales; limited hand-over from pharmacy-sourced stock | pharmacy-only distribution | Danish Veterinary and Food Administration (en.foedevarestyrelsen.dk, "Distribution and use of veterinary medicinal products"); AASV summary of Danish controls |
| Sweden | NO — therapeutic vet medicines incl. medicated feed dispensed through pharmacies only | pharmacy-only | Grave et al., Prev. Vet. Med. (2006), DK/NO/SE antimicrobial-use study (ScienceDirect S0167587706000559) |
| Norway | NO — same Nordic model: therapeutic vet medicines dispensed through pharmacies | pharmacy-only | same Grave et al. (2006) study, which covers DK, NO and SE |
| Türkiye | YES — vet clinics/polyclinics may hold and sell vet medicinal products under a retail-sale permit; sale outside authorised retail points prohibited; even own-treatment stock requires the permit | pharmacies are also authorised retail points | Veteriner Tıbbi Ürünler Hakkında Yönetmelik (mevzuat.gov.tr no. 15651); TVHB/İVHO guidance on illegal online sales |
| Poland | YES — retail of prescription vet medicines only through veterinary treatment facilities (zakład leczniczy dla zwierząt); vet supplies meds together with the service | pet shops etc. may sell OTC only (Prawo farmaceutyczne art. 71(1a)) | Główny Inspektorat Weterynarii, "Farmacja weterynaryjna" (wetgiw.gov.pl); Prawo farmaceutyczne; Vetpol guidance |
| Spain | **NO — prohibited.** Vets in clinical practice may not sell or dispense; they may only administer from a practice stock acquired via authorised channels ("cesión") | dispensing via pharmacies, authorised retailers (comerciales detallistas) and livestock entities (ADS) | Real Decreto 666/2023 (BOE-A-2023-16727); Consejo General de Colegios Veterinarios summary; MAPA Q&A on distribution/prescription/dispensing (mapa.gob.es) |
| Italy | PHARMACY-LED WITH LIMITED VET HAND-OVER — **verified 2026-08-21, replaces the earlier "likely prohibited" secondary claim**: under D.Lgs. 218/2023 (implementing Reg. (EU) 2019/6, in force 18 Jan 2024) retail sale is carried out by a pharmacist in pharmacies and in authorised commercial establishments, under the responsibility of a person registered with the Order of Pharmacists; but art. 37 lets the vet hand over medicines from their own stock to the animal's owner/keeper to START or CONTINUE the prescribed therapy, with traceability duties | pharmacies + authorised outlets (pharmacist-responsible); pharmacists may split packs to the minimum treatment quantity | D.Lgs. 7.12.2023 n. 218 art. 37 (edizionieuropee.it consolidated text; Federfarma and Ordine dei Farmacisti summaries; FNOVI FAQ) |
| Netherlands | YES — every registered vet holds a retail licence by law ("apotheekhoudende dierenarts"); may dispense only to clients whose animals are under their care; trading beyond own clients requires a separate licence. UDD class = vet-administered only | pharmacies dispense URA products on a vet's prescription | KNMvD kennisbank "Aan wie mag een dierenarts diergeneesmiddelen afleveren?"; CBG-MEB "Afleverstatus"; RVO diergeneesmiddelen page |
| Belgium | YES — vets keep one registered medicines depot (dépôt/depot, numbered by the agency) and may supply ("fourniture/verschaffing") medicines to owners of animals under their care, quantity limited to the treatment | pharmacies dispense too | AFMPS/FAGG pages "Dépôt de médicaments pour les médecins vétérinaires" and "Fourniture de médicaments au responsable d'animaux" (afmps.be / fagg.be) |
| Austria | YES — tierärztliche Hausapotheke under the Tierarzneimittelgesetz (TAMG); dispensing only to keepers of animals under the vet's treatment; opening notified to the district authority; chamber-supervised | public pharmacies a parallel channel | Österreichische Tierärztekammer, Berufsleitfaden "Tierärztliche Hausapotheke"; TAMG (ris.bka.gv.at); Apothekerkammer TAKG/TAMG merkblatt |
| Czechia | YES — vets are authorised to dispense (výdej) veterinary medicinal products alongside pharmacists; sellers of reserved (OTC-class) products register with ÚSKVBL | pharmacies dispense too | Medicines Act 378/2007 Sb.; ÚSKVBL seller register (uskvbl.cz); VFU teaching materials on léčiva |
| Hungary | YES — **pinned 2026-08-21**: the treating vet may supply the medicine personally from their own pre-purchased stock in the course of treatment (no separate prescription needed when dispensing from own stock); outside that, registered products may be dispensed only by or under the supervision of a vet or pharmacist; OTC without prescription limited to products with no antibiotics/psychotropics/euthanasia agents | vet pharmacies (állatgyógyszertár) and pharmacies the retail channel alongside practice supply | 128/2009. (X. 6.) FVM rendelet (net.jogtar.hu); Nébih GYIK "Állatgyógyászati termékek" (portal.nebih.gov.hu) |
| Romania | CHANNEL-SPLIT, VET-RUN PHARMACIES — retail runs through ANSVSA-authorised veterinary pharmacies and pharmaceutical points; **ownership nuance resolved 2026-08-21**: in a farmacie veterinară the titular is a veterinary physician (vet-run, may employ other vets and staff); puncte farmaceutice sell non-prescription products only; distributors may supply only authorised pharmacies, points, and authorised vet cabinets/clinics (the latter for their practice) | the authorised vet-pharmacy network IS the channel; online sale only for non-prescription via registered retailers | ANSVSA "Activitate farmaceutică"; Ordin ANSVSA 83/2014 (cmvro.ro copy); Norma sanitară veterinară 2006/2008 (lege5.ro) |
| Switzerland | YES — vets may run a "tierärztliche Privatapotheke" for their own clients; needs professional-practice AND retail-trade authorisation; cantons inspect | pharmacies and some specialist shops sell defined categories | TAMV (Tierarzneimittelverordnung); BLV "Verschreibung, Abgabe und Anwendung" (blv.admin.ch); canton Zürich licensing page |
| Ireland | YES — vets supply POM to animals under their care; classes route supply to vet / pharmacist / licensed retailer (LR) / registered CAM outlets | pharmacies + DAFM-licensed retailers; internet sale only via DAFM-registered suppliers | HPRA "Classification of veterinary medicines in Ireland"; Veterinary Medicinal Products Act 2023; DAFM internet-supply list |
| Finland | **YES BUT AT COST — zero profit.** Vets may hand over (luovuttaa) medicines only for treatment needs and must charge exactly their own purchase price; economic profit on medicine sales is prohibited | pharmacies the normal retail channel | Animal Medication Act 387/2014; MMM regulation 17/2014; Ruokavirasto Q&A "Lääkkeiden hankkiminen ja hinnoittelu" |
| Portugal | CHANNEL-SPLIT WITH CEDÊNCIA — dispensing entities are pharmacies and DGAV-authorised retail sale points (postos de venda); **ceding detail resolved 2026-08-21**: DL 148/2008 lets vets acquire medicines directly from manufacturers/importers/wholesalers when intended for administering to, or ceding to, animals under their care (art. 69-A also covers transport for daily clinical practice) — retail sale to the public stays with the authorised outlets | pharmacies + authorised retail points; simplified regime for non-POM outlets | Decreto-Lei 148/2008 (consolidated, diariodarepublica.pt); DGAV retail-sale pages incl. "Alteração das normas de venda a retalho" |
| Greece | YES (hybrid) — private vet clinics/production-animal vet offices may supply products to owners after issuing the prescription; dedicated vet-medicine retail shops require a licence AND a responsible scientist holding a veterinary degree | pharmacies may sell vet POM on prescription after notifying the regional veterinary service | minagric.gr vet-pharmaceuticals pages; national licence registry (mitos.gov.gr / EUGO, "Άδεια λιανικής πώλησης κτηνιατρικών φαρμακευτικών προϊόντων"); Kilkis pharmacists' association FAQ |
| Croatia | CHANNEL-SPLIT — retail only via authorised veterinary pharmacies (veterinarske ljekarne), per-location approval, national register kept by the veterinary directorate; distance sale only through registered ljekarne | the registered vet-pharmacy network IS the channel | Zakon o veterinarsko-medicinskim proizvodima (zakon.hr); Uprava za veterinarstvo "Veterinarske ljekarne" register (veterinarstvo.hr) |
| Slovakia | YES (dual) — pharmacies dispense vet medicines under their pharmacy-care permit; separately, retail sale of vet medicines (incl. distance sale) runs on a permit from the regional veterinary and food administration — the route vets use | pharmacies dispense too | zákon č. 362/2011 Z. z. o liekoch; ŠVPS "Farmácia" pages (svps.sk); mediPRÁVNIK analysis "výdaj lekárňou vs. maloobchodný predaj veterinárnymi lekármi" |
| Bulgaria | VET-STAFFED PHARMACIES — retail only via BFSA-licensed veterinary pharmacies; **the pharmacy manager and the persons selling must be veterinarians by law** | the licensed vet-pharmacy network IS the channel; BFSA controls wholesale + retail | Закон за ветеринарномедицинската дейност via BFSA (БАБХ) pages; bfsa.egov.bg licensing specimens; 1Legal.net summary of licensing requirements |
| Slovenia | YES (hybrid) — retail via pharmacies, licensed specialised outlets (specializirane prodajalne; responsible person must hold a vet or pharmacy degree), AND veterinary organisations performing veterinary activities | pharmacies + specialised outlets | ZZdr-2 art. 126; Pravilnik o specializiranih prodajalnah (Uradni list 2003); JAZMP retail-marketing pages |
| Estonia | LICENSED VET PHARMACY + VET HAND-OVER — the "veterinaarapteek" is a licensed pharmacy restricted to veterinary medicinal products; online sale only by licensed pharmacies. **Hand-over right resolved 2026-08-21**: the vet may issue (väljastada) medicines to the keeper of an animal they have examined, but only stock sourced from a wholesaler or pharmacy; OTC antiparasitics allowed without prior exam; hormonal (estrogen/androgen/gestagen) and prostaglandin products may not be handed to keepers | general + veterinary pharmacies | Medicinal Products Act; Riigi Teataja regulations on prescribing/dispensing in veterinary services (RT 128/06/2022 034) and on conditions of medicine use (RT 125/11/2021 003); Ravimiamet |
| Latvia | LICENSED VET PHARMACY — veterinary pharmaceutical activity needs a special permit/licence from the Food and Veterinary Service (PVD); prescription vet medicines reach the owner only against a practicing vet's prescription, with counselling by the issuer; a vet providing cross-border services may hand over only the minimum quantity to complete the treatment course. Domestic own-hand-over rule at statute level still TO VERIFY | licensed veterinary pharmacies | PVD "Veterināro zāļu aprites uzraudzība" (pvd.gov.lv); MK noteikumi on VMP labelling/distribution/control; Veterinārmedicīnas likums (likumi.lv) |
| Lithuania | LICENSED VET PHARMACY — **resolved 2026-08-21**: veterinary pharmacy licence holders sell to animal owners (prescription products only against a vet's prescription/request); wholesalers may also sell to owners against a prescription; the vet practice is not a named retail channel — vets prescribe, licence holders dispense | licensed veterinarijos vaistinės (and wholesalers against prescription) | Veterinarinių vaistų įstatymas implementing Reg. (EU) 2019/6 (e-seimas.lrs.lt); VMVT oversight |
| Serbia | YES via registered pharmacy — veterinarska apoteka is the registered retail entity; veterinary stations/clinics may retail vet medicines (excluding state-programme injectables, sera, vaccines and diagnostics) IF they register a veterinary pharmacy, with a licensed vet employed | registered veterinarske apoteke (often clinic-attached) | Zakon o veterinarstvu (paragraf.rs consolidated text) |
| Bosnia & Herzegovina | RETAIL VIA VETERINARSKE APOTEKE — registered under the veterinary law and inspected by the Federal inspection administration; qualified professional staff (stručni kadar) and prescription rules apply (inspectors have sanctioned dispensing without prescription / without qualified staff). Regulation is entity-split (FBiH / RS), so conditions can differ between the two entities | registered veterinarske apoteke | Zakon o veterinarstvu u BiH / FBiH (paragraf.ba; msb.gov.ba PDF); Federalna uprava za inspekcijske poslove enforcement notices |
| North Macedonia | LICENSED VET PHARMACY — a dedicated Закон за ветеринарно-медицински препарати governs VMPs separately from human medicines; the Food and Veterinary Agency (FVA/АХВ) licenses both wholesale (veterinary wholesalers) and retail (ветеринарни аптеки), each outlet approved after an Expert Commission facility inspection. Vets' own hand-over right TO VERIFY in the law text | FVA-licensed ветеринарни аптеки ARE the retail channel | Закон за ветеринарно-медицински препарати (fva.gov.mk); FVA "Одобрување на правни лица кои вршат промет со ВМП" |
| Montenegro | PHARMACY-ROUTE — veterinary medicines are regulated inside the single Zakon o ljekovima (Sl. list CG 14/26, human + vet in one act), administered by CInMED; the law counts a pharmacy supplying veterinary institutions under contract, for their patients, as retail trade. Nearly all VMPs imported — CInMED issued import consent for 260 vet medicines in 2025 and publishes the per-batch list. Vets' own hand-over right TO VERIFY | pharmacies + supply-to-veterinary-institutions route | Zakon o ljekovima 14/26 (cinmed.me PDF); CInMED annual report 2025 |
| Albania | LICENSED VET PHARMACY — **channel resolved 2026-08-21**: the national veterinary authority AKVMB publishes the official registers of licensed veterinary pharmacies (farmaci veterinare, with licence numbers) and pharmaceutical depots (wholesale) per regional veterinary service; products themselves trade only after State Commission approval under Law 10465/2011; an EU-2019/6-aligned VMP law is due in 2026. Vets' own hand-over right TO VERIFY | licensed farmaci veterinare (AKVMB register); depot wholesale tier | AKVMB "Farmaci dhe Depo Veterinare — listë me nr. licensimi" (akvmb.gov.al); Ligj 10465/2011; VKM 538/2009 licence categories; RTSH on the 2026 draft law |
| Kosovo | REGULATED, CHANNEL TO VERIFY — VMP marketing authorisation and pharmacovigilance run under Udhëzim Administrativ (MBPZHR) Nr. 12/2019 (successor to UA MA-Nr. 26/2006), with the Food and Veterinary Agency (AUV) as the veterinary authority; AKPPM licenses producers, wholesalers and retailers of medicinal products under Law 04/L-190 (RQLL central register carries the retail-pharmacy licence "Qarkullues Farmaceutik me Pakicë (Barnatore)"). Searched again 2026-08-21: no vet-specific retail licence located in public search; the RQLL register itself is unreachable from this environment — needs a direct register check. Which body licenses *veterinary* retail and whether vets dispense remains TO VERIFY | not yet documented | UA 26/2006 + UA (MBPZHR) 12/2019 (gzk.rks-gov.net); AUV legislation pages (auvk.rks-gov.net); AKPPM; RQLL (lejelicenca.rks-gov.net) |
Thirty-four rows — the map now covers every country on the study's list
except four small markets never compiled (LU, IS, CY, MT — TO COMPILE
only if a use appears).
Six distinct models after the 2026-08-21 verification pass: coupled (DE,
UK, PL, TR, NL, BE, AT, CZ, CH, IE, SK, EL, SI, RS, **HU — now pinned:
the treating vet supplies from own stock**) through dual-channel (FR),
decoupled (DK, SE, NO), **dispense-at-cost (FI — vets may hand over
medicines but only at their own purchase price, profit prohibited)**,
prohibited (**ES only — Italy reclassified**: D.Lgs. 218/2023 makes
retail pharmacist-led but art. 37 gives vets a start-or-continue-therapy
hand-over from own stock), and the licensed-vet-pharmacy channel (RO —
vet-run by law, HR, PT, BG — vet-staffed by law, EE, LV, LT, MK, BA,
**AL — now sourced via the AKVMB licence register**). ME routes through
general pharmacies under a single medicines act. The retail-margin actor
differs country by country, and in FI/DK/SE/NO/ES a vet medicine margin
is legally zero or non-existent. Remaining open points: XK retail
channel (public search exhausted — needs a direct RQLL/AUV register
check); LV domestic hand-over at statute level; MK/ME vets' own
hand-over rights.

## Case study: UK — CMA market investigation (final report 24 Mar 2026)

The only deep public margin evidence anywhere. Figures verified against
multiple summaries of the final report; pin to report paragraphs before
any figure enters a chart:

- Prescription fee cap: **£21** for the first medicine, **£12.50** per
  additional medicine in the same consultation (incl. VAT), raised from
  the £16 draft proposal; via CMA Order, remedies due implemented by
  23 Sep 2026. (Bird & Bird, Fieldfisher, Vet Times summaries of the
  final report; gov.uk case page: "Veterinary services for household
  pets".)
- **No medicine price control imposed** — the CMA relied on transparency
  remedies (tell owners medicines may be cheaper online, right to a
  written prescription) rather than capping medicine mark-ups, calling
  general price controls ill-suited to a multi-product clinical sector.
- Context finding: average vet service prices **+63% from Jan 2016 to
  Dec 2023** vs **+32%** general services inflation.

Margin-adjacent figures gathered 2026-08-21 (each labelled by who says
it — CMA finding vs sector submission):

- **Medicines often 50–60% cheaper online** than at the practice; the
  CMA puts potential owner savings at **£200–300 per year** (final
  report summaries; the transparency remedies — "tell owners medicines
  may be cheaper online", written-prescription right, publishing prices
  of the most-sold flea/tick/worm products with a link to the VMD online
  retailer register — flow from this finding).
- CMA blog/summaries: pet owners "may be paying **double** the online
  price" for medication.
- CMA econometrics (insurance-claims data): large vet groups price
  **~17% above independents** on average, with prices rising faster at
  acquired practices.
- **Sector submission, not a CMA finding:** FIVP (independent-practice
  federation) told the remedies consultation that medicine margins
  represent **25–40% of turnover** for independent practices and
  cross-subsidise consultation fees — practices expect to raise service
  prices if dispensing volume falls. Use only with that attribution.
**EXTRACTED 2026-08-21, confirmed against the FINAL report** — the
practice-level medicine margin figures, pulled from the report PDFs
themselves (fetched via the repo's Actions runner into
`notes/sources/cma/`, since gov.uk is egress-blocked from the editing
sandbox). All ¶-references below are to the **final decision report
Part A (24 Mar 2026)**, Section 11 — the final text carries the same
paragraph numbers as the provisional decision for the core finding:

- **Mark-up on purchase costs ("net net" prices): retail prices at
  LVG-owned AND independent practices average 2–5× purchase cost =
  100–400% average mark-up** (final Part A ¶11.12(a), restated
  ¶11.204). The spread across practices reflects differences in buying
  power, not in retail prices. Earlier working-paper cut (May 2025):
  LVGs ~4–5× (300–400%), independents ~2× (~100%). The CMA itself
  labels the estimate indicative, not a precise "true" mark-up
  (¶11.205).
- **Mark-up on manufacturer LIST prices**: LVGs [50–60%] to [90–100%]
  weighted average; independents 50–60%; injectables higher
  (~[100–200%] at one LVG, for wastage) (¶11.201; working paper §3.22).
  List prices are also the pricing base in practice, so manufacturer
  list increases pass straight through to owners (¶11.202 + fn. 1095).
- **The rebate wedge (final report, previously redacted tiering)**:
  wholesalers obtain a 15% discount from manufacturers and pass most of
  it on; **LVGs obtain manufacturer rebates of ~50% on average** (data
  from the nine largest UK manufacturers); independents in a buying
  group's Preferred Product scheme get [40–50%], those outside such
  schemes [20–30%] (¶11.203). This wedge is why a ~60% list mark-up
  becomes a 100–400% margin on real cost — and why mark-ups differ by
  buying power.
- **Medicine profits "account for a large proportion of the overall
  level of profitability of a FOP"** including administration and
  dispensing fees (¶11.12(b)); Part B calls the medicine mark-up
  "currently a substantial driver of FOP profits" (fn. 887).
- **Cross-subsidy verdict (final)**: no probative evidence of a true
  cross-subsidy (prices below incremental cost) — what the sector calls
  cross-subsidy is medicine revenue contributing to common costs
  (¶11.14–11.15); and the CMA rejected preserving a status quo in which
  owners of chronically ill pets "pay more than necessary for veterinary
  medicines in order to subsidise the professional fees paid by all pet
  owners" (Summary of final report ¶125–126).
- Price trend: average unit prices for medicines +[60–70%] 2014–2024 vs
  ONS services CPI +35% 2015–2023 (working paper, provisional figures
  disputed by LVGs).
- Source PDFs in-repo: `notes/sources/cma/` (77 documents incl. the
  medicines working paper, Appendices C/I/N, provisional decision
  Part A, **final decision Part A (62MB) and Part B**, final summary;
  full link manifest).

## Integrity checklist for this study

- [ ] No cross-country markup comparison chart, ever — case-study boxes only
- [ ] Every margin figure pinned to report + paragraph/page
- [ ] PPRI numbers labelled "human medicines" wherever they appear
- [ ] Dispensing map: each cell carries its own source and year
- [ ] The word "markup" defined once (on what base price, which channel
      stage) and used consistently
- [ ] No blending with the PPP study or the vet-CPI series

## Posting posture

**Higher sensitivity than vet-CPI.** A markup study points at named market
participants (distributors, corporate vet groups) far more directly than a
price-index post. Decide with employer comms whether the case-study boxes
are postable at all before drafting any public asset; the dispensing-rights
map alone is the low-risk publishable core.
