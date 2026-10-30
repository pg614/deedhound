#!/usr/bin/env python3
"""Scrapers for sheriff-published official sale lists (robots.txt checked at runtime).
Never touches *.sheriffsaleauction.ohio.gov (robots Disallow: /)."""
import re, html, json, os, sys, time, datetime, subprocess, tempfile, urllib.request, urllib.parse, urllib.robotparser, http.cookiejar, hashlib
from zoneinfo import ZoneInfo
UA = "Mozilla/5.0 (compatible; OhioSheriffSaleTracker/0.1; public-info site)"
BUA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
DELAY = 2.0; OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"); TODAY = datetime.date.today()
NOW = lambda: datetime.datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="minutes")
_robots = {}
def allowed(url):
    p = urllib.parse.urlparse(url); base = f"{p.scheme}://{p.netloc}"
    assert "sheriffsaleauction.ohio.gov" not in p.netloc, "RealAuction is off-limits"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            try: body = urllib.request.urlopen(urllib.request.Request(base + "/robots.txt", headers={"User-Agent": BUA}), timeout=20).read()
            except urllib.error.HTTPError: raise
            except Exception:
                cp = subprocess.run(["curl", "-sL", "--max-time", "30", "-A", BUA, "-w", "%{http_code}", base + "/robots.txt"], capture_output=True)
                code = cp.stdout[-3:].decode(); body = cp.stdout[:-3]
                if code == "404": body = b""
                elif code != "200": raise urllib.error.HTTPError(base, int(code or 0), "", {}, None)
            rp.parse(body.decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as e: rp.parse([] if e.code == 404 else ["User-agent: *", "Disallow: /"])
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)
class S:
    def __init__(s): s.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def get(s, url, data=None, raw=False):
        if not allowed(url): raise PermissionError("robots.txt disallows " + url)
        time.sleep(DELAY)
        r = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None, headers={"User-Agent": BUA})
        try: b = s.op.open(r, timeout=30).read()
        except (urllib.error.URLError, TimeoutError) as e:  # some county TLS stacks reject Python's ssl; fall back to curl (same robots check, same delay)
            if data: raise
            for k in range(4):
                cp = subprocess.run(["curl", "-sfL", "--max-time", "60", "-A", BUA, url], capture_output=True)
                if cp.returncode == 0: break
                time.sleep(5 * (k + 1))
            cp.check_returncode(); b = cp.stdout
        return b if raw else b.decode("utf-8", "replace")
def txt(h):
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    return [x.strip() for x in html.unescape(re.sub(r"<[^>]+>", "\n", h)).split("\n") if x.strip()]
def money(v):
    v = re.sub(r"[^\d.]", "", v or ""); return float(v) if v else None
def mdy(s):
    mm = re.search(r"(\d+)/(\d+)/(\d+)", s or "")
    if not mm: return None
    m, d, y = mm.groups(); y = int(y); y = y + 2000 if y < 100 else y
    return datetime.date(y, int(m), int(d)).isoformat()
def split_addr(a):
    m = re.match(r"(.*?),?\s+([A-Za-z .'-]+?),?\s+(?:OH|Ohio)\s+(\d{5})", a or "", re.I)
    return (m.group(1).strip(" ,"), m.group(2).strip().title(), m.group(3)) if m else (a, "", None)
def rec(county, **k):
    base = dict(county=county, state="ohio", status_history=[], times_postponed=None, upset_amount=None, auction_id=None, status="SCHEDULED", case_number=None, parcel_id=None, address=None, city="", zip=None,
                appraised_value=None, opening_bid=None, deposit=None, plaintiff=None, defendant=None, attorney=None, sale_date=None, sale_type="Foreclosure", source_url=None, as_of=NOW())
    base.update(k); return base

def montgomery():
    s = S(); u = "https://go.mcohio.org/applications/sheriffauction/SFLISTAUCTIONDO.cfm"
    end = (TODAY + datetime.timedelta(days=120)).strftime("%m/%d/%Y")
    t = txt(s.get(u, {"idate1": TODAY.strftime("%m/%d/%Y"), "idate2": end, "iSUMDET": "DET"})); out = []; sect = "Foreclosure"
    for i, x in enumerate(t):
        if x in ("MORTGAGE FORECLOSURE",): sect = "Foreclosure"
        if x == "Address:":
            j = i
            while not re.match(r"\d{2}/\d{2}/\d{4}$", t[j]): j -= 1
            date = t[j]; case = t[j + 1]; f = {}
            k = i
            while k < len(t) - 1 and t[k] != "Sale Amt:":
                if t[k].endswith(":") and not t[k + 1].endswith(":"): f[t[k][:-1]] = t[k + 1]
                k += 1
            a, c, z = split_addr(f.get("Address"))
            out.append(rec("montgomery", case_number=case, address=a, city=c, zip=z or f.get("Zip Code"), parcel_id=f.get("PID"),
                plaintiff=f.get("Plaintiff"), defendant=f.get("Defendant"), attorney=f.get("Attorney"), status=f.get("Status", "ACTIVE"),
                appraised_value=money(f.get("Appr Amt")), opening_bid=money(f.get("Min Bid")), sale_date=mdy(date),
                source_url="https://go.mcohio.org/applications/sheriffauction/sflistauction.cfm"))
    return out

CIVILVIEW = {"ohio": {"allen": 34, "lorain": 18, "medina": 81, "richland": 61},
  "new-jersey": {"atlantic": 25, "bergen": 7, "burlington": 3, "camden": 1, "cape-may": 52, "cumberland": 6, "essex": 2, "gloucester": 19,
                 "hudson": 10, "hunterdon": 32, "middlesex": 73, "monmouth": 8, "morris": 9, "ocean": 85, "passaic": 17, "salem": 20, "union": 15}}
