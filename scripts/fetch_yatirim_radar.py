#!/usr/bin/env python3
"""
Yatırım Radarı — data/yatirim-radar.json üretir.

BIST hisseleri + kıymetli madenler + emtialar için Yahoo Finance'ten 2 yıllık
günlük fiyat serisi çeker; teknik göstergeleri (SMA 20/50/100/180/200, RSI-14,
MACD, momentum, volatilite, 52 hafta bandı) ve hisseler için temel rasyoları
(F/K, PD/DD, ROE, temettü, borçluluk) hesaplar; hepsini 0-100 arası bir bileşik
skora indirger ve yatirim-radar.html'in beklediği JSON'u yazar.

GitHub Action (.github/workflows/yatirim-radar.yml) tarafından zamanlanmış
olarak çalıştırılır. Anahtar gerektirmez; chart API keyless, quoteSummary
cookie+crumb ile açılır (bkz. scripts/fetch.py'deki aynı desen).
"""
import http.cookiejar
import json
import math
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

OUT_PATH = os.environ.get("OUT_PATH", "data/yatirim-radar.json")
# FAST=1: gün içi 15 dk'lık koşular — fiyat/teknikleri tazele, rasyo ve haberleri
# önceki JSON'dan taşı (quoteSummary + RSS'i her çeyrek saat sorgulamamak için)
FAST = os.environ.get("FAST", "").strip() == "1"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TROY_OUNCE_G = 31.1034768

# sembol -> (ad, tür)  türler: hisse (BIST) | abd (NASDAQ/NYSE) | maden | emtia | endeks | doviz
UNIVERSE = {
    # --- ABD hisseleri (NASDAQ) ---
    "AAPL": ("Apple", "abd"),
    "MSFT": ("Microsoft", "abd"),
    "NVDA": ("Nvidia", "abd"),
    "GOOGL": ("Alphabet (Google)", "abd"),
    "AMZN": ("Amazon", "abd"),
    "META": ("Meta Platforms", "abd"),
    "TSLA": ("Tesla", "abd"),
    "AVGO": ("Broadcom", "abd"),
    "NFLX": ("Netflix", "abd"),
    # --- ABD hisseleri (NYSE) ---
    "BRK-B": ("Berkshire Hathaway", "abd"),
    "JPM": ("JPMorgan Chase", "abd"),
    "V": ("Visa", "abd"),
    "XOM": ("ExxonMobil", "abd"),
    "JNJ": ("Johnson & Johnson", "abd"),
    "WMT": ("Walmart", "abd"),
    "KO": ("Coca-Cola", "abd"),
    "PG": ("Procter & Gamble", "abd"),
    "LLY": ("Eli Lilly", "abd"),
    # --- ABD endeksleri ---
    "^GSPC": ("S&P 500", "endeks"),
    "^IXIC": ("Nasdaq Composite", "endeks"),
    "^DJI": ("Dow Jones", "endeks"),
    "THYAO.IS": ("Türk Hava Yolları", "hisse"),
    "TUPRS.IS": ("Tüpraş", "hisse"),
    "BIMAS.IS": ("BİM Mağazalar", "hisse"),
    "ASELS.IS": ("Aselsan", "hisse"),
    "EREGL.IS": ("Ereğli Demir Çelik", "hisse"),
    "KCHOL.IS": ("Koç Holding", "hisse"),
    "SAHOL.IS": ("Sabancı Holding", "hisse"),
    "SISE.IS": ("Şişecam", "hisse"),
    "AKBNK.IS": ("Akbank", "hisse"),
    "GARAN.IS": ("Garanti BBVA", "hisse"),
    "ISCTR.IS": ("İş Bankası (C)", "hisse"),
    "YKBNK.IS": ("Yapı Kredi", "hisse"),
    "FROTO.IS": ("Ford Otosan", "hisse"),
    "TOASO.IS": ("Tofaş Oto", "hisse"),
    "TCELL.IS": ("Turkcell", "hisse"),
    "TTKOM.IS": ("Türk Telekom", "hisse"),
    "PGSUS.IS": ("Pegasus", "hisse"),
    "ENKAI.IS": ("Enka İnşaat", "hisse"),
    "ARCLK.IS": ("Arçelik", "hisse"),
    "TAVHL.IS": ("TAV Havalimanları", "hisse"),
    "PETKM.IS": ("Petkim", "hisse"),
    "MGROS.IS": ("Migros", "hisse"),
    "GC=F": ("Altın (ons)", "maden"),
    "SI=F": ("Gümüş (ons)", "maden"),
    "PL=F": ("Platin (ons)", "maden"),
    "PA=F": ("Paladyum (ons)", "maden"),
    "HG=F": ("Bakır", "emtia"),
    "BZ=F": ("Brent Petrol", "emtia"),
    "XU100.IS": ("BIST 100", "endeks"),
    "USDTRY=X": ("Dolar/TL", "doviz"),
}


