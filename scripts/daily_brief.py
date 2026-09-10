#!/usr/bin/env python3
"""The front page: ask the site's own assistant to write today's brief from today's data.

Runs after whats_moving.py in the fetch workflow. Sends the "what moved" note and the
list of series due to the Worker's /v1/ask in mode "brief"; the model reads it, checks
with the tools, adds forecasts and correlations, and streams back markdown. The result is
kept as a back issue in data/briefs/YYYY-MM-DD.json, as the latest in data/_brief.json,
and listed in data/briefs/index.json. brief.html draws them.

A failure leaves the previous brief in place and exits 0, so a bad morning at the model
never blocks the data commit.

    WORKER_URL=https://econ-mcp.akmannamik83.workers.dev python3 scripts/daily_brief.py
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKER = os.environ.get("WORKER_URL", "https://econ-mcp.akmannamik83.workers.dev").rstrip("/")
UA = {"User-Agent": "namikakmandev.github.io daily brief (GitHub Actions)"}


def load(name):
    return json.load(open(os.path.join(ROOT, "data", name)))


def due_series(catalog, today):
    """Monthly datasets whose latest month is the one before this one: their next number is due."""
    y, m = int(today[:4]), int(today[5:7])
    prev = f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"
    due = []
    for d in catalog["datasets"]:
        last = str((d.get("coverage") or {}).get("last") or "")
        if re.match(r"^\d{4}-\d{2}$", last) and last <= prev:
            due.append({"dataset": d["file"].replace("data/", "").replace(".json", ""), "last": last})
    return sorted(due, key=lambda x: x["last"])[:25]


def build_context(today):
    moves = load("_moves.json")
    catalog = load("_catalog.json")
    items = []
    for it in moves.get("items", []):
        items.append({k: it.get(k) for k in ("dataset", "series", "subject", "title", "label", "unit", "frequency",
                                             "latest", "year_ago", "change", "is_rate", "in_points", "z", "mean_change",
                                             "since", "first", "sentence", "new", "source")})
    return {
        "date": today,
        "what_moved": {"generated": moves.get("generated"), "new_since_previous": moves.get("new_since_previous"), "items": items},
        "series_due": due_series(catalog, today),
        "collection": {"datasets": catalog.get("totals", {}).get("datasets"), "observations": catalog.get("totals", {}).get("observations")},
    }


def stream_brief(context):
    """POST to /v1/ask and read Anthropic's server-sent events; return text, chart urls, usage."""
    body = json.dumps({"mode": "brief", "context": json.dumps(context, ensure_ascii=False)}).encode("utf-8")
    req = urllib.request.Request(WORKER + "/v1/ask", data=body, headers={**UA, "content-type": "application/json"})
    text, charts, usage, tools, stop = [], [], {}, 0, None
    with urllib.request.urlopen(req, timeout=900) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        buf = b""
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            buf += chunk
            while b"\n\n" in buf:
                evt, buf = buf.split(b"\n\n", 1)
                for line in evt.decode("utf-8", "replace").split("\n"):
                    if not line.startswith("data:"):
                        continue
                    try:
                        d = json.loads(line[5:].strip())
                    except ValueError:
                        continue
                    t = d.get("type")
                    if t == "content_block_start":
                        b = d.get("content_block") or {}
                        if b.get("type") in ("mcp_tool_use", "server_tool_use", "tool_use"):
                            tools += 1
                        elif b.get("type") == "mcp_tool_result":
                            for c in b.get("content") or []:
                                if isinstance(c, dict) and c.get("type") == "text":
                                    charts += re.findall(r"https?://\S+chart\.html#[A-Za-z0-9_\-]+", c.get("text", ""))
                        elif b.get("type") == "text" and text and not text[-1].endswith("\n"):
                            text.append("\n\n")
                    elif t == "content_block_delta":
                        delta = d.get("delta") or {}
                        if delta.get("type") == "text_delta":
                            text.append(delta.get("text", ""))
                    elif t == "message_start":
                        usage.update((d.get("message") or {}).get("usage") or {})
                    elif t == "message_delta":
                        usage.update(d.get("usage") or {})
                        if (d.get("delta") or {}).get("stop_reason"):
                            stop = d["delta"]["stop_reason"]
                    elif t == "error":
                        raise RuntimeError(str((d.get("error") or {}).get("message") or "stream error"))
    return "".join(text), sorted(set(charts)), usage, tools, stop


def main():
    today = time.strftime("%Y-%m-%d", time.gmtime())
    context = build_context(today)
    started = time.time()
    try:
        text, charts, usage, tools, stop = stream_brief(context)
    except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, TimeoutError) as e:
        print(f"[warn] brief not written: {e}", file=sys.stderr)
        return 0
    if len(text.strip()) < 800:
        print(f"[warn] brief too short ({len(text)} chars), kept the previous one", file=sys.stderr)
        return 0
    m = re.search(r"^#\s+(.+)$", text, re.M)
    headline = m.group(1).strip() if m else text.strip().split("\n")[0][:120]
    out = {
        "date": today,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "headline": headline,
        "text": text.strip(),
        "charts": charts,
        "tool_calls": tools,
        "stop_reason": stop,
        "usage": usage,
        "seconds": round(time.time() - started),
        "moves_generated": context["what_moved"]["generated"],
        "model": "claude-opus-5 via /v1/ask mode brief",
    }
    os.makedirs(os.path.join(ROOT, "data", "briefs"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "briefs", today + ".json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    with open(os.path.join(ROOT, "data", "_brief.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    index_path = os.path.join(ROOT, "data", "briefs", "index.json")
    try:
        index = json.load(open(index_path))
    except Exception:
        index = {"issues": []}
    index["issues"] = [i for i in index.get("issues", []) if i.get("date") != today]
    index["issues"].insert(0, {"date": today, "headline": headline, "charts": len(charts)})
    index["issues"] = sorted(index["issues"], key=lambda i: i["date"], reverse=True)[:400]
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"brief written: {headline!r}, {len(text)} chars, {tools} tool calls, {out['seconds']} s, usage {usage}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
