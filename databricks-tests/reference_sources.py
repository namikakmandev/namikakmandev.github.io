"""Reference ("expected") data sources to compare Databricks results against.

Each test's `reference:` block picks one of these types:

    type: csv        local file (path) or URL (url) — e.g. an export from the other system
    type: api        REST endpoint returning JSON; `record_path` drills into the payload
    type: sql        any SQL database via SQLAlchemy (SQL Server, PostgreSQL, MySQL, ...)
    type: powerbi    a DAX query against a Power BI dataset (executeQueries REST API)
    type: databricks a second query (e.g. other catalog/schema, or another warehouse)

Credentials never live in the YAML: `api` headers and `sql` connection strings
support ${ENV_VAR} placeholders, and `powerbi` reads its Azure AD credentials
from environment variables.
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
    if kind == "sql":
        return _load_sql(spec)
    if kind == "powerbi":
        return _load_powerbi(spec)
    if kind == "databricks":
        return databricks.query(spec["query"], timeout_s=spec.get("timeout_s", 300))
    raise ValueError(
        f"Unknown reference type: {kind!r} (expected csv, api, sql, powerbi or databricks)")


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


def _load_sql(spec: dict) -> pd.DataFrame:
    """Query a SQL database. `connection` is a SQLAlchemy URL, e.g.

        mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+18+for+SQL+Server
        postgresql+psycopg2://user:pass@host:5432/db
        mysql+pymysql://user:pass@host/db

    Put the whole URL in an env var / secret and reference it as ${SOURCE_DB_URL}.
    Requires `sqlalchemy` plus the driver package for your database.
    """
    import sqlalchemy  # imported lazily so csv/api-only setups don't need it

    url = _expand_env(spec["connection"])
    if not url:
        raise ValueError("sql reference: 'connection' resolved to empty — is the env var set?")
    engine = sqlalchemy.create_engine(url)
    try:
        with engine.connect() as conn:
            return pd.read_sql_query(sqlalchemy.text(spec["query"]), conn)
    finally:
        engine.dispose()


def _load_powerbi(spec: dict) -> pd.DataFrame:
    """Run a DAX query against a Power BI dataset via the executeQueries API.

    Spec fields:
        dataset_id   the dataset GUID (Power BI service -> dataset -> URL)
        query        a DAX query, e.g.  EVALUATE SUMMARIZECOLUMNS(...)
        workspace_id optional workspace/group GUID (omit for "My workspace")

    Auth (either one):
        POWERBI_TOKEN                                a ready-made bearer token
        POWERBI_TENANT_ID + POWERBI_CLIENT_ID +      service principal; token is
        POWERBI_CLIENT_SECRET                        fetched automatically

    The service principal needs to be allowed in the Power BI admin portal
    ("Service principals can use Fabric APIs") and added to the workspace.
    """
    dataset_id = _expand_env(spec["dataset_id"])
    workspace = _expand_env(spec.get("workspace_id", ""))
    base = "https://api.powerbi.com/v1.0/myorg"
    url = (f"{base}/groups/{workspace}/datasets/{dataset_id}/executeQueries"
           if workspace else f"{base}/datasets/{dataset_id}/executeQueries")

    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {_powerbi_token()}"},
        json={"queries": [{"query": spec["query"]}],
              "serializerSettings": {"includeNulls": True}},
        timeout=spec.get("timeout_s", 120),
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Power BI executeQueries failed ({resp.status_code}): {resp.text[:500]}")
    rows = resp.json()["results"][0]["tables"][0]["rows"]
    df = pd.DataFrame(rows)
    # DAX returns columns like "Sales[amount]" or "[total]" — keep just the name.
    df.columns = [re.sub(r"^[^\[]*\[|\]$", "", str(c)) for c in df.columns]
    return df


def _powerbi_token() -> str:
    token = os.environ.get("POWERBI_TOKEN")
    if token:
        return token
    tenant = os.environ.get("POWERBI_TENANT_ID")
    client_id = os.environ.get("POWERBI_CLIENT_ID")
    secret = os.environ.get("POWERBI_CLIENT_SECRET")
    if not (tenant and client_id and secret):
        raise RuntimeError(
            "Power BI auth missing: set POWERBI_TOKEN, or POWERBI_TENANT_ID + "
            "POWERBI_CLIENT_ID + POWERBI_CLIENT_SECRET for a service principal")
    resp = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data={"grant_type": "client_credentials",
              "client_id": client_id,
              "client_secret": secret,
              "scope": "https://analysis.windows.net/powerbi/api/.default"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]
