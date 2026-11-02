#!/bin/sh
# The pre-registered Pakistan initialisation dates (results/pk/PREREGISTRATION-PK.md), IFS and ENS,
# from the Google mirror, scored steps only (08, 11, 14, 17 PKT), three downloads at a time.
set -u
DATES="2026-05-06 2026-05-13 2026-05-20 2026-05-27 2026-06-03 2026-06-10 2026-06-17 2026-06-24 2026-07-01 2026-07-08 2026-07-15 2026-07-22 2026-07-29 2026-08-05 2026-08-12 2026-08-19 2026-08-26"
DIR="$(dirname "$0")"
for s in oper enfo; do for d in $DATES; do echo "$d $s"; done; done |
  xargs -P 3 -n 2 sh -c '"$0/../.venv/bin/python" "$0/fetch_ecmwf_open.py" "$1" --stream "$2" --members 10 --max-step 120 --region pk --mirror gcs --work-hours-utc 3,6,9,12 || echo "FAILED $2 $1"' "$DIR"
echo ALL DONE
