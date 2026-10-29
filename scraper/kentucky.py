#!/usr/bin/env python3
"""Kentucky master commissioner sales (official sources, robots-OK as of Oct 26 2026).
Fayette: https://faycom.info/upcoming/ (robots.txt only blocks /wp-admin/) -> judgment ("to raise") + APPRAISAL AMOUNT.
Jefferson: https://www.jeffcomm.org/docs/webPush.csv (no robots.txt) + official handbill .doc (amount to be raised)
and appraisal PDF link (handwritten scan: linked, not machine-read)."""
import csv, io, json, os, re, html, subprocess, tempfile, time, datetime, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(ROOT, "data", "kentucky")
UA = {"User-Agent": "DeedHoundBot/1.0 (+https://deedhound.app/)"}
def get(u, method="GET"):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=UA, method=method), timeout=30); return r.read() if method == "GET" else r.status
def now(): return datetime.datetime.now().astimezone().isoformat(timespec="minutes")
def money(s): return float(s.replace(",", "")) if s else None
def item(**k):
    base = dict(state="kentucky", status_history=[], times_postponed=0, upset_amount=None, auction_id=None, status="Scheduled", case_number=None, parcel_id=None,
                address=None, city="", zip=None, appraised_value=None, opening_bid=None, deposit=None, plaintiff=None, defendant=None, attorney=None,
                sale_date=None, sale_type="Master Commissioner's Sale", source_url=None, as_of=now(), sheriff_number=None)
    base.update(k); return base
def fayette():
    src = "https://faycom.info/upcoming/"; h = get(src).decode("utf-8", "ignore"); items = []
    for p in re.split(r'data-elementor-type="loop-item"', h)[1:]:
        t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "|", p))); t = re.sub(r"(\| ?)+", "|", t)
        m = re.search(r"\|([A-Z][a-z]+ \d{1,2}, \d{4})\|• ([^|]+)\|", t)
        if not m: continue
        date = datetime.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat(); addr = m.group(2).replace("**SALE CANCELLED**", "").strip()
        cs = re.search(r"\|([^|]+?) vs\. ([^|]+?) – Action No\. ([0-9A-Z-]+), to raise the principal amount of \$([\d,\.]+)", t)
        ap = re.search(r"APPRAISAL AMOUNT: \$? ?\$([\d,\.]+)", t); at = re.search(r"PLAINTIFF.S ATTORNEY: ([^|]+)", t)
        items.append(item(county="fayette", sale_date=date, address=addr.title(), city="Lexington", case_number=cs and cs.group(3),
            plaintiff=cs and cs.group(1).strip(), defendant=cs and cs.group(2).strip(), upset_amount=cs and money(cs.group(4).rstrip(".")),
            appraised_value=ap and money(ap.group(1).rstrip(".")), attorney=at and at.group(1).strip(), status="CANCELLED" if "SALE CANCELLED" in t else "Scheduled",
            source_url=src, auction_id=f"ky-fayette-{cs.group(3) if cs else addr}"))
    return {"state": "kentucky", "county": "fayette", "as_of": now(), "source": src, "count": len(items), "items": items}
def handbill(case):
    try: b = get(f"https://www.jeffcomm.org/docs/handbill/{case}.doc")
    except Exception: return {}
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "h.doc"), "wb").write(b)
        subprocess.run(["soffice", "--headless", "--convert-to", "txt:Text", "h.doc", "--outdir", d], cwd=d, capture_output=True, timeout=120)
        try: t = open(os.path.join(d, "h.txt"), errors="ignore").read()
        except Exception: return {}
    j = re.search(r"amount to be raised by the judgment is \$([\d,]+\.\d\d)", t); dep = re.search(r"Deposit: \$([\d,]+\.\d\d)", t)
    return {"judgment": j and money(j.group(1)), "url": f"https://www.jeffcomm.org/docs/handbill/{case}.doc"}
def jefferson():
    src = "https://www.jeffcomm.org/upcoming-sales.php"; rows = list(csv.DictReader(io.StringIO(get("https://www.jeffcomm.org/docs/webPush.csv").decode("utf-8", "ignore")))); items = []
    for r in rows:
        case = r["CASE"].strip().upper(); m, d, y = r["Expr1"].split("/"); date = datetime.date(int(y), int(m), int(d)).isoformat()
        addr = r["exp4"].strip(); z = re.search(r"\b(4\d{4})\s*$", addr); street = re.sub(r"\s*\b4\d{4}\s*$", "", addr)
        style = r["expr5"]; pl, _, df = style.partition(" vs. ")
        hb = handbill(case); time.sleep(1)
        ap = None
        for ext in ("pdf", "PDF"):
            u = f"https://www.jeffcomm.org/docs/{m}{d}-{r['NewDocket']}.{ext}"
            try:
                if get(u, "HEAD") == 200: ap = u; break
            except Exception: pass
        items.append(item(county="jefferson", sale_date=date, address=street, city="Louisville Metro", zip=z and z.group(1), case_number=case,
            plaintiff=pl.strip()[:200], defendant=df.strip()[:200], attorney=r["ATTORNEY"].strip(), upset_amount=hb.get("judgment"),
            status="WITHDRAWN" if r.get("Expr3", "").strip() else "Scheduled", source_url=src, sheriff_number=f'Sale #{r["NewDocket"]}, Div. {r["DIV"]}',
            auction_id=f"ky-jefferson-{case}-{date}", handbill_url=hb.get("url"), appraisal_url=ap))
    return {"state": "kentucky", "county": "jefferson", "as_of": now(), "source": src, "count": len(items), "items": items}
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for fn in (fayette, jefferson):
        try: d = fn(); json.dump(d, open(os.path.join(OUT, d["county"] + ".json"), "w"), indent=1); print(d["county"], d["count"])
        except Exception as e: print("FAILED", fn.__name__, e)
