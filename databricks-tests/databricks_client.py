"""Minimal Databricks SQL client built on the SQL Statement Execution REST API.

No Databricks SDK needed — just `requests`. Authenticates with a personal
access token (or a service principal OAuth token) passed via environment
variables:

    DATABRICKS_HOST          e.g. https://adb-1234567890123456.7.azuredatabricks.net
    DATABRICKS_TOKEN         personal access token / OAuth token
    DATABRICKS_WAREHOUSE_ID  SQL warehouse id (Admin console -> SQL Warehouses -> Connection details)

API reference: https://docs.databricks.com/api/workspace/statementexecution
"""

from __future__ import annotations

import os
import time

import pandas as pd
import requests

POLL_INTERVAL_S = 2.0
DEFAULT_TIMEOUT_S = 300


class DatabricksError(RuntimeError):
    pass


class DatabricksClient:
    def __init__(self, host: str | None = None, token: str | None = None,
                 warehouse_id: str | None = None):
        self.host = (host or os.environ.get("DATABRICKS_HOST", "")).rstrip("/")
        self.token = token or os.environ.get("DATABRICKS_TOKEN", "")
        self.warehouse_id = warehouse_id or os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
        missing = [name for name, val in [
            ("DATABRICKS_HOST", self.host),
            ("DATABRICKS_TOKEN", self.token),
            ("DATABRICKS_WAREHOUSE_ID", self.warehouse_id),
        ] if not val]
        if missing:
            raise DatabricksError(f"Missing configuration: {', '.join(missing)}")
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.token}"

    def query(self, sql: str, timeout_s: int = DEFAULT_TIMEOUT_S) -> pd.DataFrame:
        """Run a SQL statement and return the full result as a DataFrame."""
        resp = self.session.post(
            f"{self.host}/api/2.0/sql/statements/",
            json={
                "statement": sql,
                "warehouse_id": self.warehouse_id,
                "wait_timeout": "30s",
                "on_wait_timeout": "CONTINUE",
                "format": "JSON_ARRAY",
                "disposition": "INLINE",
            },
            timeout=60,
        )
        resp.raise_for_status()
        payload = resp.json()
        statement_id = payload["statement_id"]

        deadline = time.monotonic() + timeout_s
        while payload["status"]["state"] in ("PENDING", "RUNNING"):
            if time.monotonic() > deadline:
                self._cancel(statement_id)
                raise DatabricksError(f"Statement timed out after {timeout_s}s: {sql[:120]}")
            time.sleep(POLL_INTERVAL_S)
            payload = self._get(f"/api/2.0/sql/statements/{statement_id}")

        state = payload["status"]["state"]
        if state != "SUCCEEDED":
            err = payload["status"].get("error", {})
            raise DatabricksError(
                f"Statement {state}: {err.get('message', 'no error message')}\nSQL: {sql[:300]}")

        columns = [c["name"] for c in payload["manifest"]["schema"]["columns"]]
        rows = list(payload.get("result", {}).get("data_array") or [])

        # Large results come back in chunks; follow the chain.
        chunk = payload.get("result", {})
        while chunk.get("next_chunk_internal_link"):
            chunk = self._get(chunk["next_chunk_internal_link"])
            rows.extend(chunk.get("data_array") or [])

        return pd.DataFrame(rows, columns=columns)

    def _get(self, path: str) -> dict:
        resp = self.session.get(f"{self.host}{path}", timeout=60)
        resp.raise_for_status()
        return resp.json()

    def _cancel(self, statement_id: str) -> None:
        try:
            self.session.post(
                f"{self.host}/api/2.0/sql/statements/{statement_id}/cancel", timeout=30)
        except requests.RequestException:
            pass
