// Builds a CV as DOCX and HTML from a content JSON file.
// usage: node build_cv.js content.json out/Namik_Akman_Resume_Company
// PDF: print the HTML with headless Chromium (see ../SKILL.md, section 5).
const fs = require("fs");
const path = require("path");
const D = require("docx");
const { Document, Packer, Paragraph, TextRun, AlignmentType, LevelFormat, BorderStyle, TabStopType } = D;

const [, , contentPath, outBase] = process.argv;
if (!contentPath || !outBase) { console.error("usage: node build_cv.js content.json out/basename"); process.exit(1); }
const C = JSON.parse(fs.readFileSync(contentPath, "utf8"));
fs.mkdirSync(path.dirname(outBase), { recursive: true });

// Rich text: a string, or an array of [text, bold] pairs.
const norm = (s) => (typeof s === "string" ? [[s, false]] : s);

// ---------- DOCX ----------
const F = "Arial", RED = "8B1A1A", INK = "222222", DIM = "555555";
const r = (t, o = {}) => new TextRun({ text: t, font: F, size: 19, color: INK, ...o });
const segs = (s, o = {}) => norm(s).map(([t, b]) => r(t, { bold: b, ...o }));
const P = (children, po = {}) => new Paragraph({ spacing: { after: 70 }, ...po, children });
const H = (t) => new Paragraph({ spacing: { before: 180, after: 70 }, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: RED, space: 2 } },
  children: [new TextRun({ text: t, font: F, size: 20, bold: true, color: RED })] });
const B = (children) => new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 40 }, children });
const RL = (left, right, o = {}) => new Paragraph({ spacing: { before: 90, after: 40 }, tabStops: [{ type: TabStopType.RIGHT, position: 10466 }],
  children: [r(left, { bold: true, ...o }), r("\t" + right, { bold: true, color: DIM })] });

const kids = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 30 }, children: [new TextRun({ text: C.name, font: F, size: 36, bold: true, color: RED })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 30 }, children: [new TextRun({ text: C.headline, font: "Georgia", size: 22, bold: true, color: INK })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [r(C.contact, { size: 17, color: DIM })] }),
  H("PROFESSIONAL SUMMARY"), ...C.summary.map((s) => P(segs(s))),
  H("CORE COMPETENCIES"), ...C.competencies.map(([k, v]) => P([r(k + ": ", { bold: true }), r(v)])),
  H("PROFESSIONAL EXPERIENCE"),
];
for (const e of C.experience) {
  kids.push(RL(e.org, e.when, { color: RED, size: 20 }));
  for (const ro of e.roles) { kids.push(RL(ro.title, ro.when)); ro.bullets.forEach((b) => kids.push(B(segs(b)))); }
}
kids.push(RL("EARLIER CAREER", C.earlier.when, { color: RED, size: 20 }));
C.earlier.bullets.forEach((b) => kids.push(B(segs(b))));
kids.push(H(C.portfolioTitle), P([r(C.portfolioLead)]));
C.portfolio.forEach((b) => kids.push(B(segs(b))));
kids.push(H("EDUCATION")); C.education.forEach((e) => kids.push(B([r(e, { bold: true })])));
kids.push(H("LANGUAGES & TECHNICAL SKILLS"), P([r("Languages: ", { bold: true }), r(C.languages)]), P([r("Technical: ", { bold: true }), r(C.technical)]));

const doc = new Document({
  styles: { default: { document: { run: { font: F, size: 19, color: INK } } } },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 220 } } } }] }] },
  sections: [{ properties: { page: { margin: { top: 680, bottom: 680, left: 850, right: 850 } } }, children: kids }],
});
Packer.toBuffer(doc).then((b) => fs.writeFileSync(outBase + ".docx", b));

// ---------- HTML (PDF source) ----------
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const hs = (s) => norm(s).map(([t, b]) => (b ? `<b>${esc(t)}</b>` : esc(t))).join("");
let h = `<!doctype html><html><head><meta charset="utf-8"><title>${esc(C.name)} — CV</title><style>
@page{size:A4;margin:14mm 16mm 13mm}body{font-family:Arial,Helvetica,sans-serif;font-size:9.6pt;line-height:1.38;color:#222;margin:0}
.c{text-align:center}h1{color:#8B1A1A;font-size:18pt;margin:0;letter-spacing:.04em}.hl{font-family:Georgia,serif;font-weight:bold;font-size:11pt;margin:2px 0}
.ct{font-size:8.4pt;color:#555;margin-bottom:8px}h2{color:#8B1A1A;font-size:9.8pt;margin:11px 0 4px;padding-bottom:2px;border-bottom:1.5px solid #8B1A1A;page-break-after:avoid}
p{margin:0 0 4px}ul{margin:0 0 3px 16px;padding:0}li{margin:0 0 2px}.rl{display:flex;justify-content:space-between;font-weight:bold;margin:6px 0 2px;page-break-after:avoid}
.org{color:#8B1A1A}.w{color:#555;white-space:nowrap;margin-left:12px}</style></head><body>
<div class="c"><h1>${esc(C.name)}</h1><div class="hl">${esc(C.headline)}</div><div class="ct">${esc(C.contact)}</div></div>
<h2>PROFESSIONAL SUMMARY</h2>${C.summary.map((s) => `<p>${hs(s)}</p>`).join("")}
<h2>CORE COMPETENCIES</h2>${C.competencies.map(([k, v]) => `<p><b>${esc(k)}:</b> ${esc(v)}</p>`).join("")}
<h2>PROFESSIONAL EXPERIENCE</h2>`;
for (const e of C.experience) {
  h += `<div class="rl"><span class="org">${esc(e.org)}</span><span class="w">${esc(e.when)}</span></div>`;
  for (const ro of e.roles) h += `<div class="rl"><span>${esc(ro.title)}</span><span class="w">${esc(ro.when)}</span></div><ul>${ro.bullets.map((b) => `<li>${hs(b)}</li>`).join("")}</ul>`;
}
h += `<div class="rl"><span class="org">EARLIER CAREER</span><span class="w">${esc(C.earlier.when)}</span></div><ul>${C.earlier.bullets.map((b) => `<li>${hs(b)}</li>`).join("")}</ul>`;
h += `<h2>${esc(C.portfolioTitle)}</h2><p>${esc(C.portfolioLead)}</p><ul>${C.portfolio.map((b) => `<li>${hs(b)}</li>`).join("")}</ul>`;
h += `<h2>EDUCATION</h2><ul>${C.education.map((e) => `<li><b>${esc(e)}</b></li>`).join("")}</ul>`;
h += `<h2>LANGUAGES &amp; TECHNICAL SKILLS</h2><p><b>Languages:</b> ${esc(C.languages)}</p><p><b>Technical:</b> ${esc(C.technical)}</p></body></html>`;
fs.writeFileSync(outBase + ".html", h);
console.log("wrote", outBase + ".docx", outBase + ".html");
