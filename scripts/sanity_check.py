#!/usr/bin/env python3
"""Compare new county data against the last committed run (git HEAD).
A county that drops >50% while its previous run still had >=2 future-dated sales is treated as a cut-off scrape:
its previous file is restored and a WARN line is printed. Exit 1 (no push) if total listings fall >50% or a file is unreadable."""
import json, glob, subprocess, sys, datetime
today = datetime.date.today().isoformat(); bad = False; tot_o = tot_n = 0
for f in sorted(glob.glob("data/*/*.json")):
    if f.split("/")[1] in ("enrich", "notes"): continue
    try: new = json.load(open(f))
    except Exception as e: print("FAIL unreadable", f, e); bad = True; continue
    r = subprocess.run(["git", "show", "HEAD:" + f], capture_output=True, text=True)
    old = json.loads(r.stdout) if r.returncode == 0 else {"items": []}
    o, n = len(old.get("items", [])), len(new.get("items", []))
    fut = sum(1 for i in old.get("items", []) if (i.get("sale_date") or "9999") >= today)
    if fut >= 2 and n < 0.5 * fut:
        subprocess.run(["git", "checkout", "HEAD", "--", f]); n = o
        print(f"WARN {f}: {fut} upcoming before, {len(new.get('items', []))} now -> kept previous run's data (as_of {old.get('as_of')})")
    elif o and n < 0.5 * o:
        print(f"NOTE {f}: {o} -> {n} (previous sales are past their date, accepted)")
    tot_o += o; tot_n += n
print(f"COUNTS total {tot_o} -> {tot_n}")
if tot_o and tot_n < 0.5 * tot_o: print("FAIL total listings dropped >50%"); bad = True
sys.exit(1 if bad else 0)
