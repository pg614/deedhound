#!/usr/bin/env python3
"""Submit URLs to IndexNow (Bing, Yandex, Seznam, Naver...). Usage:
  indexnow.py all            -> every URL in site/urls.txt
  indexnow.py changed <rev>  -> pages under site/ changed in commit <rev>
Never fails the caller; prints HTTP status per batch."""
import json, os, sys, subprocess, urllib.request
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = json.load(open(os.path.join(R, "config.json"))).get("indexnow_key")
BASE = os.environ.get("SITE_URL", "https://deedhound.app").rstrip("/"); HOST = BASE.split("//")[1]
def urls():
    if sys.argv[1:2] == ["changed"]:
        out = subprocess.run(["git", "-C", R, "diff", "--name-only", f"{sys.argv[2]}~1", sys.argv[2], "--", "site"], capture_output=True, text=True).stdout.split()
        return [BASE + "/" + p[5:].replace("index.html", "") for p in out if p.endswith("index.html") and os.path.exists(os.path.join(R, p))]
    return [l.strip() for l in open(os.path.join(R, "site", "urls.txt")) if l.strip()]
U = urls(); print(len(U), "urls")
for n in range(0, len(U), 10000):
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"{BASE}/{KEY}.txt", "urlList": U[n:n + 10000]}).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request("https://api.indexnow.org/indexnow", body, {"Content-Type": "application/json; charset=utf-8"}), timeout=60); print("batch", n, "HTTP", r.status)
    except urllib.error.HTTPError as e: print("batch", n, "HTTP", e.code, e.read()[:200])
    except Exception as e: print("batch", n, "error", e)
