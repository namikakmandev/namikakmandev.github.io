#!/usr/bin/env python3
"""
Build ASSETIX rates.json — a static snapshot of live FX + TCMB EVDS data.

Run by the GitHub Action (.github/workflows/update-rates.yml) on a schedule.
Reads the EVDS key from the EVDS_KEY environment variable (a GitHub secret),
fetches the data, and writes rates.json next to the website files. The key is
NEVER written into the output — only the resulting public figures are.

Output JSON shape matches what assetix.html expects (j.fx / j.rate / j.market).
"""
import os, json, ssl, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

TWELVEDATA_KEY    = os.environ.get("TWELVEDATA_KEY", "").strip()
EVDS_KEY          = os.environ.get("EVDS_KEY", "").strip()
EVDS_SERIES       = os.environ.get("EVDS_SERIES", "TP.BISPOLFAIZ.TUR").strip()
INTEREST_FALLBACK = float(os.environ.get("INTEREST_FALLBACK", "37.0"))
OUT_PATH          = os.environ.get("OUT_PATH", "rates.json").strip()

PAIRS = ["USD/TRY", "EUR/TRY", "GBP/TRY"]
_SSL = ssl.create_default_context()


def _get_json(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "assetix-rates/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
        return json.loads(r.read().decode("utf-8"))


def fx_twelvedata():
    sym = ",".join(PAIRS)
    url = ("https://api.twelvedata.com/exchange_rate?symbol="
           + urllib.parse.quote(sym) + "&apikey=" + urllib.parse.quote(TWELVEDATA_KEY))
    j = _get_json(url)
    out = {}
    items = j if (PAIRS[0] in j) else {sym.split(",")[0]: j}
    for p in PAIRS:
        node = items.get(p) or {}
        if "rate" in node:
            out[p.replace("/", "")] = float(node["rate"])
    if "USDTRY" not in out:
        raise RuntimeError("Twelve Data: unexpected response " + json.dumps(j)[:200])
    return {"fx": out, "source": "Twelve Data", "realtime": True,
            "asof": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def fx_frankfurter():
    url = "https://api.frankfurter.dev/v1/latest?base=USD&symbols=TRY,EUR,GBP"
    j = _get_json(url)
    r = j["rates"]
    out = {"USDTRY": float(r["TRY"])}
    if r.get("EUR"): out["EURTRY"] = round(float(r["TRY"]) / float(r["EUR"]), 4)
    if r.get("GBP"): out["GBPTRY"] = round(float(r["TRY"]) / float(r["GBP"]), 4)
    return {"fx": out, "source": "Frankfurter (ECB)", "realtime": False, "asof": j.get("date", "")}


def get_fx():
    if TWELVEDATA_KEY:
        try:
            return fx_twelvedata()
        except Exception as e:
            print("[fx] Twelve Data failed, falling back to ECB:", e)
    return fx_frankfurter()


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


RATE_SERIES = {"deposit": "TP.TRY.MT02", "loan_home": "TP.KTF12", "loan_comm": "TP.KTF17"}
INDEX_SERIES = {"kfe_tr": "TP.KFE.TR", "kfe_ist": "TP.KFE.TR10",
                "kfe_ank": "TP.KFE.TR51", "kfe_izm": "TP.KFE.TR31", "tufe": "TP.FE.OKTG01"}


def get_market():
    """Deposit/loan rates + House Price Index + CPI from TCMB EVDS."""
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
            is_ = (end - timedelta(days=800)).strftime("%d-%m-%Y")
            df = api.get_data(list(INDEX_SERIES.values()), startdate=is_, enddate=end.strftime("%d-%m-%Y"))
            for k, code in INDEX_SERIES.items():
                col = code.replace(".", "_")
                if col in df.columns:
                    s = df[df[col].notna()].reset_index(drop=True)
                    if len(s):
                        last = float(s.iloc[-1][col]); asof = str(s.iloc[-1].get("Tarih", ""))
                        yoy = None
                        if len(s) >= 13:
                            prev = float(s.iloc[-13][col])
                            if prev:
                                yoy = round((last / prev - 1) * 100, 1)
                        out[k] = {"value": round(last, 2), "yoy": yoy, "asof": asof}
            try:
                trcol = "TP_KFE_TR"
                dfh = df[df[trcol].notna()] if trcol in df.columns else df
                def _arr(code):
                    c = code.replace(".", "_")
                    if c not in dfh.columns:
                        return []
                    return [(round(float(v), 1) if v == v else None) for v in dfh[c].tolist()][-24:]
                dates = [str(x) for x in dfh["Tarih"].tolist()][-24:] if "Tarih" in dfh.columns else []
                out["kfe_hist"] = {"dates": dates, "tr": _arr("TP.KFE.TR"),
                                   "ist": _arr("TP.KFE.TR10"), "ank": _arr("TP.KFE.TR51"),
                                   "izm": _arr("TP.KFE.TR31")}
            except Exception as e2:
                print("[market hist]", repr(e2))
        except Exception as e:
            print("[market index]", repr(e))
    except Exception as ex:
        print("[market] failed:", repr(ex))
    return out


def build_payload():
    fx = get_fx(); rate = get_rate(); market = get_market()
    return {"fx": fx["fx"], "fxSource": fx["source"], "fxRealtime": fx["realtime"],
            "fxAsof": fx["asof"], "rate": rate, "market": market,
            "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cacheTtl": 0}


if __name__ == "__main__":
    payload = build_payload()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print("Wrote", OUT_PATH,
          "| fx:", payload["fx"].get("USDTRY"),
          "| rate:", payload["rate"].get("value"),
          "| market keys:", list(payload["market"].keys()))