def civilview(county, state="ohio"):
    s = S(); lu = f"https://salesweb.civilview.com/Sales/SalesSearch?countyId={CIVILVIEW[state][county]}"; h = s.get(lu); out = []
    st = "OH" if state == "ohio" else "NJ"; bad = 0
    ids = list(dict.fromkeys(re.findall(r'SaleDetails\?PropertyId=(\d+)', h))); done = set(); relisted = False
    while ids:
      pid = ids.pop(0); done.add(pid)
      if True:
        du = f"https://salesweb.civilview.com/Sales/SaleDetails?PropertyId={pid}"
        if len(out) % 25 == 0: print("  ", county, len(out), NOW(), flush=True)
        t = None
        for attempt in range(3):  # CivilView sometimes returns the index/error page instead of the detail (session lost); re-open the list for a fresh session and retry
            try:
                t = txt(s.get(du))
                if any(x in ("Sheriff #:", "Court Case #:") for x in t) and "Sales Date:" in t: break
                print("  retry", pid, attempt, "detail page invalid", NOW(), flush=True)
            except Exception as e: print("  retry", pid, attempt, repr(e), NOW(), flush=True)
            t = None; time.sleep(5 * (attempt + 1)); s = S(); s.get(lu)
        if t is None:
            print("  skip", pid, "no valid detail page", flush=True); bad += 1
            if bad >= 3 and not relisted:  # the county re-published its list mid-scrape (new PropertyIds, seen in Camden Oct 30, 2026): re-read the list once and pick up the new ids
                relisted = True; s = S(); ids = [x for x in dict.fromkeys(re.findall(r'SaleDetails\?PropertyId=(\d+)', s.get(lu))) if x not in done]; print("  ", county, "list re-read,", len(ids), "ids left", flush=True)
            if bad >= 15 and bad > len(out): raise RuntimeError(f"{county}: {bad} invalid detail pages, list is being re-published; keeping previous data")
            continue
        hi = t.index("Status History") if "Status History" in t else len(t); f = {}
        for i, x in enumerate(t[:hi - 1]):
            if x.endswith(":") and x[:-1] not in f: f[x[:-1]] = t[i + 1] if not t[i + 1].endswith(":") else ""
        hist = []
        for i in range(hi, len(t) - 1):
            if re.match(r"\d{1,2}/\d{1,2}/\d{4}$", t[i + 1]) and t[i] not in ("Date",): hist.append({"status": t[i], "date": mdy(t[i + 1])})
        i = t.index("Address:") if "Address:" in t else -1
        a = t[i + 1] if i >= 0 else ""; m = re.match(r"(.+?),?\s+" + st + r"\s+(\d{5})", t[i + 2] if i >= 0 else "")
        c, z = (m.group(1).title(), m.group(2)) if m else ("", None)
        up = f.get("Approx. Upset*") or f.get("Approx. Upset") or f.get("Approx. Judgment*") or f.get("Approx. Judgment") or f.get("Upset Price")
        postp = sum(1 for x in hist if re.search(r"adjourn|postpon|no bid|reschedul", x["status"], re.I))
        out.append(rec(county, state=state, auction_id=pid, case_number=f.get("Court Case #") or f.get("Sheriff #"), sheriff_number=f.get("Sheriff #"),
            address=a, city=c, zip=z, parcel_id=f.get("Parcel #") or None, plaintiff=f.get("Plaintiff"), defendant=f.get("Defendant"), attorney=f.get("Attorney"),
            appraised_value=money(f.get("Appraised Value")), opening_bid=money(f.get("Starting Bid")), upset_amount=money(up),
            status=(hist[-1]["status"] if hist else "Scheduled").upper(), status_history=hist, times_postponed=postp,
            sale_date=mdy(f.get("Sales Date") or f.get("Sale Date") or f.get("Sale Date/Time") or next((v for k, v in f.items() if "date" in k.lower() and re.search(r"\d+/\d+/\d+", v or "")), None)), sale_type="Tax foreclosure" if "TREASURER" in (f.get("Plaintiff") or "").upper() else "Foreclosure", source_url=du))
    if bad: print("  ", county, "invalid detail pages skipped:", bad, flush=True)
    return out

CIVILVIEW_PA = {"philadelphia": 60, "montgomery": 23, "lehigh": 51}
class _Hang(Exception): pass
def _alarm(*a): raise _Hang("request hung > 90s")
import signal; signal.signal(signal.SIGALRM, _alarm)
CV_CACHE = os.environ.get("CV_CACHE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tmp", "civilview_pa_cache"); os.makedirs(CV_CACHE, exist_ok=True)  # checkpoint: detail pages cached 12h so a re-run resumes where a cut-off run stopped
def civilview_pa(county):
    """Pennsylvania CivilView lists (Philadelphia, Montgomery, Lehigh). Field labels differ by county; status history order differs, so we use the latest-dated entry."""
    lu = f"https://salesweb.civilview.com/Sales/SalesSearch?countyId={CIVILVIEW_PA[county]}"; out = []; seen = set()
    # PropertyIds rotate per session and detail pages need the session cookie; a lost session returns the
    # site's county index page instead. So key rows by their list-row text (stable), validate each detail page,
    # and on a bad page start a new session, re-read the list and look the row up again.
    def listing():
        s = S(); h = s.get(lu); m = {}
        for r in re.findall(r"<tr.*?</tr>", h, re.S):
            pm = re.search(r"SaleDetails\?PropertyId=(\d+)", r)
            if pm: m.setdefault("|".join(txt(r)[1:]), pm.group(1))
        return s, m
    def valid(t): return bool(t) and any(x in ("Sheriff #:", "Court Case #:", "Book & Writ:") for x in t)
    s, rows = listing(); keys = list(rows); print("  ", county, "list rows", len(keys), NOW(), flush=True)
    for n, key in enumerate(keys):
        if n % 50 == 0: print("  ", county, n, len(out), NOW(), flush=True)
        t = None; cf = os.path.join(CV_CACHE, county + "_" + hashlib.sha1(key.encode()).hexdigest() + ".json")
        if os.path.exists(cf) and time.time() - os.path.getmtime(cf) < 12 * 3600: t = json.load(open(cf))
        for attempt in range(4 if t is None else 0):
            try:
                pid = rows.get(key)
                if not pid: break
                signal.alarm(90); t = txt(s.get(f"https://salesweb.civilview.com/Sales/SaleDetails?PropertyId={pid}")); signal.alarm(0)
                if valid(t): json.dump(t, open(cf, "w")); break
                raise ValueError("session lost (index page returned)")
            except Exception as e:
                signal.alarm(0); t = None; print("  retry", key[:30], attempt, repr(e), NOW(), flush=True); time.sleep(20 * (attempt + 1))
                try: signal.alarm(120); s, rows = listing(); signal.alarm(0)
                except Exception: signal.alarm(0)
        if not valid(t): print("  skip", key[:40], flush=True); continue
        pid = rows.get(key, ""); du = lu  # detail PropertyIds expire with the session, so link the official county list
        hi = t.index("Status History") if "Status History" in t else len(t); f = {}
        for i, x in enumerate(t[:hi - 1]):
            m = re.match(r"(.+?)\s*:\s*(.*)$", x)
            if m and x.endswith(":"): k = m.group(1).strip(); f.setdefault(k, t[i + 1] if not t[i + 1].rstrip().endswith(":") else "")
            elif m and m.group(1) in ("All Costs",): f.setdefault(m.group(1), m.group(2))
        hist = []
        for i in range(hi, len(t) - 1):
            if re.match(r"\d{1,2}/\d{1,2}/\d{4}$", t[i + 1]) and t[i] not in ("Date",) and not t[i].startswith("("): hist.append({"status": t[i], "date": mdy(t[i + 1])})
        hist.sort(key=lambda x: x["date"])
        cur = re.search(r"\(Current Status:(.+?) - \d", " ".join(t[hi:hi + 2]))
        status = (cur.group(1) if cur else (hist[-1]["status"] if hist else "Scheduled")).strip().upper()
        ak = next((k for k in ("Property Address", "Address") if k in f), None)
        a = f.get(ak, ""); ai = t.index(ak + ":") if ak else -1
        m = None
        for j in range(ai + 2, min(ai + 5, len(t))) if ai >= 0 else []:
            if t[j].endswith(":"): break
            m = re.match(r"(.+?),?\s+PA\s+(\d{5})", t[j])
            if m: break
        c, z = (m.group(1).title(), m.group(2)) if m else ("", None)
        if not m:  # address and city on one line (e.g. Philadelphia listing variants)
            mm = re.match(r"(.+?)\s+(PHILADELPHIA)\s+PA\s+(\d{5})$", a, re.I)
            if mm: a, c, z = mm.group(1), mm.group(2).title(), mm.group(3)
        sh = f.get("Sheriff #") or f.get("Sheriff"); case = f.get("Court Case #")
        k = sh or (case, a)
        if k in seen: continue
        seen.add(k)
        postp = sum(1 for x in hist if re.search(r"postpon|continu|stay|no bid|reschedul|adjourn", x["status"], re.I))
        typ = f.get("Sale Type") or ""
        plaintiff = f.get("Plaintiff") or ""
        tax = bool(re.search(r"\bTAX\b", typ, re.I)) or bool(re.search(r"SCHOOL DISTRICT|CITY OF PHILADELPHIA|TAX CLAIM|BUREAU", plaintiff, re.I))
        out.append(rec(county, state="pennsylvania", auction_id=pid, case_number=case or sh, sheriff_number=sh, book_writ=f.get("Book & Writ"), ward=f.get("Ward"),
            address=a, city=c, zip=z, parcel_id=f.get("OPA #") or f.get("Parcel #") or None, parcel_kind="OPA #" if f.get("OPA #") else "Parcel #",
            plaintiff=plaintiff or None, defendant=f.get("Defendant"), attorney=f.get("Attorney"), municipality=f.get("Township"), description=f.get("Description") or None,
            opening_bid=money(f.get("Minimum Bid")), upset_amount=money(f.get("Debt Amount")), all_costs=money(f.get("All Costs")), appraised_value=None,
            status=status, status_history=hist, times_postponed=postp, sale_date=mdy(f.get("Sales Date")),
            sale_type=("Tax sale" if tax else "Mortgage foreclosure") + (f" ({typ.title()})" if typ else ""), source_url=du))
    return out

