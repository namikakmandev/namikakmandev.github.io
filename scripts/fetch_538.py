#!/usr/bin/env python3
"""Build the FiveThirtyEight forecast-calibration dataset from 538's own archive.

Source: github.com/fivethirtyeight/checking-our-work-data — the data behind
"How Good Are FiveThirtyEight Forecasts?". ABC shut the site down in March 2025
and pulled it offline; the GitHub archive survived. raw_forecasts.zip holds
3.1M rows: one published probability plus the outcome that followed.

Raw rows are NOT independent observations. 538 re-ran most forecasts daily, so
one House race contributes ~100 rows; and every event lists every outcome, so
Trump and Biden are two mechanically-linked rows for the same race. Pooling them
gives a calibration curve on n=3.1M that is really a few hundred elections and a
few tens of thousands of games.

This script reduces the archive to what an honest test needs and commits that:

  data/fte-forecasts.json   one row per (event, entity, field, model), at two
                            snapshots — the final forecast and the forecast
                            closest to 30 days out — tagged with the contest it
                            belongs to, so the analysis can bootstrap over
                            clusters at whichever level it wants to defend.
  data/fte-slices.json      sufficient statistics for the slices deliberately
                            excluded (live in-play forecasts, every-forecast-date
                            pooling), so the robustness table is reproducible
                            without re-downloading 350MB.

Usage:  python3 scripts/fetch_538.py [--cache DIR]
"""
import argparse, csv, io, json, os, sys, urllib.request, zipfile
from collections import defaultdict
from datetime import date, datetime

REPO = "https://raw.githubusercontent.com/fivethirtyeight/checking-our-work-data/master"
ZIP_URL = f"{REPO}/raw_forecasts.zip"
LEAD_TARGET = 30          # days before the event for the second snapshot
BUCKETS = 20              # calibration bins, 5 percentage points wide

csv.field_size_limit(10 ** 8)


