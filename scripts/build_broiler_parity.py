#!/usr/bin/env python3
"""Build data/broiler-parity.json from the fetched FAOSTAT + FRED series.

Parity = chicken producer price / maize producer price, both USD/tonne, same
country, same year. Unit-free, so the live-weight ("biological") and carcass
chicken items can sit in one file — but they are NOT level-comparable, so each
region carries its meat_basis and Türkiye is split into two segments rather
than spliced across the 2011/2012 basis change.

"world" is monthly: IMF global poultry / corn prices via FRED — the import-
parity benchmark for markets that publish no domestic producer prices
(Kuwait, Oman, Qatar in part, Saudi Arabia in part, UAE).
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def series(fname):
    return json.load(open(os.path.join(ROOT, "data", fname)))["series"]


carcass = series("broiler-price-fao.json")
bio = series("broiler-price-fao-bio.json")
maize = series("feed-maize-fao.json")
world = series("world-meat-feed.json")

# country -> (meat series, basis). Only countries where a usable overlap with
# domestic maize exists. Kuwait/Oman/UAE have no chicken price at all; Saudi
# has chicken but almost no domestic maize price (3 yrs) - see world benchmark.
REGIONS = {
    "EG": ("Egypt", carcass, "carcass"),
    "QA": ("Qatar", carcass, "carcass"),
    "LB": ("Lebanon", carcass, "carcass"),
    "TR-carcass": ("Türkiye", carcass, "carcass"),
    "TR-bio": ("Türkiye", bio, "live weight (biological)"),
    "PL": ("Poland", bio, "live weight (biological)"),
    "IQ": ("Iraq", bio, "live weight (biological)"),
    "JO": ("Jordan", bio, "live weight (biological)"),
}

out = {
    "note": ("annual FAOSTAT producer prices, USD/tonne; parity = chicken/maize. "
             "meat_basis differs by country - ratios are comparable over time "
             "within a region, levels are not comparable across bases."),
    "regions": {},
}
for key, (area, meat, basis) in REGIONS.items():
    m, f = meat.get(area, {}), maize.get(area, {})
    rows = [[int(y), round(m[y], 1), round(f[y], 1), round(m[y] / f[y], 3)]
            for y in sorted(set(m) & set(f), key=int) if f[y]]
    if not rows:
        continue
    out["regions"][key] = {
        "source": "FAOSTAT PP via bulk download",
        "meat_basis": basis,
        "columns": ["year", "chicken_usd_t", "maize_usd_t", "parity"],
        "rows": rows,
    }
    if key.startswith("TR"):
        out["regions"][key]["caveat"] = (
            "TR levels look far above known farm-gate prices (2023: 5282 USD/t "
            "'live weight' vs ~2300 USD/t TurkStat farm gate) - use the ratio's "
            "movement only, and verify levels against TurkStat/EVDS before "
            "publishing them")

# Poland weekly, current to within a week: EC agri-food portal. Broiler is a
# carcass selling price in EUR/100kg -> x10 for EUR/t; feed grains are EUR/t.
# Both parities kept: wheat is the Polish ration's base grain, maize matches
# the denominator used in the annual FAOSTAT series.
try:
    plb = series("pl-broiler-weekly.json")["Whole broiler (65%)"]
    plf = series("pl-feed-weekly.json")
    fw, fm = plf["Feed wheat"], plf["Feed maize"]
    weeks = sorted(set(plb) & set(fw) & set(fm))
    out["regions"]["PL-weekly"] = {
        "source": "EC agri-food data portal (weekly, EUR)",
        "meat_basis": "carcass selling price, whole broiler 65%",
        "columns": ["week", "broiler_eur_t", "feed_wheat_eur_t", "feed_maize_eur_t",
                    "parity_wheat", "parity_maize"],
        "rows": [[wk, round(plb[wk] * 10, 1), round(fw[wk], 1), round(fm[wk], 1),
                  round(plb[wk] * 10 / fw[wk], 3), round(plb[wk] * 10 / fm[wk], 3)]
                 for wk in weeks if fw[wk] and fm[wk]],
    }
except (FileNotFoundError, KeyError):
    pass  # weekly PL sources not fetched yet

# Türkiye monthly, current to last month: TÜİK Yİ-ÜFE via EVDS, the same
# T17/T25 pair the cattle study used. Index ratio (both 2005-01=100), so only
# the movement is meaningful — and T17 is ALL processed meat, not broiler.
try:
    trm = series("tr-meat-feed-ppi.json")
    tm, tf = trm["meat_ppi"], trm["feed_ppi"]
    out["regions"]["TR-monthly"] = {
        "source": "TCMB EVDS / TÜİK Yİ-ÜFE (TP.TUFE1YI.T17 / T25)",
        "meat_basis": "meat-products PPI, all meat - NOT broiler-specific",
        "columns": ["month", "meat_ppi", "feed_ppi", "parity_idx"],
        "rows": [[m, round(tm[m], 2), round(tf[m], 2), round(tm[m] / tf[m], 4)]
                 for m in sorted(set(tm) & set(tf)) if tf[m]],
    }
except (FileNotFoundError, KeyError):
    pass  # EVDS series not fetched yet

# IMF poultry on FRED is an INDEX (2016=100), not USD/tonne, so the world
# parity can only be an index: rebase corn to 2016=100 and take the ratio.
pm, pc = world["poultry"], world["corn"]
both = [mth for mth in sorted(set(pm) & set(pc)) if pc[mth]]
corn_base = sum(pc[m] for m in both if m.startswith("2016")) / 12
out["regions"]["WORLD"] = {
    "source": "IMF primary commodity prices via FRED (PPOULTUSDM index, PMAIZMTUSDM USD/t)",
    "meat_basis": "world benchmark, 2016=100 index",
    "columns": ["month", "poultry_idx", "corn_idx", "parity_idx"],
    "rows": [[mth, round(pm[mth], 2), round(pc[mth] / corn_base * 100, 2),
              round(pm[mth] / (pc[mth] / corn_base), 2)] for mth in both],
}

path = os.path.join(ROOT, "data", "broiler-parity.json")
json.dump(out, open(path, "w"), separators=(",", ":"))
for k, r in out["regions"].items():
    rows = r["rows"]
    print(f"{k:11} {rows[0][0]} -> {rows[-1][0]}  n={len(rows)}")
