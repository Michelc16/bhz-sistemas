#!/usr/bin/env bash
set -euo pipefail

# Simple asset sanity check for Odoo.sh pipelines.
# Requires python package `sass` (pip install sass==1.66.1).

ASSETS=(
  "bhz_guiabh_website/static/src/scss/guiabh.scss"
)

if ! python3 - <<'PY' >/dev/null 2>&1; then
import sass
PY
then
  echo "[ERROR] Python package 'sass' not available. Install it first: pip install sass==1.66.1" >&2
  exit 1
fi

for file in "${ASSETS[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "[WARN] Asset not found: $file"
    continue
  fi
  echo "[INFO] Compiling $file"
  python3 - <<PY
import sass, sys
try:
    sass.compile(filename="${file}")
    print("[OK] ${file}")
except sass.CompileError as exc:
    print(f"[ERROR] SCSS compile failed for ${file}: {exc}", file=sys.stderr)
    sys.exit(1)
PY
done

echo "[INFO] SCSS checks completed."
