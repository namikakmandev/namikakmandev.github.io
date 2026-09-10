#!/usr/bin/env python3
"""What moved: the biggest year-on-year moves across the collection, found by the data.

Runs after build_catalog.py in the fetch workflow and writes data/_moves.json, which
moves.html draws. Nothing here is written by hand: every sentence is a template filled
from the numbers, and every number carries the dataset and series it came from.

The measure is a series' latest observation against the one a year earlier. For a
level series that is a percentage change; for something that is already a rate, a share
or a balance it is a difference in points. A move counts as big when it is far from
that series' own history of yearly changes (a z-score), so a series that always swings
30% does not crowd out one that never moves and just did.

    python3 scripts/whats_moving.py            # writes data/_moves.json
    python3 scripts/whats_moving.py --print    # also lists the picks
"""
import base64
import json
import math
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOP_N = 10
MAX_PER_DATASET = 2
MAX_PER_SUBJECT = 4
MIN_Z = 1.5            # how unusual the yearly change has to be, in that series' own history
MIN_PCT = 3.0          # and at least this much, so a flat series' 0.4% is not "unusual"
MIN_PTS = 1.0
MIN_HISTORY = 36       # observations of yearly change to judge "unusual" against (in months-equivalent)
RATE_RE = re.compile(r"%|percent|per cent|balance|\bshare (of|in)\b|yoy|year[- ]on[- ]year|growth|anomaly|\bppm\b", re.I)
PCT_RE = re.compile(r"%|percent|per cent|\bshare (of|in)\b|yoy|growth|balance", re.I)


# ---------------------------------------------------------------------------
# The plain-English names live in explore.html so the site and this page agree.

def _js_block(src, start, end):
    a = src.index(start) + len(start)
    return src[a:src.index(end, a)]


def load_names():
    html = open(os.path.join(ROOT, "explore.html"), encoding="utf-8").read()
    info = json.loads("{" + _js_block(html, "var INFO = {", "\n    };") + "}")
    subjects = json.loads("[" + _js_block(html, "var SUBJECTS = [", "\n    ];") + "]")
    names = json.loads("{" + _js_block(html, "var NAMES = {", "};") + "}")
    codes = {(k1 or k2): v for (k1, k2, v) in re.findall(r'(?:"([^"]+)"|(\w+)):\s*"([^"]+)"', _js_block(html, "var CODES = {", "};"))}
    return info, subjects, names, codes


def label_for(key, names, codes):
    m = re.match(r"^([A-Z]{2,3}|EU27_2020|EA20|EA19)(?:[|.](.+))?$", key)
    head = m and (names.get(m.group(1)) or ("European Union" if m.group(1) == "EU27_2020" else "Euro area" if m.group(1).startswith("EA") else None))
    if head:
        tail = m.group(2)
        return head + (" · " + (codes.get(tail) or tail.replace("_", " ")) if tail else "")
    return codes.get(key) or key.replace("_", " ")


# ---------------------------------------------------------------------------
# Dates. Keys are YYYY, YYYY-MM, YYYY-Qn, YYYY-Sn or YYYY-MM-DD.

def kind(d):
    if re.match(r"^\d{4}$", d):
        return "annual"
    if re.match(r"^\d{4}-\d{2}$", d):
        return "monthly"
    if re.match(r"^\d{4}-Q[1-4]$", d):
        return "quarterly"
    if re.match(r"^\d{4}-S[12]$", d):
        return "half-yearly"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        return "daily"
    return None


def year_before(d):
    return str(int(d[:4]) - 1) + d[4:]


def fresh(d, k, now):
    """Is the latest observation recent enough to be news?"""
    y, m = now.tm_year, now.tm_mon
    if k == "annual":
        return int(d) >= y - 1
    if k == "monthly":
        yy, mm = int(d[:4]), int(d[5:7])
        return (y - yy) * 12 + (m - mm) <= 4
    if k == "quarterly":
        yy, q = int(d[:4]), int(d[6])
        return (y - yy) * 12 + (m - q * 3) <= 7
    if k == "half-yearly":
        yy, h = int(d[:4]), int(d[6])
        return (y - yy) * 12 + (m - h * 6) <= 9
    if k == "daily":
        try:
            t = time.mktime(time.strptime(d, "%Y-%m-%d"))
        except ValueError:
            return False
        return (time.time() - t) / 86400 <= 45
    return False


def per_year(k):
    return {"annual": 1, "monthly": 12, "quarterly": 4, "half-yearly": 2, "daily": 250}[k]