def stark():
    s = S(); B = "https://sheriffsales.starkcountyohio.gov/"; h = s.get(B + "Foreclosures.aspx"); out = []
    dates = sorted({d for d in re.findall(r'SALE_DATE=([\d/]+)', h) if mdy(d) >= TODAY.isoformat()}, key=mdy)
    for d in dates:
        u = B + "ForeclosureSaleDetails.aspx?SALE_DATE=" + d; p = s.get(u)
        btns = re.findall(r'name="([^"]+btnSelect)"', p)
        for b in btns:
            f = {n: html.unescape(v) for n, v in re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', p)}; f[b] = "Details"
            t = txt(s.get(u, f)); i = t.index("Plaintiff vs. Defendant") if "Plaintiff vs. Defendant" in t else None
            if i is None: continue
            j = i
            while t[j] != "Case #:": j -= 1
            g = {t[k][:-1]: t[k + 1] for k in range(j, i) if t[k].endswith(":")}
            a, c, z = split_addr(g.get("Address"))
            out.append(rec("stark", case_number=t[j + 1], appraised_value=money(t[j + 3]), opening_bid=money(t[j + 5]), parcel_id=g.get("Parcels"),
                address=a, city=c, zip=z, plaintiff=t[i + 1], defendant=t[i + 3].rstrip("; "), attorney=t[t.index("Attorney:", i) + 1] if "Attorney:" in t[i:] else None,
                sale_date=mdy(d), source_url=u))
    return out

def wood():
    s = S(); u = "https://woodcountysheriff.com/DocumentCenter/View/153/Active-Listings-PDF"; b = s.get(u, raw=True)
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(b); f.flush(); t = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
    out = []
    for m in re.finditer(r"^\s*(\d{1,2}/\d{1,2}/\d{4})\s+(.+?)\s{2,}(.+?)\s{2,}\$([\d,.]+)\s+\$([\d,.]+)\s+(\S+)", t, re.M):
        d, a, c, ap, ob, case = m.groups(); online = "*" in a
        out.append(rec("wood", case_number=case, address=a.replace("*", "").strip(), city=c.strip().title(), appraised_value=money(ap) or None, opening_bid=money(ob),
            sale_date=mdy(d), sale_type=("Tax foreclosure" if "-LF-" in case else "Foreclosure") + (" (online)" if online else " (in person)"), source_url=u))
    return out

def clermont():
    s = S(); idx = "https://clermontsheriff.org/sheriffs-sales"; h = s.get(idx); out = []
    links = sorted(set(re.findall(r'href="(https://clermontsheriff\.org/media/[^"]*Foreclosure%20Sales[^"]*\.pdf)"', h)))
    for u in links:
        b = s.get(u, raw=True)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(b); f.flush(); t = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
        lines = t.splitlines(); hdr = next((l for l in lines if "Plaintiff" in l and "Defendant" in l), None)
        if not hdr: continue
        cA, cP, cD, cL, cX = 17, hdr.index("Plaintiff") - 1, hdr.index("Defendant") - 3, hdr.index("Lawyer") - 2, hdr.index("Appraisal") - 4
        blocks, cur = [], None
        for l in lines:
            if re.match(r"^\d{4}-CV", l): cur = [l]; blocks.append(cur)
            elif cur is not None:
                if re.match(r"^\s*\d{1,2}-[A-Z][a-z]{2}-\d{2}\s*$", l) or "Page " in l: cur = None
                else: cur.append(l)
        for bl in blocks:
            col = lambda a, z: " ".join(x[a:z].strip() for x in bl if x[a:z].strip())
            first = bl[0]; case = first.split()[0]; tail = first[cX:]
            m = re.findall(r"\$[\d,.]+|Cancelled|Withdrawn|Stayed|Sold", tail)
            dates = [d for x in bl for d in re.findall(r"^\s*(\d{1,2}/\d{1,2}/\d{4})", x)]
            addr = col(cA, cP); ppn = re.search(r"\b(\d{6}[A-Z]\d{3}|\d{9,})\b\s*$", addr)
            if ppn: addr = addr[:ppn.start()].strip()
            am = re.match(r"(.+\b(?:RD|ROAD|ST|STREET|AVE|AVENUE|DR|DRIVE|CT|COURT|LN|LANE|PIKE|CIR|CIRCLE|BLVD|WAY|PL|PLACE|TRL|TRAIL|PKWY|HWY|SR|TER|TERRACE|RUN|ROUTE \d+|LOOP|PATH|ROW|SQ|XING|CV|PT)\.?)\s+([A-Z .]+?),?\s*OH\s*(\d{5})", addr.replace(" /", "")) or re.match(r"(.+?)\s+([A-Z.]+),?\s*OH\s*(\d{5})", addr.replace(" /", ""))
            status = next((x for x in m if not x.startswith("$")), None)
            out.append(rec("clermont", case_number=case, address=(am.group(1) if am else addr).title(), city=(am.group(2).strip().title() if am else None), zip=(am.group(3) if am else None),
                parcel_id=ppn.group(1) if ppn else None, plaintiff=col(cP, cD) or None, defendant=col(cD, cL) or None, attorney=re.sub(r"\s*\d{3}-\d{3}-\d{4}", "", col(cL, cX)).strip() or None,
                appraised_value=money(m[0]) if m and m[0].startswith("$") else None, opening_bid=money(m[1]) if len(m) > 1 and m[1].startswith("$") else None,
                status=status or "SCHEDULED", sale_date=mdy(dates[0]) if dates else None, next_sale_date=mdy(dates[1]) if len(dates) > 1 else None,
                sale_type="Foreclosure (online)", source_url=u))
    return out

def mahoning():
    s = S(); idx = "https://www.mahoningcountyoh.gov/992/Sheriff-Sales"; h = s.get(idx); out = []
    for path, d in sorted(set(re.findall(r'href="(/DocumentCenter/View/\d+/(\d{1,2}-\d{1,2}-\d{4})-Sheriff-sale-list)"', h, re.I))):
        sd = mdy(d.replace("-", "/"))
        if sd < TODAY.isoformat(): continue
        u = "https://www.mahoningcountyoh.gov" + path; b = s.get(u, raw=True)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(b); f.flush(); t = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
        kind = "Tax foreclosure (in person)" if "TAX" in t[:300].upper() else "Foreclosure (in person)"
        for blk in re.split(r"\n(?=\s*\d+\.\s+\d{2}CV\d+)", t):
            blk = blk.split("NEXT AVAILABLE")[0]; m = re.match(r"\s*\d+\.\s+(\d{2}CV\d+)", blk)
            if not m: continue
            L = [l for l in blk.splitlines() if l.strip()]
            c2 = L[0].index(m.group(1)) + len(m.group(1)); c2 = c2 + len(L[0][c2:]) - len(L[0][c2:].lstrip())
            left = " ".join(l[:c2].strip() for l in L[1:] if l[:c2].strip()); right = [l[c2:].strip() for l in L]
            amt = re.search(r"\$([\d,.]+)", L[0]); right = [re.sub(r"\s{2,}(\$[\d,.]+|PLUS COSTS)\s*$", "", r).strip() for r in right]
            ci = next((k for k, r in enumerate(right) if re.fullmatch(r"[A-Z .]+,\s*OH\s*\d{5}", r)), None)
            cz = re.fullmatch(r"([A-Z .]+),\s*OH\s*(\d{5})", right[ci]) if ci is not None else None
            body = " ".join(r for r in (right[:ci] if ci is not None else right) if r); rest = " ".join(right[ci + 1:]) if ci is not None else body
            pl, _, df = left.partition(" VS ")
            parcels = re.findall(r"\d{2}-\d{3}-\d-\d{3}\.\d{2}-\d", rest)
            out.append(rec("mahoning", case_number=m.group(1), address=body.strip(" ,").title(), city=cz.group(1).strip().title() if cz else "",
                zip=cz.group(2) if cz else None, parcel_id=", ".join(parcels) or None, plaintiff=pl.strip() or None, defendant=df.strip() or None,
                upset_amount=money(amt.group(1)) if amt else None, sale_date=sd, sale_type=kind, source_url=u))
    return out

def trumbull(keep_past=False):
    s = S(); base = "https://www.co.trumbull.oh.us"; h = s.get(base + "/Sheriff/Services/Sheriff-Sales"); out = []
    for path in sorted(set(re.findall(r'href="(/Sheriff/[^"]*Foreclosure List\.pdf)"', h, re.I))):
        u = base + path.replace(" ", "%20"); b = s.get(u, raw=True)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(b); f.flush(); t = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
        dm = re.search(r"([A-Z]+ \d{1,2}, \d{4}) at", t)
        sd = datetime.datetime.strptime(dm.group(1).title(), "%B %d, %Y").date().isoformat() if dm else None
        for blk in re.split(r"\n(?=\s*\d+\.\s*\d{2}\s*(?:CV|BOR)\s*\d+)", t):
            blk = re.split(r"\n\s*If you are the successful|NEXT SHERIFF SALE", blk)[0]
            m = re.match(r"\s*\d+\.\s*(\d{2}\s*(?:CV|BOR)\s*\d+)\s{2,}(.+?)\s{2,}\$\s*([\d,.]+)", blk)
            if not m: continue
            L = [l for l in blk.splitlines() if l.strip()][1:]
            c2 = len(L[0]) - len(L[0].split("  ")[-1].lstrip()) if L else 0
            c2 = max(re.search(r"\S", m.string[m.start(2):]) and m.start(2), 0)
            left = " ".join(l[:c2].strip() for l in L); right = [l[c2:].strip() for l in L if l[c2:].strip()]
            cz = re.match(r"([A-Z .]+),\s*OH\s*(\d{5})", right[0]) if right else None
            pl, _, df = left.partition("VS ")
            out.append(rec("trumbull", case_number=re.sub(r"\s+", " ", m.group(1)), address=m.group(2).strip(" ,").title(), city=cz.group(1).strip().title() if cz else "",
                zip=cz.group(2) if cz else None, parcel_id=" ".join(right[1:]) or None, plaintiff=pl.strip() or None, defendant=df.strip() or None,
                opening_bid=money(m.group(3)), deposit=3000.0, sale_date=sd, sale_type="Tax foreclosure (in person)", source_url=u))
    return out

def _pdftext(b):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(b); f.flush(); return subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
def geauga():
    s = S(); pg = "https://sheriff.co.geauga.oh.us/civil/sheriffs-sales/"; h = s.get(pg); out = []
    for u in list(dict.fromkeys(re.findall(r'href="(https://[^"]+/uploads/sites/33/[^"]+LandSale[^"]*\.pdf)"', h, re.I)))[:3]:
        try: t = _pdftext(s.get(u, raw=True))
        except Exception as e: print("  skip", u, e, flush=True); continue
        for m in re.finditer(r"^\s*(\d{2}-\d{6})\s+(.+?)\s{2,}(.+?)\s{2,}OH\s+(\d{5})\s+(\S+)\s+(\d{1,2}/\d{1,2}/\d{4})\s+\$([\d,.]+)\s+\$([\d,.]+)\s+\$([\d,.]+)\s*(.*)$", t, re.M):
            pid, a, c, z, case, d, ap, ob, dep, rest = m.groups()
            note = re.search(r"PROVISIONAL SALE DATE (\d+/\d+/\d+)", rest)
            out.append(rec("geauga", parcel_id=pid, address=a.strip(), city=c.strip().title(), zip=z, case_number=case, sale_date=mdy(d), appraised_value=money(ap), opening_bid=money(ob), deposit=money(dep),
                next_sale_date=mdy(note.group(1)) if note else None, sale_type="Tax foreclosure (in person)" if re.search(r"TR\b|TF\b", case) else "Foreclosure (online)", source_url=u))
    return out
def ashtabula():
    s = S(); base = "https://www.ashtabulacounty.gov"; h = s.get(base + "/731/Sheriff-Sales"); out = []
    for path in dict.fromkeys(re.findall(r'href="(/DocumentCenter/View/\d+/[A-Z]+-SHERIFF-SALE)"', h)[:2]):
        u = base + path; t = _pdftext(s.get(u, raw=True)); L = t.splitlines()
        for i, ln in enumerate(L):
            cols = re.split(r"\s{2,}", ln.strip()); m = None
            if len(cols) == 8 and (mm := re.match(r"(.*?,.*?)\s+(\d+\s.+)$", cols[1])): cols = cols[:1] + [mm.group(1), mm.group(2)] + cols[2:]
            if len(cols) >= 9 and re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2}", cols[0]) and re.fullmatch(r"\d{9,}", cols[4]) and cols[7].startswith("$") and cols[8].startswith("$"):
                m = type("M", (), {"groups": lambda self, c=cols: tuple(c[:9])})()
            if not m: continue
            d, nm, a, c, pid, case, pl, ap, ob = m.groups(); pp = ln.find(pl); np_ = ln.find(nm)
            for ln2 in L[i + 1:i + 4]:
                if not ln2.strip() or re.match(r"\s*\d{1,2}/\d{1,2}/\d{2}\s+\S.*\$", ln2): break
                ext = ln2[pp:pp + 22].strip() if pp > 0 and len(ln2) > pp else ""
                if ext and not ext.startswith("$"): pl = pl + " " + ext.split("  ")[0]
                ext2 = ln2[np_:np_ + 22].strip() if np_ > 0 and len(ln2) > np_ else ""
                if ext2 and not re.match(r"\d", ext2): nm = nm + " " + ext2.split("  ")[0]
            nxt = re.match(r"\s*(\d{1,2}/\d{1,2}/\d{2})\b", L[i + 1]) if i + 1 < len(L) else None
            out.append(rec("ashtabula", parcel_id=pid, address=a.strip(), city=c.strip().title(), case_number=case, plaintiff=pl.strip(), defendant=nm.strip(), sale_date=mdy(d),
                next_sale_date=mdy(nxt.group(1)) if nxt else None, appraised_value=money(ap), opening_bid=money(ob), sale_type="Foreclosure (online)", source_url=u))
    return out

