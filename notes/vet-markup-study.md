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
| Italy | LIKELY NO — cited alongside Spain as a country where vet dispensing is prohibited; pharmacy-based retail | pharmacy-led | secondary only (IM Veterinaria comparison) — **TO VERIFY against D.Lgs. 193/2006 / current Italian law before use** |
| Netherlands | YES — every registered vet holds a retail licence by law ("apotheekhoudende dierenarts"); may dispense only to clients whose animals are under their care; trading beyond own clients requires a separate licence. UDD class = vet-administered only | pharmacies dispense URA products on a vet's prescription | KNMvD kennisbank "Aan wie mag een dierenarts diergeneesmiddelen afleveren?"; CBG-MEB "Afleverstatus"; RVO diergeneesmiddelen page |
| Belgium | YES — vets keep one registered medicines depot (dépôt/depot, numbered by the agency) and may supply ("fourniture/verschaffing") medicines to owners of animals under their care, quantity limited to the treatment | pharmacies dispense too | AFMPS/FAGG pages "Dépôt de médicaments pour les médecins vétérinaires" and "Fourniture de médicaments au responsable d'animaux" (afmps.be / fagg.be) |
| Austria | YES — tierärztliche Hausapotheke under the Tierarzneimittelgesetz (TAMG); dispensing only to keepers of animals under the vet's treatment; opening notified to the district authority; chamber-supervised | public pharmacies a parallel channel | Österreichische Tierärztekammer, Berufsleitfaden "Tierärztliche Hausapotheke"; TAMG (ris.bka.gv.at); Apothekerkammer TAKG/TAMG merkblatt |
| Czechia | YES — vets are authorised to dispense (výdej) veterinary medicinal products alongside pharmacists; sellers of reserved (OTC-class) products register with ÚSKVBL | pharmacies dispense too | Medicines Act 378/2007 Sb.; ÚSKVBL seller register (uskvbl.cz); VFU teaching materials on léčiva |
| Hungary | PARTIAL — governing regulation identified: 128/2009. (X. 6.) FVM rendelet on veterinary products (prescribing, dispensing/kiadás and record rules for vets; Nébih oversight; 2023+ AMR amendments). The precise practice-sale rule needs the article text | vet pharmacies (állatgyógyszertár) retail channel | 128/2009 FVM rendelet (njt.hu / net.jogtar.hu); Nébih notice on changes — **TO PIN to specific §§ before use** |
| Romania | CHANNEL-SPLIT — retail of vet medicinal products runs exclusively through ANSVSA-authorised veterinary pharmacies (farmacii veterinare) and pharmaceutical points; a vet practice as such is not a retail outlet — vets prescribe, authorised units dispense (whether/when vets own those units: nuance TO VERIFY) | the authorised vet-pharmacy network IS the channel; online sale only for non-prescription via registered retailers | ANSVSA "Precizări privind prescrierea, comercializarea, eliberarea si utilizarea produselor medicinale veterinare"; ANSVSA "Activitate farmaceutică veterinară" (ansvsa.ro) |
| Switzerland | YES — vets may run a "tierärztliche Privatapotheke" for their own clients; needs professional-practice AND retail-trade authorisation; cantons inspect | pharmacies and some specialist shops sell defined categories | TAMV (Tierarzneimittelverordnung); BLV "Verschreibung, Abgabe und Anwendung" (blv.admin.ch); canton Zürich licensing page |
| Ireland | YES — vets supply POM to animals under their care; classes route supply to vet / pharmacist / licensed retailer (LR) / registered CAM outlets | pharmacies + DAFM-licensed retailers; internet sale only via DAFM-registered suppliers | HPRA "Classification of veterinary medicines in Ireland"; Veterinary Medicinal Products Act 2023; DAFM internet-supply list |
| Finland | **YES BUT AT COST — zero profit.** Vets may hand over (luovuttaa) medicines only for treatment needs and must charge exactly their own purchase price; economic profit on medicine sales is prohibited | pharmacies the normal retail channel | Animal Medication Act 387/2014; MMM regulation 17/2014; Ruokavirasto Q&A "Lääkkeiden hankkiminen ja hinnoittelu" |
| Portugal | CHANNEL-SPLIT — dispensing entities are pharmacies and DGAV-authorised retail sale points (postos de venda); the vet practice is not a named retail channel (vets administer; ceding detail TO VERIFY in DL 148/2008) | pharmacies + authorised retail points; simplified regime for non-POM outlets | DGAV retail-sale FAQ (2023) and Manual de Dispensa; Decreto-Lei 148/2008 as amended |
| Greece | YES (hybrid) — private vet clinics/production-animal vet offices may supply products to owners after issuing the prescription; dedicated vet-medicine retail shops require a licence AND a responsible scientist holding a veterinary degree | pharmacies may sell vet POM on prescription after notifying the regional veterinary service | minagric.gr vet-pharmaceuticals pages; national licence registry (mitos.gov.gr / EUGO, "Άδεια λιανικής πώλησης κτηνιατρικών φαρμακευτικών προϊόντων"); Kilkis pharmacists' association FAQ |
| Croatia | CHANNEL-SPLIT — retail only via authorised veterinary pharmacies (veterinarske ljekarne), per-location approval, national register kept by the veterinary directorate; distance sale only through registered ljekarne | the registered vet-pharmacy network IS the channel | Zakon o veterinarsko-medicinskim proizvodima (zakon.hr); Uprava za veterinarstvo "Veterinarske ljekarne" register (veterinarstvo.hr) |
| Slovakia | YES (dual) — pharmacies dispense vet medicines under their pharmacy-care permit; separately, retail sale of vet medicines (incl. distance sale) runs on a permit from the regional veterinary and food administration — the route vets use | pharmacies dispense too | zákon č. 362/2011 Z. z. o liekoch; ŠVPS "Farmácia" pages (svps.sk); mediPRÁVNIK analysis "výdaj lekárňou vs. maloobchodný predaj veterinárnymi lekármi" |
| Bulgaria | VET-STAFFED PHARMACIES — retail only via BFSA-licensed veterinary pharmacies; **the pharmacy manager and the persons selling must be veterinarians by law** | the licensed vet-pharmacy network IS the channel; BFSA controls wholesale + retail | Закон за ветеринарномедицинската дейност via BFSA (БАБХ) pages; bfsa.egov.bg licensing specimens; 1Legal.net summary of licensing requirements |

Twenty-five rows now cover six distinct models: coupled (DE, UK, PL, TR,
NL, BE, AT, CZ, CH, IE, SK, EL), dual-channel (FR), decoupled (DK, SE, NO),
**dispense-at-cost (FI — vets may hand over medicines but only at their own
purchase price, profit prohibited)**, prohibited (ES, likely IT), and the
authorised-vet-pharmacy channel split (RO, HR, PT, BG — with Bulgaria
requiring the pharmacy staff to BE veterinarians). The retail-margin actor
differs country by country, and in FI/DK/SE/NO/ES a vet medicine margin is
legally zero or non-existent. Still TO COMPILE: SI, Baltics (EE, LV, LT),
Western Balkans (RS, BA, MK, ME, AL, XK); verifications open: HU article
text, IT, RO/PT ownership-and-ceding nuances.

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
- TO EXTRACT next: the practice-level medicine margin percentages from
  the final report appendices (not carried in the press summaries) —
  requires the full report PDF from the gov.uk case page.

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
