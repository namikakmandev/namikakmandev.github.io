#!/usr/bin/env python3
"""Discovery probe for the OECD-FAO Agricultural Outlook.

The study needs two things and only one of them is easy:

  A) the PROJECTIONS an old edition published — e.g. the 2015 Outlook's
     forecast of 2024 meat and dairy prices. Old editions are the whole point;
     scoring the current edition against itself proves nothing.
  B) what actually happened, which FAOSTAT / OWID / Eurostat already give.

This probe attacks (A). It does not parse anything and it does not decide
anything — it records what each access route returns so the real fetcher can be
written against the actual response instead of against the API docs.

Runs in GitHub Actions, which can reach OECD and FAO. The dev sandbox cannot.

  python3 scripts/probe_oecd_fao.py            # -> data/_oecd-fao-probe.json
"""
import json, os, ssl, sys, urllib.error, urllib.request
from datetime import datetime, timezone

TIMEOUT = 60
HEAD_BYTES = 1400
UA = "namikakmandev-data-probe/1.0 (+https://namikakmandev.github.io)"

# Route 1 — the current OECD SDMX API. Ask what agricultural dataflows exist
# before assuming any dataset id.
SDMX = "https://sdmx.oecd.org/public/rest"
ROUTES = [
    ("sdmx_dataflow_all_agencies",
     f"{SDMX}/dataflow/all/all/latest?format=sdmx-json"),
    ("sdmx_dataflow_TAD",
     f"{SDMX}/dataflow/OECD.TAD.ARP/all/latest?format=sdmx-json"),
    ("sdmx_dataflow_TAD_ATM",
     f"{SDMX}/dataflow/OECD.TAD.ATM/all/latest?format=sdmx-json"),
    # Route 2 — the legacy OECD.Stat SDMX-JSON endpoint. Old Outlook editions
    # were published there as HIGH_AGLINK_<year>; if any still answer, that is
    # the cleanest possible source for (A).
    *[(f"legacy_HIGH_AGLINK_{y}",
       f"https://stats.oecd.org/SDMX-JSON/data/HIGH_AGLINK_{y}/all/all"
       f"?startTime=2024&endTime=2024&dimensionAtObservation=AllDimensions")
      for y in (2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024)],
    ("legacy_dataflow_list",
     "https://stats.oecd.org/RestSDMX/sdmx.ashx/GetDataStructure/ALL"),
    # Route 3 — FAO's own copy. The Outlook is co-published, and FAO sometimes
    # posts the full database as a flat file.
    ("fao_outlook_landing",
     "https://www.fao.org/agricultural-outlook/en"),
    ("fao_outlook_data",
     "https://www.fao.org/agricultural-outlook/data/en"),
    # Route 4 — actuals, to confirm the easy half really is easy.
    ("faostat_bulk_prices",
     "https://bulks-faostat.fao.org/production/Prices_E_All_Data_(Normalized).zip"),
    ("fao_food_price_index",
     "https://www.fao.org/images/worldfoodsituationlibraries/default-document-library/"
     "food_price_indices_data_jul.csv"),
    ("owid_meat_production",
     "https://ourworldindata.org/grapher/meat-production-tonnes.csv"),
]


def attempt(name, url):
    """Fetch one route and record what came back, never raising."""
    rec = {"name": name, "url": url}
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(400_000)
            rec.update(status=r.status,
                       content_type=r.headers.get("Content-Type", ""),
                       bytes_read=len(body),
                       final_url=r.geturl())
            rec["head"] = body[:HEAD_BYTES].decode("utf-8", "replace")
            # If it parses as JSON, summarise its shape rather than dumping it.
            try:
                j = json.loads(body)
                rec["json_top_keys"] = list(j)[:25] if isinstance(j, dict) else \
                    f"list[{len(j)}]"
                flows = (j.get("data", {}) or {}).get("dataflows")
                if isinstance(flows, list):
                    hits = [{"id": f.get("id"), "name": f.get("name")}
                            for f in flows
                            if any(k in json.dumps(f).upper()
                                   for k in ("AGLINK", "OUTLOOK", "AGRICULT"))]
                    rec["agricultural_dataflows"] = hits[:60]
                    rec["dataflow_count"] = len(flows)
            except Exception:
                pass
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, error="HTTPError",
                   head=(e.read(HEAD_BYTES) or b"").decode("utf-8", "replace"))
    except Exception as e:                       # noqa: BLE001 — a probe
        rec.update(status=None, error=f"{type(e).__name__}: {e}")
    print(f"  {rec.get('status'):>5}  {name:<32} "
          f"{rec.get('bytes_read', 0):>9,}b  {rec.get('error', '')[:60]}")
    return rec


def main():
    print("OECD-FAO Agricultural Outlook — discovery probe")
    print("  looking for OLD editions' projections; actuals are the easy half\n")
    out = {"probed_at": datetime.now(timezone.utc).isoformat(),
           "probed_by": "scripts/probe_oecd_fao.py",
           "question": ("Can an old OECD-FAO Outlook edition's projections be "
                        "retrieved programmatically? Without them there is no "
                        "study."),
           "routes": [attempt(n, u) for n, u in ROUTES]}
    ok = [r for r in out["routes"] if r.get("status") == 200]
    out["summary"] = {"n_routes": len(out["routes"]), "n_ok": len(ok),
                      "ok": [r["name"] for r in ok]}
    os.makedirs("data", exist_ok=True)
    path = "data/_oecd-fao-probe.json"
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n  {len(ok)} of {len(out['routes'])} routes answered: "
          f"{[r['name'] for r in ok]}")
    print(f"  wrote {path} ({os.path.getsize(path):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