def fmt_date(d):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", d)
    if m:
        return f"{int(m.group(3))} {months[int(m.group(2)) - 1]} {m.group(1)}"
    m = re.match(r"^(\d{4})-(\d{2})$", d)
    if m:
        return f"{months[int(m.group(2)) - 1]} {m.group(1)}"
    m = re.match(r"^(\d{4})-Q([1-4])$", d)
    if m:
        return f"Q{m.group(2)} {m.group(1)}"
    m = re.match(r"^(\d{4})-S([12])$", d)
    if m:
        return f"H{m.group(2)} {m.group(1)}"
    return d


def fmt(v):
    a = abs(v)
    if a >= 1e9:
        return f"{v / 1e9:.1f}bn".replace(".0bn", "bn")
    if a >= 1e6:
        return f"{v / 1e6:.1f}m".replace(".0m", "m")
    if a >= 1000:
        return f"{v:,.0f}"
    if a >= 10:
        return f"{v:.1f}".rstrip("0").rstrip(".")
    return f"{v:.2f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------

def yearly_changes(dates, series, is_rate, k):
    """[(date, change)] for every date with a value a year earlier."""
    out = []
    if k == "daily":
        # the nearest observation at or before the same calendar date a year earlier
        import datetime
        parsed = {}
        for d in dates:
            try:
                parsed[d] = datetime.date.fromisoformat(d)
            except ValueError:
                pass
        for d in dates:
            if d not in parsed:
                continue
            target = parsed[d] - datetime.timedelta(days=365)
            prev = None
            for back in range(0, 10):
                t = (target - datetime.timedelta(days=back)).isoformat()
                if t in series:
                    prev = series[t]
                    break
            if prev is None:
                continue
            cur = series[d]
            c = (cur - prev) if is_rate else ((cur / prev - 1) * 100 if prev and prev > 0 and cur > 0 else None)
            if c is not None and math.isfinite(c):
                out.append((d, c))
        return out
    for d in dates:
        p = year_before(d)
        if p not in series:
            continue
        prev, cur = series[p], series[d]
        if is_rate:
            c = cur - prev
        else:
            if not prev or prev <= 0 or cur <= 0:
                continue
            c = (cur / prev - 1) * 100
        if math.isfinite(c):
            out.append((d, c))
    return out


def unit_of(entry, key):
    units = entry.get("units") or {}
    if key in units:
        return units[key]
    tail = key.split("|")[-1]
    if tail in units:
        return units[tail]
    return entry.get("unit") or ""


