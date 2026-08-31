# Migration staging for the private tracker

The pharma price study is meant to live in a **private** repo, not here — this
repo is public and serves GitHub Pages, so anything merged to `main` is on the
open web. Repo creation needs the account owner; everything else is ready.

This folder holds the two files that differ in the private repo, so the move
survives a lost container:

- `PRIVATE-REPO-README.md` → becomes `README.md` there
- `pharma-prices.workflow.yml` → becomes `.github/workflows/pharma-prices.yml`
  there. It differs from this repo's copy in three ways: it pulls `rates.json`
  from the published site instead of rebuilding it (no secrets to duplicate),
  it runs the outlier check before committing, and it rebuilds
  `pharma-report.html`.

Everything else moves across unchanged: `pharma-prices.html`, `scripts/` and
`data/`.

`pharma-report.html` is generated, not authored — `scripts/build_pharma_report.py`
bakes the data into the page so it opens off disk without a web server. A
private repo has no Pages host, so that file is how the report gets read there.
