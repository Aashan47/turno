#!/bin/sh
# The pre-registered initialisation dates (results/PREREGISTRATION.md), IFS then ENS.
set -u
DATES="2026-06-03 2026-06-10 2026-06-17 2026-06-24 2026-07-01 2026-07-08 2026-07-15 2026-07-22 2026-07-29 2026-07-30 2026-08-05 2026-08-12 2026-08-19 2026-08-26"
PY="$(dirname "$0")/../.venv/bin/python"
for d in $DATES; do "$PY" "$(dirname "$0")/fetch_ecmwf_open.py" "$d" --stream oper --max-step 120 || echo "FAILED oper $d"; done
for d in $DATES; do "$PY" "$(dirname "$0")/fetch_ecmwf_open.py" "$d" --stream enfo --members 10 --max-step 120 || echo "FAILED enfo $d"; done
echo ALL DONE
