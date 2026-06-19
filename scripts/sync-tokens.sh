#!/usr/bin/env bash
# Copies the canonical tokens.css into every sibling repo.
# Source of truth: portfolio-website/css/tokens.css
# Run from anywhere; adjust ROOT if your folder layout differs.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/portfolio-website/css/tokens.css"
TARGETS=(
  "$ROOT/commercial-finance-tools/tokens.css"
  "$ROOT/dealer-diagnostic-demo/tokens.css"
  "$ROOT/ledger-deck/tokens.css"
)
for t in "${TARGETS[@]}"; do
  cp "$SRC" "$t" && echo "synced -> $t"
done
echo "Done. Remember to commit each repo."