def _city_from(a):
    m = re.match(r"(.+?),\s*([A-Za-z .'-]+)$", a.strip()); return (m.group(1).strip(), m.group(2).strip().title()) if m else (a.strip(), "")
def marion():
    s = S(); pg = "https://www.marioncountyohio.gov/elected_offices/sheriff/sheriff_sales/index.php"; h = s.get(pg); out = []
    for href in dict.fromkeys(re.findall(r'href="(https://www\.marioncountyohio\.gov/[^"]*Sheriff Sale (\d+-\d+-\d{4})[^"]*\.pdf)[^"]*"', h)):
        u, ds = href; d = mdy(ds.replace("-", "/"))
        if d < TODAY.isoformat(): continue
        url = urllib.parse.quote(u.split("?")[0], safe=":/"); t = _pdftext(s.get(url, raw=True))
        kind = "Tax foreclosure (in person)" if "TAX" in t[:300].upper() else "Mobile home (on-site)" if "MOBILE HOME" in t[:300].upper() else "Foreclosure (online)"
        nd = re.search(r"RESCHEDULED TO SELL ON\s+([A-Z]+ \d{1,2}, \d{4})", t.replace("\n", " "))
        nd = datetime.datetime.strptime(nd.group(1).title(), "%B %d, %Y").date().isoformat() if nd else None
        for m in re.finditer(r"^(\S.+?)\s{2,}((?:\d{4} CV \d+|CV[A-Z]? ?\d+|\d{2,4}[- ]?[A-Z]{2,3}[- ]?\d+))\s+(.+?)\s{2,}(\S+?),?\s+\$\s*([\d,.]+)\s*\$\s*([\d,.]+)\s*(?:\$\s*([\d,.]+)|(\d+%))?", t, re.M):
            nm, case, a, pid, ap, ob, dep, pct = m.groups(); nl = t[m.end():].split("\n")[1] if t[m.end():].count("\n") > 1 else ""
            line = t[t.rfind("\n", 0, m.start()) + 1:m.end()]; ai = line.find(a)
            if a.rstrip().endswith(",") and ai > 0 and nl[ai:ai + 40].strip(): a = a + " " + nl[ai:ai + 40].strip().split("  ")[0]
            if nl[:30].strip() and not re.search(r"\d|IF TH|\$", nl): nm = nm + " " + nl[:30].strip()
            a, c = _city_from(a.rstrip(" ,"))
            out.append(rec("marion", defendant=nm.replace("*", "").strip(), case_number=case, address=a, city=c, parcel_id=pid if re.search(r"\d", pid) else None,
                appraised_value=money(ap), opening_bid=money(ob), deposit=money(dep) if dep else None, sale_date=d, next_sale_date=nd, sale_type=kind, source_url=url))
    return out
