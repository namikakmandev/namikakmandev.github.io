"""Reference ("expected") data sources to compare Databricks results against.

Each test's `reference:` block picks one of these types:

    type: csv        local file (path) or URL (url) — e.g. an export from the other system
    type: api        REST endpoint returning JSON; `record_path` drills into the payload
    type: databricks a second query (e.g. other catalog/schema, or another warehouse)

Credentials for `api` sources can be injected via headers with ${ENV_VAR}
placeholders, so tokens never live in the YAML.
"""

from __future__ import annotations

import os
import re

import pandas as pd
import requests

from databricks_client import DatabricksClient

_ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env(value: str) -> str:
    return _ENV_RE.sub(lambda m: os.environ.get(m.group(1), ""), value)


def load_reference(spec: dict, databricks: DatabricksClient) -> pd.DataFrame:
    kind = spec.get("type")
    if kind == "csv":
        return _load_csv(spec)
    if kind == "api":
        return _load_api(spec)
    if kind == "databricks":
        return databricks.query(spec["query"], timeout_s=spec.get("timeout_s", 300))
    raise ValueError(f"Unknown reference type: {kind!r} (expected csv, api or databricks)")


def _load_csv(spec: dict) -> pd.DataFrame:
    source = spec.get("path") or spec.get("url")
    if not source:
        raise ValueError("csv reference needs a 'path' or 'url'")
    return pd.read_csv(source, sep=spec.get("separator", ","))


def _load_api(spec: dict) -> pd.DataFrame:
    headers = {k: _expand_env(v) for k, v in (spec.get("headers") or {}).items()}
    resp = requests.get(_expand_env(spec["url"]), headers=headers,
                        params=spec.get("params"), timeout=spec.get("timeout_s", 60))
    resp.raise_for_status()
    data = resp.json()
    for part in filter(None, spec.get("record_path", "").split(".")):
        data = data[part]
    if isinstance(data, dict):
        data = [data]
    return pd.DataFrame(data)