def main():
    want_print = "--print" in sys.argv
    now = time.gmtime()
    info, subjects, names, codes = load_names()
    subj_of = {}
    for s, members in subjects:
        for n in members:
            subj_of.setdefault(n, s)
    cfg = {s["name"]: s for s in json.load(open(os.path.join(ROOT, "data-sources.json")))["sources"]}
    catalog = json.load(open(os.path.join(ROOT, "data", "_catalog.json")))["datasets"]
    by_name = {d["file"].replace("data/", "").replace(".json", ""): d for d in catalog}

    candidates = []
    for name, subj in subj_of.items():
        if subj == "Reference files" or name not in by_name:
            continue
        cat = by_name[name]
        if not cat.get("coverage") or not cat["coverage"].get("first"):
            continue
        path = os.path.join(ROOT, "data", name + ".json")
        try:
            body = json.load(open(path))
        except Exception:
            continue
        series_all = body.get("series") if isinstance(body, dict) else None
        if not isinstance(series_all, dict):
            continue
        entry = cfg.get(name, {})
        note = entry.get("note") or cat.get("note") or ""
        source = entry.get("source") or cat.get("source") or ""
        for key, ser in series_all.items():
            if not isinstance(ser, dict) or key.startswith("_"):
                continue
            pts = {d: v for d, v in ser.items() if isinstance(v, (int, float)) and math.isfinite(v)}
            dates = sorted(pts)
            if len(dates) < 8:
                continue
            k = kind(dates[-1])
            if not k or not all(kind(d) == k for d in dates[-3:]):
                continue
            last = dates[-1]
            if not fresh(last, k, now):
                continue
            unit = unit_of(entry, key)
            # A rate, a share or a balance moves in points; anything that can go negative
            # (a trade balance in dollars) is a difference too, since a percentage of a
            # negative number means nothing.
            is_rate = bool(RATE_RE.search(unit)) or any(pts[d] < 0 for d in dates)
            changes = yearly_changes(dates, pts, is_rate, k)
            if len(changes) < max(8, MIN_HISTORY * per_year(k) // 12):
                continue
            if changes[-1][0] != last:
                continue
            cur = changes[-1][1]
            hist = [c for _, c in changes[:-1]]
            mean = sum(hist) / len(hist)
            var = sum((c - mean) ** 2 for c in hist) / max(len(hist) - 1, 1)
            sd = math.sqrt(var)
            if sd <= 0:
                continue
            z = (cur - mean) / sd
            if abs(z) < MIN_Z or (abs(cur) < (MIN_PTS if is_rate else MIN_PCT)):
                continue
            # when did the yearly change last exceed this one, in the same direction?
            since = None
            for d, c in reversed(changes[:-1]):
                if (cur > 0 and c >= cur) or (cur < 0 and c <= cur):
                    since = d
                    break
            prev_date = year_before(last)
            hist_pts = dates[-(per_year(k) * 3 + 1):] if k != "daily" else dates[-260:]
            candidates.append({
                "dataset": name, "series": key, "subject": subj,
                "title": (info.get(name) or [name])[0],
                "question": (info.get(name) or ["", ""])[1],
                "label": label_for(key, names, codes),
                "unit": unit, "frequency": k, "is_rate": is_rate, "in_points": bool(PCT_RE.search(unit)),
                "latest": {"date": last, "value": pts[last]},
                "year_ago": {"date": prev_date, "value": pts.get(prev_date)},
                "change": cur, "z": z, "mean_change": mean, "n_history": len(hist),
                "since": since, "first": changes[0][0],
                "history": [[d, pts[d]] for d in hist_pts],
                "source": source, "note": note,
            })

    candidates.sort(key=lambda c: -abs(c["z"]))
    picks, per_ds, per_subj = [], {}, {}
    for c in candidates:
        if per_ds.get(c["dataset"], 0) >= MAX_PER_DATASET or per_subj.get(c["subject"], 0) >= MAX_PER_SUBJECT:
            continue
        picks.append(c)
        per_ds[c["dataset"]] = per_ds.get(c["dataset"], 0) + 1
        per_subj[c["subject"]] = per_subj.get(c["subject"], 0) + 1
        if len(picks) >= TOP_N:
            break

    # Which of these were not in the previous note: the page marks them, so a daily
    # reader sees at a glance what changed since yesterday.
    out_path = os.path.join(ROOT, "data", "_moves.json")
    previous = set()
    try:
        for it in json.load(open(out_path)).get("items", []):
            previous.add((it.get("dataset"), it.get("series"), it.get("latest", {}).get("date")))
    except Exception:
        pass
    for c in picks:
        c["new"] = (c["dataset"], c["series"], c["latest"]["date"]) not in previous
        c["sentence"] = sentence(c)
        c["chart"] = chart_link(c)
        c["z"] = round(c["z"], 2)
        c["change"] = round(c["change"], 2)
        c["mean_change"] = round(c["mean_change"], 2)

    out = {
        "_readme": "Written by scripts/whats_moving.py after each data refresh. The ten most unusual "
                   "year-on-year moves across the collection, ranked by how far each is from that "
                   "series' own history of yearly changes. Sentences are templates filled from the numbers.",
        "generated": time.strftime("%Y-%m-%d", now),
        "new_since_previous": sum(1 for c in picks if c["new"]),
        "candidates": len(candidates),
        "items": picks,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    if want_print:
        for i, c in enumerate(picks, 1):
            print(f"{i:2}. {'NEW ' if c['new'] else '    '}[{c['subject']}] {c['sentence']}")
    print(f"{len(picks)} picks from {len(candidates)} candidates -> data/_moves.json")


def sentence(c):
    up = c["change"] > 0
    what = c["title"] + (" — " + c["label"] if c["label"] and c["label"].lower() != c["title"].lower() else "")
    when = fmt_date(c["latest"]["date"])
    if c["is_rate"] and c["in_points"]:
        how = f"{'up' if up else 'down'} {fmt(abs(c['change']))} points on a year earlier, at {fmt(c['latest']['value'])}%"
    elif c["is_rate"]:
        how = f"{'up' if up else 'down'} {fmt(abs(c['change']))} on a year earlier, at {fmt(c['latest']['value'])}"
    else:
        how = f"{'up' if up else 'down'} {fmt(abs(c['change']))}% on a year earlier"
    ctx = ""
    if c["since"] is None:
        ctx = f", the {'biggest rise' if up else 'sharpest fall'} in a record that starts in {c['first'][:4]}"
    elif int(c["latest"]["date"][:4]) - int(c["since"][:4]) >= 2:
        ctx = f", the {'biggest rise' if up else 'sharpest fall'} since {fmt_date(c['since'])}"
    avg = c["mean_change"]
    avg_txt = f"{'+' if avg > 0 else ''}{fmt(avg)}{'%' if not c['is_rate'] else (' points' if c['in_points'] else '')}"
    return f"{what}: {how} in {when}{ctx}. The usual yearly change is {avg_txt}."


def chart_link(c):
    start = c["history"][0][0]
    spec = {"title": c["title"] + " — " + c["label"] if c["label"] else c["title"],
            "series": [{"dataset": c["dataset"], "series": c["series"], "start": str(int(start[:4]) - 7)}]}
    raw = json.dumps(spec, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "chart.html#" + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


if __name__ == "__main__":
    main()