def wayne():
    s = S(); out = []
    for pg in ("https://waynecountysheriff.com/sheriff-sales/", "https://waynecountysheriff.com/sheriff-sales/probate-tax-sales/"):
        h = s.get(pg)
        for u in dict.fromkeys(re.findall(r'(https://waynecountysheriff\.com/wp-content/uploads/\d{4}/\d{2}/[A-Za-z0-9-]+\.pdf)', h)):
            fn = u.rsplit("/", 1)[1]; mm = re.search(r"([A-Za-z]+)-(\d{1,2})-(\d{4})", fn)
            if not mm: continue
            try: d = datetime.datetime.strptime(f"{mm.group(1)[:3]} {mm.group(2)} {mm.group(3)}", "%b %d %Y").date()
            except ValueError: continue
            if d < TODAY: continue
            t = _pdftext(s.get(u, raw=True))
            for m in re.finditer(r"^\s*(\d{4} CV[A-Z]?-?[A-Z]? ?\d+)\s+(.+?)\s{2,}(\d{2}-\d{5}\.\d{2,3})\s+\$([\d,.]+)\s+\$([\d,.]+)\s+(\S+)", t, re.M):
                case, a, pid, ob, dep, loc = m.groups(); a, c = _city_from(a)
                out.append(rec("wayne", case_number=case, address=a, city=c, parcel_id=pid, opening_bid=money(ob), deposit=money(dep), sale_date=d.isoformat(),
                    sale_type=("Tax foreclosure" if "probate" in pg else "Foreclosure") + (" (in person)" if loc.lower() == "lobby" else " (online)"), source_url=u))
    return out
