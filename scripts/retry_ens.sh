#!/bin/sh
PY="$(dirname "$0")/../.venv/bin/python"
for d in 2026-07-15 2026-08-05 2026-08-12 2026-08-19 2026-08-26; do "$PY" "$(dirname "$0")/fetch_ecmwf_open.py" "$d" --stream enfo --members 10 --max-step 120 || echo "FAILED enfo $d"; done
echo RETRY DONE
