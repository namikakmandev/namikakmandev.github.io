# Databricks data-validation tests

Automated tests that run SQL on Databricks through its REST API and compare the
results against a second data source (a CSV export, a REST API, or another
Databricks query). Use it to check that data landing in Databricks matches the
system it came from — row counts, schemas, and cell-level values with numeric
tolerance.

No Databricks SDK or CLI required — plain Python (`requests` + `pandas`), so it
runs anywhere: your laptop, GitHub Actions, or any CI/agent environment your
company allows.

## 1. What you need from Databricks

1. **Workspace URL** — the address you open in the browser, e.g.
   `https://adb-1234567890123456.7.azuredatabricks.net`.
2. **Access token** — in Databricks: your avatar → *Settings* → *Developer* →
   *Access tokens* → *Generate new token*. (If your company uses service
   principals, an OAuth token works the same way.)
3. **SQL warehouse ID** — *SQL Warehouses* → pick a warehouse → *Connection
   details* → the `Id` field.

## 2. Run locally

```bash
cd databricks-tests
pip install -r requirements.txt

export DATABRICKS_HOST="https://adb-....azuredatabricks.net"
export DATABRICKS_TOKEN="dapi..."
export DATABRICKS_WAREHOUSE_ID="abc123..."

python run_tests.py                     # all tests
python run_tests.py --only my_test      # one test
```

Results are printed to the console and written to `results/report.md`.
Exit code is non-zero when any test fails, so CI turns red automatically.

## 3. Define your tests

Tests live in [`config/tests.yml`](config/tests.yml) — the file ships with three
commented examples (CSV, REST API, Databricks-vs-Databricks). Each test has
three parts:

```yaml
- name: my_test
  databricks:                 # the "actual" side — SQL run on Databricks
    query: SELECT ...
  reference:                  # the "expected" side — where to pull comparison data
    type: csv | api | databricks
    ...
  compare:                    # what to check
    keys: [id]                             # join keys for row-level diffs
    checks: [row_count, schema, values]
    float_tolerance: 0.01                  # relative tolerance for numbers
    row_count_tolerance: 0
```

Reference source options:

| type | fields | use when |
|------|--------|----------|
| `csv` | `path` or `url`, optional `separator` | the other system gives you file exports |
| `api` | `url`, `params`, `headers` (supports `${ENV_VAR}`), `record_path` | the other system has a REST API |
| `sql` | `connection` (SQLAlchemy URL, supports `${ENV_VAR}`), `query` | the source of truth is a SQL database |
| `powerbi` | `dataset_id`, `workspace_id`, `query` (DAX) | validating against what a Power BI report shows |
| `databricks` | `query` | reconciling two tables/layers inside Databricks |

Secrets (API tokens, connection strings) are never written in the YAML — use
`${ENV_VAR}` placeholders and export the variable (or add a GitHub secret).

### 3a. SQL database references

Set `SOURCE_DB_URL` to a SQLAlchemy connection URL and install the matching
driver from `requirements.txt`:

- SQL Server / Azure SQL: `mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+18+for+SQL+Server` (driver: `pyodbc`)
- PostgreSQL: `postgresql+psycopg2://user:pass@host:5432/db` (driver: `psycopg2-binary`)
- MySQL: `mysql+pymysql://user:pass@host/db` (driver: `pymysql`)

### 3b. Power BI references

The `powerbi` type sends a DAX query to the dataset through the
[executeQueries REST API](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/execute-queries),
so you validate the *same numbers the report shows*, measures included.

- `dataset_id` / `workspace_id`: open the dataset in the Power BI service and
  copy the GUIDs from the URL (`.../groups/<workspace_id>/datasets/<dataset_id>`).
- Auth, either: set `POWERBI_TOKEN` (a bearer token, fine for trying it out),
  or set `POWERBI_TENANT_ID` + `POWERBI_CLIENT_ID` + `POWERBI_CLIENT_SECRET`
  for an Azure AD service principal (the right choice for scheduled runs —
  ask your Power BI admin to enable *service principals can use Fabric APIs*
  and add the principal to the workspace).
- DAX result columns arrive as `Table[column]` — the framework strips them to
  plain `column` names so they line up with your Databricks columns.

**Often simpler:** if the Power BI report just visualises a SQL database or a
Databricks table, point the test at that underlying source with the `sql` or
`databricks` type instead — same numbers, much easier auth. Use the `powerbi`
type when the logic you want to validate lives in Power BI measures.

## 4. Automate with GitHub Actions

The workflow [`.github/workflows/databricks-tests.yml`](../.github/workflows/databricks-tests.yml)
runs the suite every weekday morning and on demand (*Actions* tab → *Databricks
data-validation tests* → *Run workflow*).

Add these repository secrets under *Settings → Secrets and variables → Actions*:

- `DATABRICKS_HOST`
- `DATABRICKS_TOKEN`
- `DATABRICKS_WAREHOUSE_ID`
- `SOURCE_API_TOKEN` — only if you use an `api` reference that needs auth
- `SOURCE_DB_URL` — only for `sql` references (full SQLAlchemy connection URL)
- `POWERBI_TENANT_ID`, `POWERBI_CLIENT_ID`, `POWERBI_CLIENT_SECRET` — only for
  `powerbi` references

The markdown report is uploaded as a build artifact on every run, pass or fail.

> **Note:** if your company workspace has IP access lists enabled, GitHub's
> runners may be blocked; in that case run the suite from a machine inside the
> allowed network (the script itself is identical).

## 5. How comparison works

- Column names are compared case-insensitively; numeric-looking strings are
  coerced to numbers before comparing (so `"42"` equals `42`).
- With `keys`, rows are joined on the key columns and each shared column is
  diffed cell by cell; missing/extra keys are reported with up to 10 examples.
- Without `keys`, rows are sorted and compared positionally — fine for small
  aggregate results.
- Numeric mismatches within `float_tolerance` (relative) are ignored, so
  floating-point noise doesn't cause failures.