def logan():
    s = S(); pg = "https://www.logancountyohio.gov/sheriff-sales.html"; h = s.get(pg); out = []
    m0 = re.search(r'href="(/uploads/[^"]*currentsales[^"]*\.pdf)"', h)
    if not m0: return out
    u = "https://www.logancountyohio.gov" + m0.group(1); t = _pdftext(s.get(u, raw=True)); sd = None; blk = []
    PAR = r"\d{2}-\d{3}-\d{2}-\d{2}-\d{3}-\d{3}"
    for ln in t.splitlines():
        mm = re.match(r"\s*Sale Date\s+(\d+/\d+/\d{4})", ln)
        if mm: sd = mdy(mm.group(1)); blk = []; continue
        blk.append(ln)
        cm = re.search(r"Case #\s+(\S+)(?:\s+\$([\d,.]+))?", ln)
        if not cm: continue
        first = next((x for x in blk if re.search(PAR, x)), None); body = blk; blk = []
        if not first or not sd: continue
        pm = re.search(PAR, first); pre = re.split(r"\s{2,}", first[:pm.start()].strip())
        addr = pre[-1].rstrip(" -") if len(pre) >= 3 else ""
        pl = pre[0] if len(pre) >= 3 else ""; df = pre[1] if len(pre) >= 3 else ""
        fi = body.index(first)
        def col(v, nxt_start):
            st = first.find(v)
            if st < 0 or not v: return v
            parts = [v]
            for x in body[fi + 1:-1]:
                seg = x[st:nxt_start].strip() if len(x) > st else ""
                if len(seg) > 2 and not re.search(r"online|in person|Judgement|\$|" + PAR, seg, re.I): parts.append(seg)
            return " ".join(parts)
        if len(pre) >= 3:
            ps, ds_, as_ = first.find(pl), first.find(df), first.find(addr)
            pl, df = col(pl, ds_), col(df, as_)
            ex = [x[as_:pm.start()].strip() for x in body[fi + 1:fi + 2] if len(x) > as_]
            if ex and ex[0] and not re.search(PAR + r"|\$", ex[0]): addr = addr + " " + ex[0]
        ap = re.search(r"\$([\d,.]+)", first[pm.end():]); status = "CANCELED" if "CANCEL" in " ".join(body).upper() else "SCHEDULED"
        tax = "Treasurer" in " ".join(body)
        city = ""
        for x in reversed(body[:-1]):
            x = x.strip()
            if x and not re.search(r"online|in person|Judgement|\$|ACTIVE|" + PAR, x, re.I) and len(re.split(r"\s{2,}", x)) == 1: city = x.title(); break
        out.append(rec("logan", case_number=cm.group(1), address=addr, city=city, parcel_id=pm.group(0), plaintiff=pl, defendant=df,
            appraised_value=None if tax else (money(ap.group(1)) if ap else None), opening_bid=money(cm.group(2)) if tax and cm.group(2) else None,
            status=status, sale_date=sd, sale_type="Tax foreclosure (in person)" if tax else "Foreclosure (online)", source_url=u))
    return out
def scioto():
    import xlrd
    s = S(); pg = "https://www.sciotocountysheriff.org/sales"; h = s.get(pg); out = []
    m0 = re.search(r'href="(https://www\.sciotocountysheriff\.org/_files/ugd/[^"?]+\.xls)\?[^"]*UPCOMING', h)
    if not m0: return out
    u = m0.group(1); b = xlrd.open_workbook(file_contents=s.get(u, raw=True)); sh = b.sheet_by_index(0)
    for r in range(sh.nrows):
        v = [sh.cell_value(r, c) for c in range(sh.ncols)]
        if not re.match(r"\d{2}-CI[A-Z]-\d+", str(v[0])) or not isinstance(v[4], float): continue
        d = xlrd.xldate.xldate_as_datetime(v[4], b.datemode).date().isoformat(); a, c = _city_from(str(v[6]))
        bid = re.search(r"\$\s*([\d,.]+)", str(v[5])); firm = "MINIMUM BID" in str(v[5]).upper()
        out.append(rec("scioto", case_number=v[0], defendant=v[1].strip(), parcel_id=str(v[3]).strip(" ,"), address=a, city=c, sale_date=d,
            opening_bid=money(bid.group(1)) if bid and firm else None, attorney=str(v[7]).replace("ATTORNEY", "").strip() or None,
            notes=None if firm else "Taxes due " + (bid.group(0) if bid else "") + " plus court costs; minimum bid set the Friday before sale",
            sale_type="Tax foreclosure (in person)", source_url=u))
    return out


def _tok(h):
    import html as H
    t = re.sub(r'(?is)<(script|style).*?</\1>', '', h); t = re.sub(r'(?i)<(br|/tr|/p|/li|/div|/h\d|/t[dh])[^>]*>', '\n', t)
    t = H.unescape(re.sub(r'<[^>]+>', '', t)).replace('\xa0', ' ')
    return [re.sub(r'\s+', ' ', x).strip(' |') for x in t.splitlines() if re.sub(r'\s+', ' ', x).strip(' |')]
def _ld(s):
    s = re.sub(r'(\d)(st|nd|rd|th)\b', r'\1', s); s = re.sub(r'\s+', ' ', s.replace(',', ', ')).strip()
    for f in ("%B %d, %Y", "%m/%d/%Y"):
        try: return datetime.datetime.strptime(s.title() if f[1] == 'B' else s, f).date().isoformat()
        except ValueError: pass
def _fd(s):
    m = re.findall(r'(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}(?:st|nd|rd|th)?,? ?\d{4}|\d{1,2}/\d{1,2}/\d{4}', s, re.I)
    return [_ld(x if '/' in x else re.sub(r',? ?(\d{4})$', r', \1', x)) for x in m]
def _zip(a):
    m = re.search(r'^(.*?),?\s+([A-Za-z .]+?),?\s+(?:OH|Ohio),?\s+(\d{5})', a)
    return (m.group(1).strip(' ,'), m.group(2).strip().title(), m.group(3)) if m else (a, "", None)

def harrison():
    s = S(); u = "https://www.harrisoncountyohio.gov/media/Sheriff/property-for-sale-2026.pdf"; out = []
    for ln in _pdftext(s.get(u, raw=True)).splitlines():
        m = re.match(r"\s*\d+\s+(.+?)\s+Vs\.?\s+(.+?)\s{2,}(.+?)\s{2,}(.+?)\s{2,}(\d{5})\s+(?:(\d+/\d+/\d{4})\s+)?\$\s*([\d,.]+)\s+(\d+/\d+/\d{4})\s+(\d+/\d+/\d{4})\s*(.*)$", ln)
        if not m: continue
        pl, df, a, c, z, ad, amt, d1, d2, rest = m.groups()
        if rest.strip(): continue
        d1, d2 = mdy(d1), mdy(d2); d = d1 if d1 >= TODAY.isoformat() else d2
        tax = "Treasurer" in pl
        out.append(rec("harrison", plaintiff=pl.strip(), defendant=df.strip(), address=a, city=c.title(), zip=z, sale_date=d, next_sale_date=d2 if d == d1 else None,
            appraised_value=None if tax else money(amt), opening_bid=money(amt) if tax else None, sale_type="Tax foreclosure" if tax else "Foreclosure", source_url=u))
    return out

def hocking():
    s = S(); u = "https://www.hockingsheriff.org/sheriffsales/"; t = _tok(s.get(u)); out = []
    for i, x in enumerate(t):
        m = re.match(r"(Online Auction|Tax Sale)\s*Case No\. (\S+)", x)
        if not m: continue
        f = {}
        for y in t[i + 2:i + 8]:
            for k in ("Parcel Numbers", "Parcel Number", "Appraised At", "Minimum Bid", "1st Date of Sale", "2nd Date of Sale"):
                if y.startswith(k): f[k] = y[len(k):].strip(); break
        a, c, z = _zip(t[i + 1]); d1 = _ld(f.get("1st Date of Sale", "")); d2 = _ld(f.get("2nd Date of Sale", ""))
        d = d1 if d1 and d1 >= TODAY.isoformat() else d2
        out.append(rec("hocking", case_number=m.group(2), address=a, city=c, zip=z, parcel_id=(f.get("Parcel Numbers") or f.get("Parcel Number", "")).split(";")[0],
            appraised_value=money(f.get("Appraised At")), opening_bid=money(f.get("Minimum Bid")), sale_date=d, next_sale_date=d2 if d == d1 else None,
            sale_type="Tax foreclosure (in person)" if m.group(1) == "Tax Sale" else "Foreclosure (online)", source_url=u))
    return out

