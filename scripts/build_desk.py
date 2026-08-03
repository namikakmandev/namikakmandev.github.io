#!/usr/bin/env python3
"""Build data/desk-index.json — the indicator layer behind desk.html.

Reads the series already fetched into data/ (plus the broiler series in
js/broiler-data.js) and emits one small file: for each indicator, the latest
value, the change, a sparkline, and — the part that matters — the source,
the exact series code, what the series does NOT measure, and any known break.

Adding an indicator is an entry in INDICATORS below. Pointing this at internal
sources later means changing where `load()` reads from, not rewriting the page.

    python scripts/build_desk.py
"""
import json, re, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "desk-index.json"


def load(name):
    return json.loads((DATA / name).read_text())


def annual_hicp():
    """Euro-area HICP, monthly -> annual mean. The named deflator for EUR money."""
    raw = load("eu-hicp.json")["series"]["hicp"]
    by_year = {}
    for k, v in raw.items():
        by_year.setdefault(int(k[:4]), []).append(v)
    return {y: statistics.fmean(v) for y, v in by_year.items() if len(v) >= 6}


def broiler_series():
    """TR broiler parity (chicken price / feed price), monthly, from js/broiler-data.js."""
    txt = (ROOT / "js" / "broiler-data.js").read_text()
    body = txt.split("window.BROILER_DATA=", 1)[1].strip().rstrip(";")
    rows = json.loads(body.replace("'", '"'))
    return [(m, parity, meat, feed) for m, parity, meat, feed in rows]


def pct(new, old):
    return None if not old else (new / old - 1) * 100


def spark(pairs, n=48):
    """[(label, value)] -> trimmed sparkline payload."""
    tail = pairs[-n:]
    return [[str(a), round(float(b), 4)] for a, b in tail]


