#!/usr/bin/env python3
"""
Build the Dealer Diagnostic demo's OWN macro snapshot (dealer-demo/rates.json).

Independent of ASSETIX: this is a self-contained copy with its own GitHub
Action (.github/workflows/dealer-demo-macro.yml). It fetches live FX + TCMB
EVDS data and writes dealer-demo/rates.json, which the demo reads directly.
Reads the EVDS key from the EVDS_KEY environment variable (a GitHub secret);
the key is NEVER written into the output — only the resulting public figures.

Output shape matches what dealer-demo/index.html expects (j.fx / j.rate / j.market).
"""
import os, json, ssl, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

EVDS_KEY          = os.environ.get("EVDS_KEY", "").strip()
EVDS_SERIES       = os.environ.get("EVDS_SERIES", "TP.BISPOLFAIZ.TUR").strip()
INTEREST_FALLBACK = float(os.environ.get("INTEREST_FALLBACK", "37.0"))
OUT_PATH          = os.environ.get("OUT_PATH", "dealer-demo/rates.json").strip()

PAIRS = ["USD/TRY", "EUR/TRY", "GBP/TRY"]
_SSL = ssl.create_default_context()


def _get_json(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "dealer-macro/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
        return json.loads(r.read().decode("utf-8"))


def fx_frankfurter():
    url = "https://api.frankfurter.dev/v1/latest?base=USD&symbols=TRY,EUR,GBP"
    j = _get_json(url)
    r = j["rates"]
    out = {"USDTRY": float(r["TRY"])}
    if r.get("EUR"): out["EURTRY"] = round(float(r["TRY"]) / float(r["EUR"]), 4)
    if r.get("GBP"): out["GBPTRY"] = round(float(r["TRY"]) / float(r["GBP"]), 4)
    return {"fx": out, "source": "Frankfurter (ECB)", "realtime": False, "asof": j.get("date", "")}


def _evds():
    from evds import evdsAPI
    return evdsAPI(EVDS_KEY)


def get_rate():
    """TL policy rate from TCMB EVDS."""
    if not EVDS_KEY:
        return {"value": INTEREST_FALLBACK, "source": "manuel (varsayilan)", "asof": ""}
    try:
        api = _evds()
        end = datetime.now(); start = end - timedelta(days=730)
        df = api.get_data([EVDS_SERIES], startdate=start.strftime("%d-%m-%Y"), enddate=end.strftime("%d-%m-%Y"))
        col = EVDS_SERIES.replace(".", "_")
        valid = df[df[col].notna()]
        if len(valid) == 0:
            raise RuntimeError("no values for " + EVDS_SERIES)
        row = valid.iloc[-1]
        return {"value": float(row[col]), "source": "TCMB EVDS (" + EVDS_SERIES + ")", "asof": str(row.get("Tarih", ""))}
    except Exception as ex:
        print("[rate] EVDS failed:", repr(ex))
        return {"value": INTEREST_FALLBACK, "source": "manuel (EVDS hatasi)", "asof": ""}


RATE_SERIES = {"deposit": "TP.TRY.MT02", "loan_comm": "TP.KTF17"}
TUFE_SERIES = "TP.FE.OKTG01"


def get_market():
    """Deposit/commercial-loan rates + CPI (TÜFE, with YoY) from TCMB EVDS."""
    if not EVDS_KEY:
        return {}
    out = {}
    try:
        api = _evds(); end = datetime.now()
        try:
            rs = (end - timedelta(days=120)).strftime("%d-%m-%Y")
            df = api.get_data(list(RATE_SERIES.values()), startdate=rs, enddate=end.strftime("%d-%m-%Y"))
            for k, code in RATE_SERIES.items():
                col = code.replace(".", "_")
                if col in df.columns:
                    s = df[df[col].notna()]
                    if len(s):
                        out[k] = {"value": round(float(s.iloc[-1][col]), 2), "asof": str(s.iloc[-1].get("Tarih", ""))}
        except Exception as e:
            print("[market rates]", repr(e))
        try:
            is_ = (end - timedelta(days=900)).strftime("%d-%m-%Y")
            df = api.get_data([TUFE_SERIES], startdate=is_, enddate=end.strftime("%d-%m-%Y"))
            col = TUFE_SERIES.replace(".", "_")
            if col in df.columns:
                s = df[df[col].notna()].reset_index(drop=True)
                if len(s):
                    last = float(s.iloc[-1][col]); asof = str(s.iloc[-1].get("Tarih", ""))
                    yoy = None
                    if len(s) >= 13:
                        prev = float(s.iloc[-13][col])
                        if prev:
                            yoy = round((last / prev - 1) * 100, 1)
                    out["tufe"] = {"value": round(last, 2), "yoy": yoy, "asof": asof}
        except Exception as e:
            print("[tufe]", repr(e))
    except Exception as ex:
        print("[market] failed:", repr(ex))
    return out


def build_payload():
    fx = fx_frankfurter(); rate = get_rate(); market = get_market()
    return {"fx": fx["fx"], "fxSource": fx["source"], "fxRealtime": fx["realtime"],
            "fxAsof": fx["asof"], "rate": rate, "market": market,
            "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cacheTtl": 0}


if __name__ == "__main__":
    payload = build_payload()
    os.makedirs(os.path.dirname(OUT_PATH) or ".", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print("Wrote", OUT_PATH,
          "| fx:", payload["fx"].get("USDTRY"),
          "| rate:", payload["rate"].get("value"),
          "| market keys:", list(payload["market"].keys()))
