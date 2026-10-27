#!/usr/bin/env bash
# Kentucky master commissioner lists (Fayette faycom.info, Jefferson jeffcomm.org). Run daily before build.py.
set -u; cd "$(dirname "$0")/.."; python3 scraper/kentucky.py
