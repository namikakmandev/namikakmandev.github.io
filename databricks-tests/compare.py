"""Compare a Databricks result DataFrame against a reference DataFrame.

Checks available per test (compare.checks in the YAML):

    row_count   same number of rows (optionally within row_count_tolerance)
    schema      same column names (order-insensitive, case-insensitive)
    values      cell-by-cell match, joined on compare.keys; numeric columns
                compared with float_tolerance (relative)

Returns a CheckResult per check so the report can show exactly what differed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

MAX_EXAMPLES = 10


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    examples: list[str] = field(default_factory=list)


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    for col in df.columns:
        # API/CSV numbers often arrive as strings — coerce where possible
        # so 42 == "42" and 3.10 == "3.1".
        coerced = pd.to_numeric(df[col], errors="coerce")
        if coerced.notna().sum() >= df[col].notna().sum() and df[col].notna().any():
            df[col] = coerced
    return df


def run_checks(actual: pd.DataFrame, expected: pd.DataFrame, spec: dict) -> list[CheckResult]:
    checks = spec.get("checks", ["row_count", "schema", "values"])
    actual, expected = _normalise(actual), _normalise(expected)
    results: list[CheckResult] = []

    if "row_count" in checks:
        results.append(_check_row_count(actual, expected, spec))
    if "schema" in checks:
        results.append(_check_schema(actual, expected))
    if "values" in checks:
        results.append(_check_values(actual, expected, spec))
    return results


def _check_row_count(actual, expected, spec) -> CheckResult:
    tol = spec.get("row_count_tolerance", 0)
    diff = abs(len(actual) - len(expected))
    passed = diff <= tol
    return CheckResult(
        "row_count", passed,
        f"databricks={len(actual)} reference={len(expected)}"
        + (f" (tolerance {tol})" if tol else ""))


def _check_schema(actual, expected) -> CheckResult:
    a, e = set(actual.columns), set(expected.columns)
    if a == e:
        return CheckResult("schema", True, f"{len(a)} columns match")
    detail = []
    if a - e:
        detail.append(f"only in databricks: {sorted(a - e)}")
    if e - a:
        detail.append(f"only in reference: {sorted(e - a)}")
    return CheckResult("schema", False, "; ".join(detail))


def _check_values(actual, expected, spec) -> CheckResult:
    keys = [k.lower() for k in spec.get("keys", [])]
    tol = spec.get("float_tolerance", 1e-6)
    common = [c for c in actual.columns if c in set(expected.columns)]
    if not common:
        return CheckResult("values", False, "no common columns to compare")

    if keys:
        missing = [k for k in keys if k not in common]
        if missing:
            return CheckResult("values", False, f"key column(s) missing: {missing}")
        merged = actual[common].merge(expected[common], on=keys, how="outer",
                                      suffixes=("_db", "_ref"), indicator=True)
        examples: list[str] = []
        orphans = merged[merged["_merge"] != "both"]
        for _, row in orphans.head(MAX_EXAMPLES).iterrows():
            side = "databricks" if row["_merge"] == "left_only" else "reference"
            examples.append(f"key {tuple(row[k] for k in keys)} only in {side}")
        mismatch_count = len(orphans)

        both = merged[merged["_merge"] == "both"]
        for col in [c for c in common if c not in keys]:
            a, e = both[f"{col}_db"], both[f"{col}_ref"]
            if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(e):
                bad = ~((a.isna() & e.isna()) | ((a - e).abs() <= tol * e.abs().clip(lower=1)))
            else:
                bad = ~((a.isna() & e.isna()) | (a.astype(str) == e.astype(str)))
            mismatch_count += int(bad.sum())
            for _, row in both[bad].head(MAX_EXAMPLES - len(examples)).iterrows():
                examples.append(
                    f"key {tuple(row[k] for k in keys)} column '{col}': "
                    f"databricks={row[f'{col}_db']!r} reference={row[f'{col}_ref']!r}")
        passed = mismatch_count == 0
        return CheckResult("values", passed,
                           "all values match" if passed else f"{mismatch_count} mismatch(es)",
                           examples)

    # No keys: compare sorted frames positionally (fine for aggregates / small sets).
    a = actual[common].sort_values(common).reset_index(drop=True)
    e = expected[common].sort_values(common).reset_index(drop=True)
    if len(a) != len(e):
        return CheckResult("values", False,
                           f"row counts differ ({len(a)} vs {len(e)}); "
                           "set compare.keys for row-level diffs")
    mismatches = []
    for col in common:
        if pd.api.types.is_numeric_dtype(a[col]) and pd.api.types.is_numeric_dtype(e[col]):
            bad = ~((a[col].isna() & e[col].isna())
                    | ((a[col] - e[col]).abs() <= tol * e[col].abs().clip(lower=1)))
        else:
            bad = ~((a[col].isna() & e[col].isna())
                    | (a[col].astype(str) == e[col].astype(str)))
        for idx in a.index[bad][:MAX_EXAMPLES]:
            mismatches.append(f"row {idx} column '{col}': "
                              f"databricks={a.at[idx, col]!r} reference={e.at[idx, col]!r}")
    passed = not mismatches
    return CheckResult("values", passed,
                       "all values match" if passed else f"{len(mismatches)}+ mismatch(es)",
                       mismatches[:MAX_EXAMPLES])
