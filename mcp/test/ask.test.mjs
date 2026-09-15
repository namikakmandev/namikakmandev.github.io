// The daily question counters behind /v1/ask, exercised without a runtime.
import assert from "node:assert/strict";
import { emptyQuota, takeQuota, refundQuota, quotaView, PER_VISITOR_PER_DAY, SITE_PER_DAY, today, advisorQuestion } from "../dist/ask.js";

let failures = 0;
function check(name, fn) {
  try { fn(); console.log("ok   ", name); } catch (e) { failures++; console.log("FAIL ", name, "\n      ", e.message); }
}

check("a visitor gets the daily allowance and no more", () => {
  let s = emptyQuota("2026-09-08");
  for (let i = 0; i < PER_VISITOR_PER_DAY; i++) {
    const r = takeQuota(s, "a", "2026-09-08"); s = r.state;
    assert.equal(r.ok, true);
    assert.equal(quotaView(s, "a").remaining, PER_VISITOR_PER_DAY - i - 1);
  }
  const r = takeQuota(s, "a", "2026-09-08");
  assert.equal(r.ok, false); assert.equal(r.reason, "visitor");
  assert.equal(takeQuota(s, "b", "2026-09-08").ok, true, "another visitor is unaffected");
});

check("the site-wide ceiling holds across visitors", () => {
  let s = emptyQuota("2026-09-08");
  let taken = 0;
  for (let v = 0; v < SITE_PER_DAY; v++) { const r = takeQuota(s, "v" + v, "2026-09-08"); s = r.state; if (r.ok) taken++; }
  assert.equal(taken, SITE_PER_DAY);
  const r = takeQuota(s, "fresh", "2026-09-08");
  assert.equal(r.ok, false); assert.equal(r.reason, "site");
});

check("a new day resets everything", () => {
  let s = emptyQuota("2026-09-08");
  for (let i = 0; i < PER_VISITOR_PER_DAY; i++) s = takeQuota(s, "a", "2026-09-08").state;
  const r = takeQuota(s, "a", "2026-09-09");
  assert.equal(r.ok, true); assert.equal(r.state.day, "2026-09-09"); assert.equal(r.state.site, 1);
});

check("a refund gives the question back, never below zero, never across days", () => {
  let s = emptyQuota("2026-09-08");
  s = takeQuota(s, "a", "2026-09-08").state;
  s = refundQuota(s, "a", "2026-09-08");
  assert.equal(quotaView(s, "a").remaining, PER_VISITOR_PER_DAY); assert.equal(s.site, 0);
  s = refundQuota(s, "a", "2026-09-08");
  assert.equal(s.site, 0); assert.equal(s.visitors.a, 0);
  s = takeQuota(s, "a", "2026-09-08").state;
  const s2 = refundQuota(s, "a", "2026-09-09");
  assert.equal(s2.site, 1, "yesterday's count is not touched from a later day");
});

check("today is a UTC calendar date", () => {
  assert.match(today(Date.UTC(2026, 8, 8, 23, 59)), /^2026-09-08$/);
  assert.match(today(Date.UTC(2026, 8, 9, 0, 0)), /^2026-09-09$/);
});

check("the advisor question names the dataset and the series on screen, in either language", () => {
  const q = advisorQuestion("tr-cpi-ppi", ["cpi", "cpi_food"]);
  assert.match(q, /"tr-cpi-ppi"/); assert.match(q, /cpi, cpi_food/); assert.match(q, /should not be used for/);
  const t = advisorQuestion("tr-cpi-ppi", [], "tr");
  assert.match(t, /veri setini/); assert.doesNotMatch(t, /Bakılan/);
});

if (failures) { console.log(`\n${failures} failing`); process.exit(1); }
console.log("\nall passing");
