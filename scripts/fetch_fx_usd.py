#!/usr/bin/env python3
"""Store USD cross-rates so the report does not depend on a live call.

The chart page used to fetch AUD/CZK/HUF/RON/SEK from frankfurter.app in the
browser. That works on a plain web host and fails everywhere else that matters:
a published artifact's content-security policy blocks the request outright, and
an offline copy of the report has no network at all. In both cases the page
quietly lost five markets, because a panel cannot join a shared USD scale
without a rate.

So the rates are fetched once per run, on the runner, and committed. The page
prefers this file and falls back to the live call, which means an old file is
never worse than no file.

Only rates the report actually needs are stored. rates.json already carries the
TRY pairs from TCMB and is not touched here.

Output: data/fx-usd.json
"""
import json
import pathlib
import sys
import urllib.request

WANT = ["AUD", "PLN", "CZK", "HUF", "RON", "SEK", "BGN", "DKK", "NOK", "CHF", "EUR", "GBP"]
URL = "https://api.frankfurter.app/latest?from=USD&to=" + ",".join(WANT)
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "fx-usd.json"


def main():
    try:
        with urllib.request.urlopen(URL, timeout=30) as r:
            payload = json.load(r)
    except Exception as e:                      # noqa: BLE001 - any failure is the same story
        print(f"fetch_fx_usd: {type(e).__name__}: {e}", file=sys.stderr)
        if OUT.exists():
            print("keeping the existing file rather than truncating it")
            return 0
        print("no existing file to keep; the report will fall back to its live call")
        return 0

    rates = payload.get("rates") or {}
    # Stored as CURRENCY->USD, which is the direction the page multiplies by.
    # A zero or missing rate is dropped rather than stored as null: a null would
    # read as "we know it is nothing".
    usd = {c: 1.0 / v for c, v in rates.items() if isinstance(v, (int, float)) and v > 0}
    if not usd:
        print("fetch_fx_usd: response carried no usable rates", file=sys.stderr)
        return 0

    missing = [c for c in WANT if c not in usd]
    OUT.write_text(json.dumps({
        "asof": payload.get("date"),
        "base": "USD",
        "source": "frankfurter.app (ECB reference rates)",
        "note": "CURRENCY->USD multipliers. Fetched on the runner so the report "
                "works inside a CSP-restricted artifact and offline.",
        "usd": {c: round(v, 8) for c, v in sorted(usd.items())},
    }, indent=1) + "\n")
    print(f"wrote {OUT.name}: {len(usd)} rates as of {payload.get('date')}"
          + (f"; not returned: {', '.join(missing)}" if missing else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