def build():
    out = []
    hicp = annual_hicp()

    # 1 ── EU-27 veterinary expenses (Eurostat EAA) ───────────────────────────
    vet = load("eu-vet-expenses.json")["series"]["EU27_2020"]
    yrs = sorted(vet, key=int)
    y1, y0 = yrs[-1], yrs[-2]
    base = yrs[-11] if len(yrs) >= 11 else yrs[0]
    defl = hicp[int(y1)] / hicp[int(base)]
    out.append({
        "id": "eu-vet-spend", "group": "Spend",
        "title": "EU-27 farm veterinary expenditure", "market": "EU-27",
        "value": vet[y1], "unit": "€ million", "asof": y1,
        "change": pct(vet[y1], vet[y0]), "change_label": f"vs {y0}",
        "change2": pct(vet[y1] / defl, vet[base]),
        "change2_label": f"real, vs {base} (HICP-deflated)",
        "spark": spark([(y, vet[y]) for y in yrs]),
        "source": "Eurostat, Economic Accounts for Agriculture",
        "code": "aact_eaa01 · AM205000 · MIO_EUR",
        "not_measured": "All livestock combined — not cattle only. Excludes companion-animal care. Current prices, so non-euro members carry FX effects.",
        "break": None,
        "deflator": "Euro-area HICP annual mean (FRED CP0000EZ19M086NEST)",
    })

    # 2 ── TR broiler parity ──────────────────────────────────────────────────
    br = broiler_series()
    months = [r[0] for r in br]
    parity = [r[1] for r in br]
    last, prev12 = parity[-1], parity[-13] if len(parity) > 13 else parity[0]
    longrun = statistics.fmean(parity)
    out.append({
        "id": "tr-broiler-parity", "group": "Margin",
        "title": "Türkiye broiler parity (chicken price ÷ feed price)", "market": "Türkiye",
        "value": last, "unit": "ratio", "asof": months[-1],
        "change": pct(last, prev12), "change_label": "vs same month last year",
        "change2": pct(last, longrun), "change2_label": f"vs {months[0][:4]}–{months[-1][:4]} mean ({longrun:.2f})",
        "spark": spark(list(zip(months, parity)), 60),
        "source": "TÜİK Yİ-ÜFE producer price indices; TEPGE poultry market reports",
        "code": "C10.12 (poultry meat) ÷ C10.91 (feed), monthly",
        "not_measured": "A ratio of two price indices, not a physical quantity and not a margin. It shows how the price relationship moved, never the level of profit. Excludes chick cost, energy, labour and mortality.",
        "break": None,
        "deflator": "None needed — both legs are price indices, so inflation largely cancels in the ratio.",
    })

    # 3 ── Cattle parity, three markets ───────────────────────────────────────
    cp = load("cattle-parity.json")["regions"]
    for reg, name in (("US", "United States"), ("EU", "European Union"), ("TR", "Türkiye")):
        rows = cp[reg]["rows"]
        m = [r[0] for r in rows]
        p = [r[3] for r in rows]
        out.append({
            "id": f"{reg.lower()}-cattle-parity", "group": "Margin",
            "title": f"{name} cattle parity (cattle price ÷ feed price)", "market": name,
            "value": p[-1], "unit": "ratio", "asof": m[-1],
            "change": pct(p[-1], p[-13]) if len(p) > 13 else None, "change_label": "vs same month last year",
            "change2": pct(p[-1], statistics.fmean(p)), "change2_label": "vs own long-run mean",
            "spark": spark(list(zip(m, p)), 60),
            "source": {"US": "BLS producer price indexes via FRED",
                       "EU": "Eurostat agricultural price indices",
                       "TR": "TÜİK producer price indices"}[reg],
            "code": {"US": "WPU0131 (slaughter cattle) ÷ WPU012202 (corn)",
                     "EU": "apri_pi15_outa / apri_pi15_ina",
                     "TR": "Yİ-ÜFE livestock ÷ feed"}[reg],
            "not_measured": "Index ratio, not kilograms and not margin. Levels are not comparable across countries — only changes within a country are. Series start dates differ.",
            "break": None,
            "deflator": "None — index ÷ index.",
        })

    # 4 ── EU cattle herd ─────────────────────────────────────────────────────
    herd = load("herd-cattle.json")["series"]["EU"]
    hy = sorted(herd, key=int)
    out.append({
        "id": "eu-cattle-herd", "group": "Volume",
        "title": "EU cattle herd", "market": "EU",
        "value": herd[hy[-1]] / 1e6, "unit": "million head", "asof": hy[-1],
        "change": pct(herd[hy[-1]], herd[hy[-2]]), "change_label": f"vs {hy[-2]}",
        "change2": pct(herd[hy[-1]], herd[hy[-11]]), "change2_label": f"vs {hy[-11]}",
        "spark": spark([(y, herd[y] / 1e6) for y in hy], 40),
        "source": "FAOSTAT cattle stocks, via Our World in Data",
        "code": "cattle-livestock-count-heads",
        "not_measured": "Dairy and beef combined; a head count says nothing about carcass weight or output. National totals only.",
        "break": None, "deflator": None,
    })

    # 5 ── US cow-calf costs (carries a real methodology break) ───────────────
    cc = load("us-cowcalf-costs.json")["series"]
    tot = cc.get("Total, costs listed") or cc[next(iter(cc))]
    ty = sorted(tot, key=int)
    out.append({
        "id": "us-cowcalf-cost", "group": "Cost",
        "title": "US cow-calf total listed costs", "market": "United States",
        "value": tot[ty[-1]], "unit": "$ per bred cow", "asof": ty[-1],
        "change": pct(tot[ty[-1]], tot[ty[-2]]), "change_label": f"vs {ty[-2]}",
        "change2": None, "change2_label": None,
        "spark": spark([(y, tot[y]) for y in ty], 30),
        "source": "USDA ERS commodity costs and returns, cow-calf",
        "code": "ERS cow-calf, U.S. total",
        "not_measured": "Accounting cost per bred cow, not cash cost and not profit.",
        "break": "USDA ERS changed the survey basis in 2008 — a step of about −29% in one year that is not economic. No comparison may span it.",
        "deflator": None,
    })

    return {
        "generated_from": "public sources only — no company or licensed data",
        "builder": "scripts/build_desk.py",
        "indicators": out,
    }


if __name__ == "__main__":
    idx = build()
    OUT.write_text(json.dumps(idx, ensure_ascii=False, indent=1))
    print(f"wrote {OUT.relative_to(ROOT)} — {len(idx['indicators'])} indicators")
    for i in idx["indicators"]:
        print(f"  {i['id']:22} {i['asof']:>8}  {i['value']:>12,.2f} {i['unit']}")
