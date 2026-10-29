#!/usr/bin/env bash
# Start the daily refresh in the background (survives the caller's session) and return immediately.
# Log: logs/refresh_YYYY-MM-DD.log, ending with "EXIT <code>". A lock prevents overlapping runs.
REPO="$(cd "$(dirname "$0")/.." && pwd)"; cd "$REPO" && mkdir -p logs tmp
LOG="logs/refresh_$(date +%F).log"; LOCK="tmp/refresh.lock"
if ! flock -n "$LOCK" true; then echo "ALREADY RUNNING (lock $REPO/$LOCK held); not starting"; exit 0; fi
nohup setsid flock -n "$LOCK" bash -c 'echo "START $(date "+%F %T %Z") repo=$PWD branch=$(git rev-parse --abbrev-ref HEAD)"; bash scripts/daily_refresh.sh; echo "EXIT $? $(date "+%F %T %Z")"' >>"$LOG" 2>&1 </dev/null &
echo "STARTED pid $! log $REPO/$LOG"