def erie():
    s = S(); u = "https://www.eriecounty.oh.gov/SheriffSales.aspx"; t = _tok(s.get(u)); out = []; d = None
    for i, x in enumerate(t):
        m = re.match(r"\w+day (\w+ \d{1,2}, \d{4})", x)
        if m: d = _ld(m.group(1)); continue
        if x.startswith("Status of Past Sales"): break
        if d and re.match(r"\d{4}CV\d+$", x):
            pl, df = t[i - 2], t[i - 1]; a, c, z = _zip(t[i + 1]); pid = re.sub(r"^PPN:", "", t[i + 2]).strip()
            vals = []
            for y in t[i + 3:i + 7]:
                if re.match(r"\$[\d,.]+$", y): vals.append(money(y))
                else: break
            tax = "Treasurer" in pl
            ap, ob, dep = (None, vals[0] if vals else None, vals[1] if len(vals) > 1 else None) if tax else ((vals + [None] * 3)[:3])
            out.append(rec("erie", case_number=x, plaintiff=pl, defendant=df, address=a, city=c, zip=z, parcel_id=pid, appraised_value=ap, opening_bid=ob, deposit=dep,
                sale_date=d, sale_type=("Tax foreclosure" if tax else "Foreclosure") + " (online)", source_url=u))
    return out

def ashland():
    s = S(); u = "https://www.ashlandcountysheriff.org/property-sales"; t = _tok(s.get(u)); out = []
    for i, x in enumerate(t):
        if re.match(r"\d{2}-CFR-\d+$|\d{2}-[A-Z]{2,4}-\d+$", x) and i >= 3 and re.match(r"\d+/\d+/\d{4}$", t[i - 3]):
            d1, d2 = mdy(t[i - 3]), mdy(t[i - 2]); d = d1 if d1 >= TODAY.isoformat() else d2
            a = t[i + 2].rstrip(","); cz = t[i + 3]; m = re.match(r"(.+?), OH (\d{5})", cz)
            if m: c, z, j = m.group(1).title(), m.group(2), i + 4
            else: c, z, j = "", None, i + 3
            canc = t[j + 1] if len(t) > j + 1 else ""
            if canc.upper().startswith("Y"): continue
            out.append(rec("ashland", case_number=x, parcel_id=t[i + 1], address=a, city=c, zip=z, appraised_value=money(t[j]), sale_date=d, next_sale_date=d2 if d == d1 else None,
                sale_type="Foreclosure (" + t[i - 1].strip().lower() + ")", source_url=u))
    return out

def gallia():
    s = S(); u = "https://www.galliasheriff.org/sheriff-sales"; t = _tok(s.get(u)); out = []; d = None; typ = None
    for i, x in enumerate(t):
        if x in ("Tax Sale", "Online Sheriff Sale"): typ = x; continue
        dd = _fd(x)
        if typ and dd and re.match(r"\w+ \d{1,2}, \d{4}\s*@", x): d = dd[0]; continue
        m = re.match(r"Case ?#:? ?(\S+)", x)
        if not (m and d): continue
        f = {}
        for y in t[i + 1:i + 10]:
            if re.match(r"Case ?#", y): break
            k, _, v = y.partition(":") if ":" in y else y.partition("-")
            f[k.strip().upper()] = v.strip(" -")
        a, c, z = _zip(f.get("ADDRESS") or f.get("PROPERTY ADDRESS", ""))
        tax = typ == "Tax Sale"
        out.append(rec("gallia", case_number=m.group(1), parcel_id=f.get("PARCEL NO.") or f.get("PARCEL ID"), address=a, city=c, zip=z,
            appraised_value=money(f.get("APPRAISAL")), opening_bid=money(f.get("STARTING BID") or f.get("OPENING BID")), deposit=money(f.get("DEPOSIT REQUIREMENT")),
            sale_date=d, sale_type="Tax foreclosure (in person)" if tax else "Foreclosure (online)", source_url=u))
    return out

def paulding():
    s = S(); u = "https://www.pauldingohsheriff.com/sheriff-sales/"; t = _tok(s.get(u)); out = []
    for i, x in enumerate(t):
        if x == "Appraisal Amount" and i and t[i + 2] == "First Sale":
            hdr = t[i - 1]
            if re.search(r"SOLD|CANCEL|WITHDRAWN", hdr, re.I): continue
            a, _, c = hdr.partition(","); d1 = _fd(t[i + 3]); d2 = _fd(t[i + 5]) if t[i + 4] == "Second Sale" else []
            d1 = d1[0] if d1 else None; d2 = d2[0] if d2 else None; d = d1 if d1 and d1 >= TODAY.isoformat() else d2
            out.append(rec("paulding", address=a.strip(), city=c.strip().title(), appraised_value=money(t[i + 1]), sale_date=d, next_sale_date=d2 if d == d1 else None,
                sale_type="Foreclosure", source_url=u))
    return out

def clinton():
    s = S(); u = "https://clintonsheriff.com/public-services/property-sales/"; t = _tok(s.get(u)); out = []
    for i, x in enumerate(t):
        if x != "SHERIFF’S SALE" and x != "SHERIFF'S SALE": continue
        hd = t[i + 1]; ds = _fd(hd)
        if not ds: continue
        d = ds[-1] if "POSTPONED" in hd.upper() else ds[0]
        if re.search(r"CANCEL|WITHDRAWN", hd, re.I): continue
        case = t[i + 2]; pl, _, df = t[i + 3].partition(" vs. "); a, c, z = _zip(t[i + 4])
        blk = " ".join(t[i + 5:i + 12]); ap = re.search(r"Appraisal:\s*\$([\d,.]+)", blk); ob = re.search(r"2/3:\s*\$([\d,.]+)|Minimum Bid:\s*\$([\d,.]+)", blk, re.I); dp = re.search(r"Deposit:\s*\$([\d,.]+)", blk)
        pm = re.search(r"Parcel No[s.]*\s*([0-9A-Z]{10,})", blk)
        out.append(rec("clinton", case_number=case, plaintiff=pl.strip(), defendant=df.strip(), address=a, city=c, zip=z, parcel_id=pm.group(1) if pm else None,
            appraised_value=money(ap.group(1)) if ap else None, opening_bid=money(next(g for g in ob.groups() if g)) if ob else None, deposit=money(dp.group(1)) if dp else None,
            sale_date=d, sale_type="Foreclosure (online)", notes=("Postponed: " + hd) if "POSTPONED" in hd.upper() else None, source_url=u))
    return out