def get(url, opener=None, timeout=45, retries=3):
    for attempt in range(retries):
        try:
            if opener:
                return opener.open(url, timeout=timeout).read()
            req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA,
                                                       "Accept": "*/*"})
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(4 * 2 ** attempt)


def fetch_chart(sym):
    """2 yıllık günlük seri -> ({ts: close}, currency). Boşluklar atlanır."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(sym)}?range=2y&interval=1d")
    j = json.loads(get(url).decode())
    r = ((j.get("chart") or {}).get("result") or [{}])[0]
    ts = r.get("timestamp") or []
    q = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    closes = q.get("close") or []
    series = {}
    for t, c in zip(ts, closes):
        if c is not None:
            series[time.strftime("%Y-%m-%d", time.gmtime(t))] = float(c)
    cur = (r.get("meta") or {}).get("currency")
    return series, cur


def sma(vals, n, i=None):
    i = len(vals) if i is None else i
    if i < n:
        return None
    return sum(vals[i - n:i]) / n


def rsi14(vals, n=14):
    if len(vals) < n + 1:
        return None
    gains = losses = 0.0
    for k in range(1, n + 1):
        d = vals[k] - vals[k - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    ag, al = gains / n, losses / n
    for k in range(n + 1, len(vals)):
        d = vals[k] - vals[k - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)


def ema_series(vals, n):
    if not vals:
        return []
    k = 2 / (n + 1)
    out = [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def macd_hist(vals):
    if len(vals) < 35:
        return None
    macd = [a - b for a, b in zip(ema_series(vals, 12), ema_series(vals, 26))]
    signal = ema_series(macd, 9)
    return macd[-1] - signal[-1]


def ret(vals, days):
    if len(vals) <= days:
        return None
    base = vals[-1 - days]
    return vals[-1] / base - 1 if base else None


def ann_vol(vals, days=30):
    if len(vals) < days + 1:
        return None
    rets = [math.log(vals[i] / vals[i - 1]) for i in range(len(vals) - days, len(vals))
            if vals[i - 1] > 0]
    if len(rets) < 2:
        return None
    m = sum(rets) / len(rets)
    var = sum((r - m) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(252)


def technicals(closes):
    p = closes[-1]
    t = {
        "price": p,
        "chg1d": (p / closes[-2] - 1) if len(closes) > 1 and closes[-2] else None,
        "sma20": sma(closes, 20), "sma50": sma(closes, 50),
        "sma100": sma(closes, 100), "sma180": sma(closes, 180),
        "sma200": sma(closes, 200),
        "rsi14": rsi14(closes[-260:]),
        "macd_hist": macd_hist(closes[-260:]),
        "r1m": ret(closes, 21), "r3m": ret(closes, 63),
        "r6m": ret(closes, 126), "r12m": ret(closes, 252),
        "vol30": ann_vol(closes),
    }
    yr = closes[-252:]
    t["hi52"], t["lo52"] = max(yr), min(yr)
    t["from_hi52"] = p / t["hi52"] - 1 if t["hi52"] else None
    t["pos52"] = ((p - t["lo52"]) / (t["hi52"] - t["lo52"])
                  if t["hi52"] and t["hi52"] != t["lo52"] else None)
    for key, s in (("vs_sma180", t["sma180"]), ("vs_sma200", t["sma200"])):
        t[key] = p / s - 1 if s else None
    s200_prev = sma(closes, 200, len(closes) - 20)
    t["sma200_slope20"] = (t["sma200"] / s200_prev - 1) if t["sma200"] and s200_prev else None
    return t


def clamp01(x):
    return max(0.0, min(1.0, x))


def lin(x, lo, hi):
    """x'i [lo,hi] aralığından [0,1]'e doğrusal taşı (eksiği/fazlası kırpılır)."""
    if x is None or hi == lo:
        return None
    return clamp01((x - lo) / (hi - lo))


def score_asset(t, f, is_stock):
    trend = 0.0
    for w, v in ((10, lin(t.get("vs_sma200"), -0.20, 0.20)),
                 (10, lin(t.get("vs_sma180"), -0.20, 0.20)),
                 (8, lin((t["sma50"] / t["sma200"] - 1) if t.get("sma50") and t.get("sma200") else None,
                         -0.10, 0.10)),
                 (7, lin(t.get("sma200_slope20"), -0.05, 0.05))):
        trend += w * (v if v is not None else 0.5)

    mom = 0.0
    for w, v in ((9, lin(t.get("r3m"), -0.25, 0.25)),
                 (8, lin(t.get("r6m"), -0.40, 0.40))):
        mom += w * (v if v is not None else 0.5)
    rsi = t.get("rsi14")
    mom += 8 * (max(0.0, 1 - abs(rsi - 57.5) / 32.5) if rsi is not None else 0.5)

    risk = 0.0
    vol = t.get("vol30")
    risk += 8 * (lin(0.80 - vol, 0, 0.65) if vol is not None else 0.5)
    fh = t.get("from_hi52")
    risk += 7 * (clamp01(1 + fh / 0.50) if fh is not None else 0.5)

    value = None
    if is_stock:
        value = 0.0
        pe = (f or {}).get("trailing_pe")
        value += 9 * (lin(40 - pe, 0, 36) if pe and pe > 0 else 0.33)
        pb = (f or {}).get("price_to_book")
        value += 7 * (lin(6 - pb, 0, 5.5) if pb and pb > 0 else 0.43)
        roe = (f or {}).get("roe")
        value += 5 * (lin(roe, 0, 0.40) if roe is not None else 0.4)
        dy = (f or {}).get("dividend_yield")
        value += 4 * (lin(dy, 0, 0.06) if dy is not None else 0.25)

    max_pts = 75 + (25 if value is not None else 0)
    got = trend + mom + risk + (value or 0)
    total = round(got / max_pts * 100, 1)
    label = "Olumlu" if total >= 65 else ("Nötr" if total >= 45 else "Zayıf")
    return {"total": total, "trend": round(trend, 1), "momentum": round(mom, 1),
            "value": round(value, 1) if value is not None else None,
            "risk": round(risk, 1), "label": label}


def _num(v):
    """Yahoo sayıları {'raw':x,'fmt':...} sarar; aç, düz sayıyı/None'ı tolere et."""
    if isinstance(v, dict):
        v = v.get("raw")
    return v if isinstance(v, (int, float)) else None


