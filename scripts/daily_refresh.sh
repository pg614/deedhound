#!/usr/bin/env bash
# Daily refresh: official lists (OH, NJ, PA, KY) -> value lookups -> sanity check -> build -> commit + push to main.
# Settings come from deploy.env (SITE_URL, BASE_PATH, DEPLOY_BRANCH). Nothing is pushed if any step fails.
set -uo pipefail
cd "$(dirname "$0")/.."
set -a; . ./deploy.env; set +a
step() { echo "== $* $(date '+%F %T %Z')"; }
fail() { echo "FAIL: $*"; exit 1; }
[ "$(git rev-parse --abbrev-ref HEAD)" = "$DEPLOY_BRANCH" ] || fail "repo $(pwd) is on $(git rev-parse --abbrev-ref HEAD), not $DEPLOY_BRANCH"
git diff --quiet HEAD -- . ':!data' ':!site' || fail "uncommitted code changes; refusing to run"
git fetch -q origin && git merge -q --ff-only "origin/$DEPLOY_BRANCH" || fail "cannot fast-forward to origin/$DEPLOY_BRANCH"
step scrape; python3 scraper/official.py ohio new-jersey pennsylvania || fail "official.py"
step kentucky; python3 scraper/kentucky.py || fail "kentucky.py"
step sanity; python3 scripts/sanity_check.py || fail "sanity check"
step enrich; python3 enrich.py || fail "enrich.py"
step build; python3 build.py || fail "build.py"
[ -s site/index.html ] || fail "site/index.html missing"
step commit
git add -A data site
if git diff --cached --quiet; then echo "no data changes"; else
  git commit -q -m "Daily refresh $(date +%F): OH, NJ, PA, KY data, enrich, rebuild" || fail "commit"
  git push -q origin "HEAD:$DEPLOY_BRANCH" || { git pull -q --rebase origin "$DEPLOY_BRANCH" && git push -q origin "HEAD:$DEPLOY_BRANCH"; } || fail "push"
fi
echo "PUSHED $(git rev-parse --short HEAD)"