def morrow():
    s = S(); u = "https://morrowcountysheriff.com/tax-sales/"; t = _tok(s.get(u)); out = []
    for i, x in enumerate(t):
        if re.match(r"\d+/\d+/\d{4}$", x) and i + 3 < len(t) and re.match(r"\d{4}CV\d+$", t[i + 1]):
            j = i + 3; addr = []
            while j < len(t) and not t[j].startswith("$") and not re.match(r"\d+/\d+/\d{4}$", t[j]): addr.append(t[j]); j += 1
            mb = money(t[j]) if j < len(t) and t[j].startswith("$") else None
            last = addr[-1] if addr else ""; zm = re.match(r"(.+?) (\d{5})$", last)
            out.append(rec("morrow", case_number=t[i + 1], defendant=t[i + 2], address=" ".join(addr[:-1]) if zm else " ".join(addr), city=zm.group(1).title() if zm else "", zip=zm.group(2) if zm else None,
                opening_bid=mb, sale_date=mdy(x), sale_type="Tax foreclosure (in person)", source_url=u))
    return out

def vanwert():
    s = S(); u = "https://www.vanwertcountyohio.gov/government/sheriff/divisions/sheriff_sales.php"; t = _tok(s.get(u)); out = []
    for i, x in enumerate(t):
        m = re.match(r"(\d+/\d+/\d{4}) \d", x)
        if not m: continue
        j = i + 1
        while j < i + 4 and " vs " not in t[j]: j += 1
        if " vs " not in t[j] or any(re.search(r"SOLD|CANCEL|WITHDRAWN", y, re.I) for y in t[i:j]): continue
        pl, _, df = t[j].partition(" vs "); cm = re.match(r"CASE: (\S+)", t[j + 1]); a = t[j + 2]; cz = re.match(r"(.+?), Ohio\s+(\d{5})", t[j + 3])
        ap = re.search(r"\$([\d,.]+)", t[j + 4])
        out.append(rec("van-wert", case_number=cm.group(1) if cm else None, plaintiff=pl.strip(), defendant=df.strip().rstrip("."), address=a, city=cz.group(1) if cz else "", zip=cz.group(2) if cz else None,
            appraised_value=money(ap.group(1)) if ap else None, attorney=t[j + 5] if len(t) > j + 5 else None, sale_date=mdy(m.group(1)), sale_type="Foreclosure (online)", source_url=u))
    return out

def union():
    s = S(); u = "https://www.unioncountyohio.gov/sheriff-sales"; h = s.get(u); out = []
    for link in dict.fromkeys(re.findall(r'href="([^"]+\.pdf)"', h, re.I)):
        name = urllib.parse.unquote(link.rsplit("/", 1)[-1]); ds = _fd(name.replace("-", " ").replace("th ", " "))
        if not ds or ds[0] < TODAY.isoformat() or "SOLD" in name.upper(): continue
        t = _pdftext(s.get(link.replace(" ", "%20"), raw=True)); tax = "TAX SALE" in t.upper()
        for blk in re.split(r"(?=Case #)", t)[1:]:
            cm = re.match(r"Case #\s*(\S+)\s+Address:\s*(.+)", blk); g = lambda k: (re.search(k + r":\s*(.+)", blk) or [None, None])[1]
            a = cm.group(2).strip(); am = re.match(r"(.+?\b(?:St|Rd|Ave|Dr|Ln|Ct|Pike|Blvd|Way|Pl|Cir|Hwy|Road|Street|Avenue|Drive)\.?)\s+([A-Z][A-Za-z ]+?)\s+OH\b", a); sd = _fd(g("Second Sale Date") or "")
            out.append(rec("union", case_number=cm.group(1), address=am.group(1) if am else a, city=am.group(2).title() if am else "", plaintiff=g("Plaintiff"), defendant=g("Defendant"), attorney=g("Attorney"),
                opening_bid=money(g("Opening Bid")), deposit=money(g("Deposit")), appraised_value=money(g("Appraisal|Appraised Value")), sale_date=ds[0], next_sale_date=sd[0] if sd else None,
                sale_type="Tax foreclosure (in person, Marysville)" if tax else "Foreclosure (online)", source_url=link.replace(" ", "%20")))
    return out

def holmes():
    s = S(); u = "https://www.holmescountysheriff.org/sales-bids"; t = txt(s.get(u)); out = []
    for i, x in enumerate(t):
        if x != "Case Number:": continue
        f = {}
        for k in range(i, min(i + 20, len(t)) - 1, 1):
            if t[k].endswith(":"): f[t[k][:-1]] = t[k + 1]
        dates = [datetime.date(int(y), int(m), int(d)).isoformat() for m, d, y in re.findall(r"(\d\d)-(\d\d)-(\d{4})", f.get("Sale Date(s)", ""))]
        fut = [d for d in dates if d >= TODAY.isoformat()]
        if not fut: continue
        a, c, z = _zip(f.get("Address", ""))
        out.append(rec("holmes", case_number=f.get("Case Number"), plaintiff=f.get("Plaintiff"), defendant=f.get("Defendant"), address=a, city=c, zip=z, appraised_value=money(f.get("Appraisal")),
            sale_date=fut[0], next_sale_date=fut[1] if len(fut) > 1 else None, sale_type="Foreclosure (online)", source_url=u))
    return out

JOBS = {("ohio","union"): union, ("ohio","holmes"): holmes, ("ohio","harrison"): harrison, ("ohio","hocking"): hocking, ("ohio","erie"): erie, ("ohio","ashland"): ashland, ("ohio","gallia"): gallia, ("ohio","paulding"): paulding, ("ohio","clinton"): clinton, ("ohio","morrow"): morrow, ("ohio","van-wert"): vanwert, ("ohio", "marion"): marion, ("ohio", "wayne"): wayne, ("ohio", "logan"): logan, ("ohio", "scioto"): scioto, ("ohio", "geauga"): geauga, ("ohio", "ashtabula"): ashtabula, ("ohio", "trumbull"): trumbull, ("ohio", "mahoning"): mahoning, ("ohio", "clermont"): clermont, ("ohio", "montgomery"): montgomery, ("ohio", "stark"): stark, ("ohio", "wood"): wood,
        **{(st, c): (lambda c=c, st=st: civilview(c, st)) for st in CIVILVIEW for c in CIVILVIEW[st]},
        **{("pennsylvania", c): (lambda c=c: civilview_pa(c)) for c in CIVILVIEW_PA}}
NAMES = {}
if __name__ == "__main__":
    args = sys.argv[1:]
    keys = [k for k in JOBS if not args or k[0] in args or k[1] in args or f"{k[0]}/{k[1]}" in args]
    for st, c in keys:
        try:
            items = [dict(i, state=st) for i in JOBS[(st, c)]() if i["sale_date"] and i["sale_date"] >= TODAY.isoformat()]
            src = items[0]["source_url"] if items else None
            os.makedirs(os.path.join(OUT, st), exist_ok=True)
            json.dump({"state": st, "county": c, "as_of": NOW(), "source": src, "count": len(items), "items": items}, open(os.path.join(OUT, st, c + ".json"), "w"), indent=1)
            print(st, c, len(items), flush=True)
        except Exception as e: print(st, c, "ERROR", repr(e), flush=True)
