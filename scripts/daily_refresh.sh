#!/usr/bin/env bash
# Daily refresh: official sheriff lists (Ohio, Pennsylvania, New Jersey) -> official value lookups -> rebuild site.
# Pennsylvania: Philadelphia, Montgomery, Lehigh via CivilView (scraper/official.py civilview_pa); values via Philadelphia OPA (Carto) and Montgomery (PASDA).
set -u
cd "$(dirname "$0")/.."
python3 scraper/official.py ohio new-jersey pennsylvania
# Kentucky: Fayette + Jefferson Master Commissioner lists
python3 scraper/kentucky.py
python3 enrich.py
SITE_URL="${SITE_URL:-https://pg614.github.io/deedhound}" BASE_PATH="${BASE_PATH:-/deedhound}" python3 build.py
