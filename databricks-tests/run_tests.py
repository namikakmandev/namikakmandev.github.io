#!/usr/bin/env python3
"""Run Databricks data-validation tests defined in config/tests.yml.

Usage:
    python run_tests.py                       # run every test
    python run_tests.py --only daily_sales    # run one test by name
    python run_tests.py --config my.yml --report results/report.md

Exit code 0 = all tests passed, 1 = at least one failure (so CI goes red).
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

import yaml

from compare import CheckResult, run_checks
from databricks_client import DatabricksClient
from reference_sources import load_reference

HERE = Path(__file__).parent


def run_test(test: dict, defaults: dict, client: DatabricksClient) -> tuple[bool, list[CheckResult], float]:
    started = time.monotonic()
    compare_spec = {**defaults, **(test.get("compare") or {})}
    actual = client.query(test["databricks"]["query"],
                          timeout_s=test["databricks"].get("timeout_s", 300))
    expected = load_reference(test["reference"], client)
    results = run_checks(actual, expected, compare_spec)
    return all(r.passed for r in results), results, time.monotonic() - started


def write_report(path: Path, outcomes: list[dict]) -> None:
    lines = ["# Databricks data-validation report", ""]
    n_pass = sum(1 for o in outcomes if o["passed"])
    lines.append(f"**{n_pass}/{len(outcomes)} tests passed**")
    for o in outcomes:
        icon = "✅" if o["passed"] else "❌"
        lines += ["", f"## {icon} {o['name']}  `{o['seconds']:.1f}s`"]
        if o.get("description"):
            lines.append(f"_{o['description']}_")
        if o.get("error"):
            lines += ["", "```", o["error"], "```"]
        for check in o.get("checks", []):
            mark = "✅" if check.passed else "❌"
            lines.append(f"- {mark} **{check.name}** — {check.detail}")
            lines += [f"  - {ex}" for ex in check.examples]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=HERE / "config" / "tests.yml", type=Path)
    parser.add_argument("--only", help="run only the test with this name")
    parser.add_argument("--report", default=HERE / "results" / "report.md", type=Path)
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    defaults = config.get("defaults") or {}
    tests = config.get("tests") or []
    if args.only:
        tests = [t for t in tests if t["name"] == args.only]
        if not tests:
            print(f"No test named {args.only!r} in {args.config}", file=sys.stderr)
            return 1

    client = DatabricksClient()
    outcomes = []
    for test in tests:
        name = test["name"]
        print(f"→ {name} ...", flush=True)
        try:
            passed, checks, seconds = run_test(test, defaults, client)
            outcomes.append({"name": name, "description": test.get("description"),
                             "passed": passed, "checks": checks, "seconds": seconds})
        except Exception:
            outcomes.append({"name": name, "description": test.get("description"),
                             "passed": False, "checks": [], "seconds": 0.0,
                             "error": traceback.format_exc(limit=5)})
        status = "PASS" if outcomes[-1]["passed"] else "FAIL"
        print(f"  {status}")
        for check in outcomes[-1].get("checks", []):
            print(f"    [{'ok' if check.passed else 'XX'}] {check.name}: {check.detail}")
            for ex in check.examples:
                print(f"         {ex}")

    write_report(args.report, outcomes)
    n_pass = sum(1 for o in outcomes if o["passed"])
    print(f"\n{n_pass}/{len(outcomes)} tests passed — report: {args.report}")
    return 0 if n_pass == len(outcomes) else 1


if __name__ == "__main__":
    sys.exit(main())
