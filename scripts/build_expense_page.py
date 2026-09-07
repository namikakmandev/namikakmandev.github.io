#!/usr/bin/env python3
"""Inject the expense-control rules into harcama-sifreli.html.

The page and the CLI share one set of parsing and category rules, which live in
tools/expense-control/rules/. This copies the current rules into the two
<script type="application/json"> blocks in the page, so nothing has to be kept
in sync by hand. Run it after editing either rules file:

    python3 scripts/build_expense_page.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "harcama-sifreli.html"
RULES = ROOT / "tools" / "expense-control" / "rules"

BLOCKS = {
    "rules-statement": RULES / "garanti-bbva.json",
    "rules-categories": RULES / "categories.json",
}


def main():
    html = PAGE.read_text(encoding="utf-8")
    for element_id, source in BLOCKS.items():
        data = json.loads(source.read_text(encoding="utf-8"))
        # Drop the prose keys the page has no use for, and keep it compact.
        data = {k: v for k, v in data.items() if not k.endswith("note")}
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        if "</script" in payload:
            sys.exit(f"{source.name}: contains '</script', refusing to inline")
        pattern = re.compile(
            r'(<script id="' + element_id + r'" type="application/json">).*?(</script>)',
            re.S)
        html, count = pattern.subn(lambda m: m.group(1) + payload + m.group(2), html)
        if count != 1:
            sys.exit(f"{PAGE.name}: expected one #{element_id} block, found {count}")
        print(f"  {element_id:<18} <- {source.name}  ({len(payload):,} bytes)")
    PAGE.write_text(html, encoding="utf-8")
    print(f"  wrote {PAGE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