def yahoo_session():
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", BROWSER_UA), ("Accept", "*/*"),
                     ("Accept-Language", "en-US,en;q=0.9")]
    for seed in ("https://fc.yahoo.com", "https://finance.yahoo.com/quote/AAPL"):
        try:
            op.open(seed, timeout=30).read()
        except Exception:
            pass  # 404/403 olabilir — sadece Set-Cookie lazım
    last = None
    for attempt in range(6):
        for host in ("query1", "query2"):
            try:
                c = op.open(f"https://{host}.finance.yahoo.com/v1/test/getcrumb",
                            timeout=30).read().decode().strip()
                if c and "<" not in c:
                    return op, c
                last = f"empty crumb from {host}"
            except Exception as ex:
                last = f"{type(ex).__name__}: {ex}"
        time.sleep(min(60, 5 * 2 ** attempt))
    raise RuntimeError(f"crumb alınamadı: {last}")


def fetch_fundamentals(op, crumb, sym):
    mods = "defaultKeyStatistics,summaryDetail,financialData,price,earningsTrend"
    url = ("https://query1.finance.yahoo.com/v10/finance/quoteSummary/"
           f"{urllib.parse.quote(sym)}?modules={mods}&crumb={urllib.parse.quote(crumb)}")
    j = json.loads(get(url, opener=op).decode())
    res = ((j.get("quoteSummary") or {}).get("result") or [None])[0]
    if not res:
        return None
    ks = res.get("defaultKeyStatistics") or {}
    sd = res.get("summaryDetail") or {}
    fd = res.get("financialData") or {}
    pr = res.get("price") or {}
    # PEG'i kendimiz hesaplarız: Yahoo'nun hazır pegRatio'su güvenilmez (bkz.
    # fetch.py notu). Büyüme: önce analist konsensüsü (+1y), yoksa gerçekleşen
    # yıllık kâr büyümesi. F/K: önce ileriye dönük, yoksa cari.
    growth_1y = None
    for tr in (res.get("earningsTrend") or {}).get("trend", []):
        if tr.get("period") == "+1y":
            growth_1y = _num(tr.get("growth"))
    growth = growth_1y if (growth_1y and growth_1y > 0) else _num(fd.get("earningsGrowth"))
    pe_for_peg = _num(sd.get("forwardPE")) or _num(sd.get("trailingPE"))
    peg = None
    if pe_for_peg and pe_for_peg > 0 and growth and growth > 0.01:
        peg = round(pe_for_peg / (growth * 100), 2)
    return {
        "peg": peg,
        "peg_growth": growth,
        "yahoo_peg": _num(ks.get("pegRatio")),
        "long_name": pr.get("longName") or pr.get("shortName"),
        "market_cap": _num(pr.get("marketCap")),
        "trailing_pe": _num(sd.get("trailingPE")),
        "forward_pe": _num(sd.get("forwardPE")),
        "price_to_book": _num(ks.get("priceToBook")),
        "price_to_sales": _num(sd.get("priceToSalesTrailing12Months")),
        "trailing_eps": _num(ks.get("trailingEps")),
        "beta": _num(ks.get("beta")),
        "dividend_yield": _num(sd.get("dividendYield")),
        "roe": _num(fd.get("returnOnEquity")),
        "profit_margin": _num(fd.get("profitMargins")),
        "debt_to_equity": _num(fd.get("debtToEquity")),
        "revenue_growth": _num(fd.get("revenueGrowth")),
        "earnings_growth": _num(fd.get("earningsGrowth")),
        "target_mean": _num(fd.get("targetMeanPrice")),
        "analysts": _num(fd.get("numberOfAnalystOpinions")),
        "recommendation": fd.get("recommendationKey"),
    }


def fetch_news(sym, limit=3):
    url = ("https://feeds.finance.yahoo.com/rss/2.0/headline?s="
           f"{urllib.parse.quote(sym)}&region=US&lang=en-US")
    try:
        root = ET.fromstring(get(url, timeout=20, retries=1).decode("utf-8", "replace"))
        items = []
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            date = (it.findtext("pubDate") or "").strip()
            if title:
                items.append({"t": title, "u": link, "d": date})
            if len(items) >= limit:
                break
        return items
    except Exception:
        return []


def spark(closes, dates, points=125, step=2):
    """Son ~1 yılın kapanış + SMA180/200 örneklemi (grafik için)."""
    n = len(closes)
    idx = list(range(max(0, n - points * step), n, step))
    if idx and idx[-1] != n - 1:
        idx.append(n - 1)
    rnd = lambda v: round(v, 4) if v is not None else None
    return {
        "close": [rnd(closes[i]) for i in idx],
        "sma180": [rnd(sma(closes, 180, i + 1)) for i in idx],
        "sma200": [rnd(sma(closes, 200, i + 1)) for i in idx],
        "start": dates[idx[0]] if idx else None,
        "end": dates[idx[-1]] if idx else None,
    }


def main():
    charts, errors = {}, []
    prev = {}
    if FAST:
        try:
            with open(OUT_PATH, encoding="utf-8") as fh:
                prev = {a["symbol"]: a for a in json.load(fh)["assets"]}
        except Exception as ex:
            errors.append(f"FAST: önceki JSON okunamadı ({ex}); tam mod")
    for n, sym in enumerate(UNIVERSE):
        if n:
            time.sleep(0.6)  # Actions IP'leri kolay 429 yer — yavaş git
        try:
            series, cur = fetch_chart(sym)
            if len(series) < 220:
                raise RuntimeError(f"yetersiz veri ({len(series)} gün)")
            charts[sym] = (series, cur)
            print(f"chart  {sym:10s} {len(series)} gün")
        except Exception as ex:
            errors.append(f"{sym}: chart {type(ex).__name__}: {ex}")
            print(f"chart  {sym:10s} HATA {ex}")

    # Gram altın (TL) = ons altın / 31.1035 × USD/TRY — tarih kesişimiyle türet
    if "GC=F" in charts and "USDTRY=X" in charts:
        gold, fx = charts["GC=F"][0], charts["USDTRY=X"][0]
        common = sorted(set(gold) & set(fx))
        if len(common) >= 220:
            charts["GRAMALTIN"] = ({d: gold[d] / TROY_OUNCE_G * fx[d] for d in common}, "TRY")

    op = crumb = None
    if not prev:  # FAST modunda rasyolar önceki JSON'dan gelir, oturum gereksiz
        try:
            op, crumb = yahoo_session()
        except Exception as ex:
            errors.append(f"quoteSummary oturumu açılamadı: {ex}")

    assets = []
    for sym, (series, cur) in charts.items():
        dates = sorted(series)
        closes = [series[d] for d in dates]
        name, typ = UNIVERSE.get(sym, ("Gram Altın (TL)", "maden"))
        t = technicals(closes)

        fund = None
        if typ in ("hisse", "abd"):
            if prev:
                fund = (prev.get(sym) or {}).get("fund")
            elif crumb:
                try:
                    time.sleep(1.5)
                    fund = fetch_fundamentals(op, crumb, sym)
                except Exception as ex:
                    errors.append(f"{sym}: fundamentals {type(ex).__name__}: {ex}")

        if prev:
            news = (prev.get(sym) or {}).get("news") or []
        else:
            news = fetch_news(sym) if sym in UNIVERSE else []

        rnd = lambda v, p=4: round(v, p) if isinstance(v, float) else v
        assets.append({
            "symbol": sym, "name": name, "type": typ, "currency": cur,
            "tech": {k: rnd(v, 6 if k in ("chg1d", "sma200_slope20") else 4)
                     for k, v in t.items()},
            "fund": fund,
            "score": score_asset(t, fund, typ in ("hisse", "abd")),
            "spark": spark(closes, dates),
            "news": news,
        })

    assets.sort(key=lambda a: -a["score"]["total"])
    out = {
        "asof": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "assets": assets,
        "errors": errors,
    }
    os.makedirs(os.path.dirname(OUT_PATH) or ".", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"\n{OUT_PATH}: {len(assets)} varlık, {len(errors)} hata")
    for e in errors:
        print("  !", e)


if __name__ == "__main__":
    main()