def fetch_zip(cache_dir):
    """Download raw_forecasts.zip once, reuse it on later runs."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "raw_forecasts.zip")
    if os.path.exists(path) and os.path.getsize(path) > 10_000_000:
        print(f"  cache hit: {path} ({os.path.getsize(path):,} bytes)")
        return path
    print(f"  downloading {ZIP_URL} ...")
    with urllib.request.urlopen(ZIP_URL, timeout=600) as r, open(path, "wb") as fh:
        fh.write(r.read())
    print(f"  saved {os.path.getsize(path):,} bytes")
    return path


def parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def contest_key(event, entity, field, event_date):
    """The set of rows whose outcomes are mechanically linked.

    538's schema is not uniform across projects. A House race puts the race in
    `event` and the candidates in `entity`; an NBA game leaves `event` empty and
    puts the matchup in `entity`, split into prob1/prob2/probtie. Both are one
    contest whose probabilities sum to one and whose outcomes cannot both
    happen, which is the thing a cluster bootstrap must not break apart.
    """
    if field in ("prob1", "prob2", "probtie"):     # head-to-head fixture
        return f"{event}|{entity}|{event_date}"
    return f"{event}|{field}|{event_date}"         # race, or season-long outcome


def is_live(project, forecast_type):
    """In-play forecasts: updated during the event itself.

    A team 30 points up with two minutes left is a 99.9% call that any model
    gets right. They are 430k of the 3.1M rows and they flatter every
    calibration statistic, so the headline excludes them.
    """
    return forecast_type == "live" or project.endswith("-live")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=os.environ.get("FTE_CACHE", ".cache/538"),
                    help="directory to keep the downloaded archive in")
    ap.add_argument("--out", default="data", help="directory to write the JSON into")
    args = ap.parse_args(argv)

    print("FiveThirtyEight forecast archive")
    zpath = fetch_zip(args.cache)

    # ---------------------------------------------------------------- pass 1
    # Walk the archive once. Keep, per forecasting unit, the last forecast and
    # the one closest to LEAD_TARGET days out. Accumulate the excluded slices
    # as sufficient statistics at the same time.
    units = {}
    slices = defaultdict(lambda: {"n": 0, "sum_p": 0.0, "sum_p2": 0.0,
                                  "sum_o": 0.0, "sum_po": 0.0,
                                  "bins": [[0, 0.0, 0.0] for _ in range(BUCKETS)]})
    total = skipped_tie = skipped_bad = 0

    def add_slice(name, p, o):
        s = slices[name]
        s["n"] += 1
        s["sum_p"] += p
        s["sum_p2"] += p * p
        s["sum_o"] += o
        s["sum_po"] += p * o
        b = s["bins"][min(BUCKETS - 1, int(p * BUCKETS))]
        b[0] += 1
        b[1] += p
        b[2] += o

    with zipfile.ZipFile(zpath) as z:
        name = next(n for n in z.namelist() if n.endswith(".csv"))
        with z.open(name) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))
            for row in reader:
                total += 1
                try:
                    p = float(row["prob"])
                    o = float(row["outcome"])
                except (TypeError, ValueError):
                    skipped_bad += 1
                    continue
                if not (0.0 <= p <= 1.0):
                    skipped_bad += 1
                    continue
                if o not in (0.0, 1.0):
                    # 16 soccer draws coded 0.5. Not a binary outcome; drop.
                    skipped_tie += 1
                    continue

                project, ftype = row["project"], row["forecast_type"]
                field = row["field"]
                live = is_live(project, ftype)
                add_slice("all_dates_incl_live", p, o)
                if not live:
                    add_slice("all_dates_no_live", p, o)
                else:
                    add_slice("live_only", p, o)
                    continue          # live forecasts never enter the panel

                fdate, edate = parse_date(row["forecast_date"]), parse_date(row["event_date"])
                contest = contest_key(row["event"], row["entity"], field,
                                      row["event_date"])
                key = (row["topic"], project, ftype, row["year"], contest,
                       row["entity"], field)
                lead = (edate - fdate).days if (fdate and edate) else None

                u = units.get(key)
                if u is None:
                    u = units[key] = {"final": None, "lead30": None}
                # final = latest forecast date on record
                if u["final"] is None or (fdate and fdate > u["final"][0]):
                    u["final"] = (fdate, p, o, lead)
                # lead30 = forecast whose lead is closest to LEAD_TARGET days
                if lead is not None and lead >= 0:
                    best = u["lead30"]
                    if best is None or abs(lead - LEAD_TARGET) < abs(best[3] - LEAD_TARGET):
                        u["lead30"] = (fdate, p, o, lead)

    print(f"  read {total:,} rows  (dropped {skipped_bad:,} unparseable, "
          f"{skipped_tie:,} non-binary)")
    print(f"  reduced to {len(units):,} forecasting units")

    # ---------------------------------------------------------------- pass 2
    # Group units by (topic, project, model, year) and, inside that, by contest.
    # The contest is the finest cluster; (project, year) is the coarsest — for
    # politics that is one election night, which is the level a shared national
    # polling error actually operates at.
    groups = defaultdict(lambda: defaultdict(list))
    for (topic, project, ftype, year, contest, entity, field), u in units.items():
        g = groups[(topic, project, ftype, year)]
        final = u["final"]
        lead30 = u["lead30"]
        rows = [("f", final)]
        # Only a genuinely earlier snapshot is a separate test of the model.
        if lead30 is not None and final is not None and lead30[0] != final[0]:
            rows.append(("l", lead30))
        for tag, rec in rows:
            if rec is None:
                continue
            _, p_, o_, lead = rec
            g[contest].append((tag, round(p_ * 1000), int(o_),
                               lead if lead is not None else -1))

    out_groups = []
    n_final = n_lead = n_contests = 0
    for (topic, project, ftype, year), contests in sorted(groups.items()):
        keys, rows_enc = [], []
        for contest in sorted(contests):
            rows = contests[contest]
            n_final += sum(1 for r in rows if r[0] == "f")
            n_lead += sum(1 for r in rows if r[0] == "l")
            keys.append(contest.split("|")[-1])          # the contest's date
            rows_enc.append(";".join(f"{t}{p_},{o_},{d}" for t, p_, o_, d in rows))
        n_contests += len(rows_enc)
        out_groups.append({"topic": topic, "project": project,
                           "model": ftype or "-", "year": int(year),
                           "dates": keys, "clusters": rows_enc})

    panel = {
        "source": "FiveThirtyEight, 'How Good Are FiveThirtyEight Forecasts?'",
        "source_url": "https://github.com/fivethirtyeight/checking-our-work-data",
        "note": ("538's own published forecast record. ABC News shut the site "
                 "down in March 2025 and took it offline; this GitHub archive is "
                 "what survived."),
        "fetched_by": "scripts/fetch_538.py",
        "fetched_at": date.today().isoformat(),
        "encoding": ("clusters[] are contests, dates[] their event dates. Each "
                     "cluster is ';'-joined rows "
                     "'<snap><prob_permille>,<outcome>,<lead_days>' where snap is "
                     "f (final forecast) or l (closest to 30 days out), outcome is "
                     "0 or 1, and lead_days is -1 when undated."),
        "excludes": ("in-play 'live' forecasts, and all but two snapshots per "
                     "forecasting unit — see data/fte-slices.json for those"),
        "lead_target_days": LEAD_TARGET,
        "n_final": n_final, "n_lead30": n_lead, "n_units": len(units),
        "n_contests": n_contests,
        "groups": out_groups,
    }

    os.makedirs(args.out, exist_ok=True)
    p1 = os.path.join(args.out, "fte-forecasts.json")
    with open(p1, "w") as fh:
        json.dump(panel, fh, separators=(",", ":"))

    for s in slices.values():
        s["bins"] = [[n, round(sp, 4), so] for n, sp, so in s["bins"]]
        for k in ("sum_p", "sum_p2", "sum_o", "sum_po"):
            s[k] = round(s[k], 4)
    p2 = os.path.join(args.out, "fte-slices.json")
    with open(p2, "w") as fh:
        json.dump({
            "source_url": panel["source_url"],
            "fetched_by": "scripts/fetch_538.py",
            "fetched_at": panel["fetched_at"],
            "note": ("Sufficient statistics for the slices the headline excludes, "
                     "so the robustness table reproduces without the 350MB archive. "
                     f"bins are {BUCKETS} equal-width probability bins, each "
                     "[count, sum_of_forecast, sum_of_outcome]."),
            "slices": dict(slices),
        }, fh, separators=(",", ":"))

    print(f"\n  wrote {p1} ({os.path.getsize(p1):,} bytes)")
    print(f"        {n_final:,} final forecasts, {n_lead:,} 30-day snapshots, "
          f"{n_contests:,} contests")
    print(f"  wrote {p2} ({os.path.getsize(p2):,} bytes)")
    for name, s in sorted(slices.items()):
        print(f"        slice {name:<22} n={s['n']:>9,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
