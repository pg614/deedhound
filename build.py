#!/usr/bin/env python3
import json, urllib.parse, glob, os, re, html, datetime, shutil
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, "site")
BRAND = json.load(open(os.path.join(ROOT, "brand.json")))
BASE_PATH = os.environ.get("BASE_PATH", "").rstrip("/")
import re as _re
def _bp(doc): return _re.sub(r'(href|src)="/(?!/)', lambda m: f'{m.group(1)}="{BASE_PATH}/', doc) if BASE_PATH else doc
BASE = os.environ.get("SITE_URL", BRAND["site_url"]).rstrip("/")
ENR_P = os.path.join(ROOT, "data", "enrich", "enrich.json"); ENR = json.load(open(ENR_P)) if os.path.exists(ENR_P) else {}
CFG = json.load(open(os.path.join(ROOT, "config.json"))) if os.path.exists(os.path.join(ROOT, "config.json")) else {}
SV = CFG.get("streetview", {})  # Google Street View Static slot: off until enabled + api_key set
STATES = {"ohio": ("Ohio", "OH"), "new-jersey": ("New Jersey", "NJ")}
def E(s): return html.escape(str(s)) if s is not None else ""
def slug(s): return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
def usd(v): return "—" if v is None else f"${v:,.0f}"
def fdate(d): return datetime.date.fromisoformat(d).strftime("%a, %b %-d, %Y")
def asof(a): return datetime.datetime.fromisoformat(a).strftime("%b %-d, %Y %-I:%M %p ET")
CSS = ("""*{box-sizing:border-box}body{margin:0;font:19px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#1d2433;background:#f6f7f9}
a{color:NAVY}header{background:#fff;color:NAVY;border-bottom:5px solid GOLD}header .w{display:flex;align-items:center;justify-content:space-between}header a{color:NAVY;text-decoration:none;font-weight:600}
.w{max-width:1080px;margin:0 auto;padding:16px}.logo{font-weight:800;font-size:24px;display:flex;align-items:center;gap:10px}.logo small{font-weight:500;font-size:16px;color:NAVY;margin-left:4px;max-width:150px;line-height:1.2}.logoslot{display:inline-block;width:40px;height:40px;border-radius:50%;background:#f5b82e}nav a{margin-left:18px;font-size:18px}
h1{font-size:34px;margin:8px 0}.muted{color:#3f4756;font-size:17px}.card{background:#fff;border:1px solid #e3e6eb;border-radius:10px;padding:16px;margin:12px 0}
table{width:100%;border-collapse:collapse;background:#fff}th,td{padding:12px 12px;border-bottom:1px solid #dde1e7;text-align:left;font-size:18px}th{background:NAVY;color:#fff;position:sticky;top:0}
td.n{text-align:right;font-variant-numeric:tabular-nums}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}
.grid a{display:block;background:#fff;border:1px solid #e3e6eb;border-radius:8px;padding:12px;text-decoration:none}.grid b{font-size:26px;display:block;color:NAVY}
.warn{background:#fff8e6;border:1px solid #f1d48a;border-radius:8px;padding:14px 16px;font-size:17px}.kv{display:grid;grid-template-columns:240px 1fr;gap:6px 12px}
form.nl{display:flex;gap:8px;flex-wrap:wrap}form.nl input{flex:1;min-width:220px;padding:14px;font-size:18px;border:1px solid #c9ced8;border-radius:6px}form.nl button{padding:14px 22px;font-size:18px;background:GOLD;color:#fff;border:0;border-radius:6px;font-weight:700}
footer{font-size:16px;color:#5b6475}.scroll{overflow-x:auto}h1,h2,h3{color:NAVY}.grid a{border-left:5px solid GOLD}
.pd{display:grid;grid-template-columns:minmax(260px,380px) 1fr;gap:18px;align-items:start}@media(max-width:760px){.pd{grid-template-columns:1fr}.kv{grid-template-columns:1fr 1fr}}
.ph{margin:0;width:100%;aspect-ratio:4/3;background:#eef1f5;border:2px dashed #c6ccd6;border-radius:10px;display:flex;align-items:center;justify-content:center;text-align:center;color:#5b6475;font-weight:600;overflow:hidden;flex-direction:column}
figure.ph{border-style:solid}.ph img{width:100%;height:100%;object-fit:cover}.ph figcaption{font-size:14px;font-weight:400;padding:4px}""").replace("NAVY", BRAND["navy"]).replace("GOLD", BRAND["gold"])
DISC = ('<p class="warn"><b>Verify before you bid.</b> This is an unofficial summary of public sheriff-sale listings. Sales are often cancelled or '
        'postponed. Always confirm details with the official legal notice and the county sheriff\'s official sale site linked on each page. Not legal or financial advice.</p>')
NL = ('<div class="card"><h2 style="margin-top:0">Get the weekly sheriff sale email</h2><p class="muted">One plain, easy-to-read email each week with new sales and a few picks near you. Free. (Signup coming soon — not yet connected.)</p>'
      '<form class="nl" onsubmit="alert(\'Newsletter signup is not live yet.\');return false"><input type="email" placeholder="you@example.com" aria-label="Email"><button>Subscribe</button></form></div>')
def page(path, title, desc, body, ld=None, crumbs=None):
    canon = BASE + "/" + path.replace("index.html", "")
    lds = (ld if isinstance(ld, list) else [ld]) if ld else []
    if crumbs: lds.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + u} for i, (n, u) in enumerate(crumbs)]})
    nav = " › ".join(f'<a href="{u}">{E(n)}</a>' for n, u in crumbs) if crumbs else ""
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canon}"><link rel="stylesheet" href="/style.css"><link rel="icon" href="{BRAND.get("favicon","")}"><link rel="apple-touch-icon" href="{BRAND.get("apple_icon","")}"><meta name="theme-color" content="{BRAND["navy"]}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
{''.join(f'<script type="application/ld+json">{json.dumps(x)}</script>' for x in lds)}</head><body>
<header><div class="w"><a class="logo" href="/">{('<img src="'+BRAND["logo"]+'" alt="'+E(BRAND["name"])+'" height="68">') if BRAND["logo"] else E(BRAND["name"])}<small>{E(BRAND["tagline"])}</small></a><nav>{" ".join(f'<a href="/{k}/">{v[0]}</a>' for k,v in STATES.items())}</nav></div></header>
<main class="w"><div class="muted">{nav}</div>{body}</main>
<footer class="w">Data compiled from lists published by county sheriffs' offices. Bidding happens on each county's official sale site. {DISC}</footer></body></html>"""
    fp = os.path.join(OUT, path); os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, "w").write(_bp(doc))
def table(items, show_county=False):
    r = "".join(f'<tr><td>{fdate(i["sale_date"])}</td><td><a href="{i["url"]}">{E(i["address"] or "")}</a></td><td>{E(i["city"])}</td>'
                + (f'<td>{E(i["county_name"])}</td>' if show_county else "") +
                f'<td class="n">{usd(i["appraised_value"]) if i["appraised_value"] else usd(i.get("upset_amount"))}</td><td class="n">{usd(i["opening_bid"])}</td><td>{E((i.get("plaintiff") or "—")[:28])}</td></tr>' for i in items)
    return ('<div class="scroll"><table><thead><tr><th>Sale date</th><th>Address</th><th>City</th>' + ("<th>County</th>" if show_county else "") +
            f'<th>Appraised / upset*</th><th>Min. bid</th><th>Lender</th></tr></thead><tbody>{r}</tbody></table></div>')
REGION = {"ohio": {"montgomery":"Southwest","wood":"Northwest","allen":"Northwest","stark":"Northeast","lorain":"Northeast","medina":"Northeast","richland":"North Central",
   "portage":"Northeast","trumbull":"Northeast","mahoning":"Northeast","summit":"Northeast","clermont":"Southwest","clark":"Southwest"},
  "new-jersey": {"bergen":"North","essex":"North","hudson":"North","passaic":"North","morris":"North","union":"North","hunterdon":"Central","middlesex":"Central","monmouth":"Central","ocean":"Central",
   "burlington":"South","camden":"South","gloucester":"South","salem":"South","cumberland":"South","atlantic":"South","cape-may":"South"}}
DEAD = re.compile(r"CANCEL|SOLD|WITHDRAW|BANKRUPT|SATISF|VACAT|STAY|CLOSED|REDEEM|RELEASED", re.I)
def picks(st, items):
    out = []
    for r in sorted(set(REGION[st].values())):
        c = [i for i in items if REGION[st].get(i["county"]) == r and i["appraised_value"] and i["opening_bid"] and i["appraised_value"] >= 40000]
        c.sort(key=lambda i: i["opening_bid"] / i["appraised_value"])
        if c: out.append(f'<h3>{r} {STATES[st][0]}</h3>' + table(c[:3], True))
    return ('<h2>Lowest starting bids vs. appraisal, by region</h2><p class="muted">Facts only, not advice: homes appraised at $40,000+ whose published starting bid is the smallest share of the appraisal.</p>' + "".join(out)) if out else ""
def hist_html(i):
    h = i.get("status_history") or []
    if not h: return '<span class="muted">Not published by this source</span>'
    return f'{i.get("times_postponed") or 0} postponement/no-bid event(s)<br>' + "<br>".join(f'{E(x["status"])} — {datetime.date.fromisoformat(x["date"]).strftime("%b %-d, %Y")}' for x in h)
PH = '<div class="ph" role="img" aria-label="No photo available"><span>No photo available<br><small>from an official source yet</small></span></div>'
def enrich_html(i, full):
    e = ENR.get(i.get("auction_id") or f'{i.get("county")}|{i["case_number"]}|{i["address"]}'); photo = ""
    if e and e.get("photo"):
        photo = (f'<div><figure class="ph"><img src="{E(e["photo"])}" alt="Photo of {E(full)}" loading="lazy" referrerpolicy="no-referrer" '
                 f'onerror="this.parentNode.style.display=\'none\';this.parentNode.nextElementSibling.style.display=\'flex\'"><figcaption>{E(e.get("photo_note") or "")}</figcaption></figure>'
                 + PH.replace('class="ph"', 'class="ph" style="display:none"') + '</div>')
    elif SV.get("enabled") and SV.get("api_key"):
        q = urllib.parse.urlencode({"size": "640x400", "location": full, "key": SV["api_key"]})
        photo = f'<figure class="ph"><img src="https://maps.googleapis.com/maps/api/streetview?{q}" alt="Street View of {E(full)}" loading="lazy"><figcaption>Image: Google Street View</figcaption></figure>'
    else: photo = PH
    if not e:
        return f'<h2>Property details</h2><div class="card pd">{photo}<div><p class="muted">We have not matched this property to official county tax records yet. Check the county auditor/assessor website using the parcel ID above.</p></div></div>'
    rows = "".join(f'<div><b>{E(f[0])}</b></div><div>{usd(f[1]) if len(f) > 2 else E(f[1])}</div>' for f in e["facts"])
    asof_txt = datetime.datetime.fromisoformat(e["retrieved"]).strftime("%b %-d, %Y")
    return (f'<h2>Property details from official tax records</h2><div class="card pd">{photo}<div><div class="kv">'
            f'<div><b>Parcel</b></div><div>{E(e["parcel"])}</div>{rows}</div>'
            f'<p class="muted">Source: <a href="{E(e["source_url"])}" rel="nofollow">{E(e["source"])}</a> · retrieved {asof_txt}'
            + (f' · record updated {E(e["data_date"])}' if e.get("data_date") else "") + '. ' + E(e.get("note") or "") + ' Always confirm with the county.</p></div></div>')

import csv as _csv
INFO = json.load(open(os.path.join(ROOT, "ref", "county_info.json")))
LAW = {"ohio": [
  ("What is the minimum bid at an Ohio sheriff sale?", "For most foreclosure sales the property cannot sell for less than two-thirds of its court-ordered appraised value (Ohio Revised Code 2329.20). If it does not sell, it is typically offered again at a second sale with no minimum, as published for each property.", "https://codes.ohio.gov/ohio-revised-code/section-2329.20"),
  ("How much deposit do I need?", "Ohio law sets the deposit by appraised value: $2,000 if appraised at $10,000 or less, $5,000 if over $10,000 up to $200,000, and $10,000 if over $200,000 (Ohio Revised Code 2329.211). The plaintiff/judgment creditor is not required to make a deposit.", "https://codes.ohio.gov/ohio-revised-code/section-2329.211"),
  ("Can the owner still stop the sale?", "An Ohio owner can redeem the property by paying the judgment, interest and costs any time before the court confirms the sale (Ohio Revised Code 2329.33). Sales are also often cancelled or postponed, so always re-check the official list.", "https://codes.ohio.gov/ohio-revised-code/section-2329.33")],
 "new-jersey": [
  ("Can a New Jersey sheriff sale be postponed?", "Yes. New Jersey law lets the defendant (owner) request up to two adjournments of a sheriff sale, and the plaintiff or court can postpone it further (N.J.S.A. 2A:17-36). That is why many listings show several postponements.", "https://lis.njleg.state.nj.us/"),
  ("Can the owner redeem after the sale?", "Under the New Jersey Court Rules (R. 4:65-5) there is a 10-day period after the sale for objections, and the owner may redeem during that time before the deed is delivered.", "https://www.njcourts.gov/attorneys/rules-of-court")]}
ADJ = {}
for _l in open(os.path.join(ROOT, "ref", "adj.txt"), encoding="latin-1").read().splitlines()[1:]:
    _p = _l.split("|")
    if len(_p) == 4 and _p[0] != _p[2]: ADJ.setdefault(_p[0], []).append(_p[2])
def neighbors(cn, ab):
    return [n.split(" County,")[0] for n in ADJ.get(f"{cn} County, {ab}", []) if n.endswith(", " + ab)]
DOW = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
def county_seo(st, cn, d, items):
    sn, ab = STATES[st]; key = f"{st}/{slug(cn)}"; inf = INFO.get(key); facts = []; faq = []
    if items:
        days = {}; [days.__setitem__(DOW[datetime.date.fromisoformat(i["sale_date"]).weekday()], days.get(DOW[datetime.date.fromisoformat(i["sale_date"]).weekday()], 0) + 1) for i in items]
        dd = ", ".join(f"{k}s ({v})" for k, v in sorted(days.items(), key=lambda x: -x[1]))
        facts.append(f'On the official list as of {asof(d["as_of"])}, {len(items)} upcoming sales fall on: {dd}. Next sale: {fdate(items[0]["sale_date"])}.')
        types = sorted({i["sale_type"] for i in items if i.get("sale_type")})
        if types: facts.append("Sale types listed: " + "; ".join(types) + ".")
        r = [i["opening_bid"] / i["appraised_value"] for i in items if i.get("opening_bid") and i.get("appraised_value")]
        if r: facts.append(f"Where both are published, the opening bid is a median {sorted(r)[len(r)//2]:.0%} of the appraised value ({len(r)} listings).")
        dep = sorted({i["deposit"] for i in items if i.get("deposit")})
        if dep: facts.append("Deposits published on this list: " + ", ".join(usd(x) for x in dep[:6]) + ".")
        pc = [i for i in items if i.get("times_postponed")]
        if pc: facts.append(f"{len(pc)} of {len(items)} listings show at least one postponement in the official status history.")
    intro = "".join(f"<li>{E(x)}</li>" for x in facts)
    off = ""
    if inf: off = "<h3>From the county's official pages</h3><ul>" + "".join(f"<li>{E(x)}</li>" for x in inf["facts"]) + f'</ul><p class="muted">Source: <a href="{E(inf["src"])}" rel="nofollow">{E(inf["src"])}</a></p>'
    faq.append((f"Where do {cn} County sheriff sale listings come from?", f"DeedHound compiles them from the official list published at {d['source'] or 'the county sheriff site'}, refreshed daily. Always confirm with the official legal notice."))
    if items: faq.append((f"How many {cn} County sheriff sales are coming up?", f"{len(items)} upcoming sales as of {asof(d['as_of'])}; the next is {fdate(items[0]['sale_date'])}."))
    if inf: faq += [(f"How do {cn} County sheriff sales work?", " ".join(inf["facts"][:3]))]
    law = [(q, a + f" Source: {u}") for q, a, u in LAW.get(st, [])]
    faq += law
    nb = neighbors(cn, ab)
    return intro, off, faq, nb
def faq_html(faq): return "<h2>Frequently asked questions</h2>" + "".join(f'<details class="card"><summary><b>{E(q)}</b></summary><p>{E(a)}</p></details>' for q, a in faq)
def faq_ld(faq): return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
COVERED = {(os.path.basename(os.path.dirname(f)), os.path.basename(f)[:-5]) for f in glob.glob(os.path.join(ROOT, "data", "*", "*.json")) if "enrich" not in f}
def nb_html(st, nb):
    if not nb: return ""
    return "<h2>Neighboring counties</h2><p>" + " · ".join(f'<a href="/{st}/{slug(n)}-county/">{E(n)} County</a>' for n in nb if st == "ohio" or (st, slug(n)) in COVERED) + "</p>"
def build_guides(st, urls):
    if st != "ohio": return []
    sn, ab = STATES[st]; out = []
    for r in _csv.DictReader(open(os.path.join(ROOT, "county_sources.csv"))):
        cn = r["county"]; s = slug(cn)
        if (st, s) in COVERED: continue
        inf = INFO.get(f"{st}/{s}"); offu = (inf or {}).get("src") or r.get("official_list_url") or ""
        if "civilview" in offu: offu = ""
        ra = f"https://{s.replace('-','')}.sheriffsaleauction.ohio.gov"
        facts = "".join(f"<li>{E(x)}</li>" for x in (inf or {}).get("facts", []))
        faq = [(f"Does DeedHound list {cn} County sheriff sales?", f"Not yet. We only publish listings from official sources whose terms and robots.txt allow it, and {cn} County's list is not available to us that way yet."),
               (f"Where can I see {cn} County sheriff sales?", f"On the state's official sheriff sale website for the county ({ra})" + (f" and the county's official page ({offu})." if offu else "."))]
        faq += [(q, a + f" Source: {u}") for q, a, u in LAW["ohio"]]
        body = (f'<h1>How to find {cn} County, Ohio sheriff sales</h1><p class="warn"><b>DeedHound doesn\'t list {cn} County sales yet.</b> Here is where the official listings are and how the sales work.</p>'
                f'<div class="card"><h2 style="margin-top:0">Official links</h2><ul>' + (f'<li><a href="{E(offu)}" rel="nofollow">{cn} County official sheriff sale page</a></li>' if offu else "")
                + f'<li><a href="{ra}" rel="nofollow">{cn} County official online sheriff sale site (Realauction, run under contract with the Ohio Department of Administrative Services)</a></li></ul></div>'
                + (f'<div class="card"><h2 style="margin-top:0">How sales work in {cn} County</h2><ul>{facts}</ul><p class="muted">Source: <a href="{E(inf["src"])}" rel="nofollow">{E(inf["src"])}</a></p></div>' if inf else "")
                + NL.replace("Get the weekly sheriff sale email", f"Get notified when we add {cn} County") + faq_html(faq) + nb_html(st, neighbors(cn, ab)) + DISC)
        u = f"/{st}/{s}-county/"
        page(u.strip("/") + "/index.html", f"How to Find {cn} County Ohio Sheriff Sales – Official Links & Rules | {BRAND['name']}",
             f"Where to find {cn} County, Ohio sheriff sales: official sheriff and auction site links, deposit and 2/3 minimum bid rules. DeedHound doesn't list this county yet.",
             body, [faq_ld(faq)], [("Home", "/"), (sn, f"/{st}/"), (f"{cn} County", u)]); urls.append(u); out.append((cn, u))
    return out
def build_state(st, urls):
    sn, ab = STATES[st]; today = datetime.date.today().isoformat(); counties = []; allitems = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data", st, "*.json"))):
        d = json.load(open(f)); cn = d["county"].replace("-", " ").title(); cs = f"/{st}/{slug(cn)}-county"
        items = sorted([i for i in d["items"] if i["sale_date"] >= today and not DEAD.search(i["status"] or "")], key=lambda i: (i["sale_date"], i["address"] or ""))
        for i in items:
            i["county_name"] = cn; i["url"] = f'{cs}/{slug(i["city"]) or "unknown-city"}/{slug(i["address"])}-{slug(i["case_number"])}/'
        counties.append((cn, cs, d, items)); allitems += items
    if not counties: return None
    for cn, cs, d, items in counties:
        cities = {}
        for i in items: cities.setdefault(i["city"] or "Unknown city", []).append(i)
        bid = f"https://{d['county'].replace('-','')}.sheriffsaleauction.ohio.gov" if st == "ohio" else "https://salesweb.civilview.com/"
        for i in items:
            full = f'{i["address"]}, {i["city"]}, {ab} {i["zip"] or ""}'.strip()
            ld = {"@context": "https://schema.org", "@type": "Event", "name": f"Sheriff sale: {full}", "startDate": i["sale_date"],
                  "eventStatus": "https://schema.org/EventScheduled", "organizer": {"@type": "Organization", "name": f"{cn} County Sheriff", "url": d["source"]},
                  "location": {"@type": "Place", "name": full, "address": {"@type": "PostalAddress", "streetAddress": i["address"], "addressLocality": i["city"], "postalCode": i["zip"], "addressRegion": ab, "addressCountry": "US"}},
                  "offers": {"@type": "Offer", "price": i["opening_bid"], "priceCurrency": "USD", "url": i["source_url"]} if i["opening_bid"] else None}
            kv = [("Sale date", fdate(i["sale_date"]) + f' ({E(i["sale_type"])})'), ("Address", E(full)), ("County", cn), ("Appraised value", usd(i["appraised_value"])),
                  ("Minimum / opening bid", usd(i["opening_bid"]) + (f' <span class="muted">({i["opening_bid"]/i["appraised_value"]:.0%} of appraisal)</span>' if i["opening_bid"] and i["appraised_value"] else ""))]
            if i.get("next_sale_date"): kv.append(("Next sale date if no bid", E(i["next_sale_date"]) + ' <span class="muted">as published by the Sheriff</span>'))
            if i.get("upset_amount"): kv.append(("Approx. upset / judgment*", usd(i["upset_amount"]) + ' <span class="muted">*as published by the Sheriff; excludes interest and fees</span>'))
            kv += [("Case number", E(i["case_number"])), ("Sheriff #", E(i.get("sheriff_number") or "—")), ("Parcel ID", E(i["parcel_id"] or "—")),
                  ("Plaintiff / lender", E(i["plaintiff"]) if i["plaintiff"] else '<span class="muted">Not on this county\'s published list — see the court docket</span>'), ("Plaintiff\'s attorney", E(i.get("attorney") or "—")),
                  ("Current status", E(i["status"])), ("Status history", hist_html(i))]
            body = (f'<h1>{E(i["address"])}, {E(i["city"])}</h1><p class="muted">{cn} County, {sn} sheriff sale · Data as of {asof(i["as_of"])}</p>'
                    '<div class="card kv">' + "".join(f"<div><b>{k}</b></div><div>{v}</div>" for k, v in kv) + '</div>' + enrich_html(i, full) +
                    f'<p><a href="{E(i["source_url"])}" rel="nofollow">See this listing on the official {cn} County Sheriff list →</a>'
                    + (f'<br><a href="{bid}" rel="nofollow">Register / bid on the official {cn} County sale site →</a>' if st == "ohio" else "") + f'</p>{DISC}{NL}')
            page(i["url"].strip("/") + "/index.html", f'{i["address"]}, {i["city"]} {ab} – Sheriff Sale {fdate(i["sale_date"])} | {BRAND["name"]}',
                 f'Sheriff sale {fdate(i["sale_date"])}: {full}. Case {i["case_number"]}.', body, {k: v for k, v in ld.items() if v},
                 [("Home", "/"), (sn, f"/{st}/"), (f"{cn} County", f"{cs}/"), (i["city"], f'{cs}/{slug(i["city"]) or "unknown-city"}/'), (i["address"], i["url"])]); urls.append(i["url"])
        for c, its in cities.items():
            u = f"{cs}/{slug(c)}/"
            page(u.strip("/") + "/index.html", f"{c}, {ab} Sheriff Sales ({len(its)} upcoming) | {BRAND['name']}", f"{len(its)} upcoming sheriff sales in {c}, {cn} County, {sn}.",
                 f'<h1>{E(c)}, {sn} sheriff sales</h1><p class="muted">{len(its)} upcoming in {E(c)}, {cn} County · Data as of {asof(d["as_of"])} · Source: <a href="{d["source"]}" rel="nofollow">official {cn} County list</a></p>{table(its)}<p>More: <a href="{cs}/">all {cn} County sheriff sales</a> · ' + " · ".join(f'<a href="{cs}/{slug(o)}/">{E(o)}</a>' for o in sorted(cities) if o != c) + f'</p>{DISC}{NL}', None,
                 [("Home", "/"), (sn, f"/{st}/"), (f"{cn} County", f"{cs}/"), (c, u)]); urls.append(u)
        clinks = " · ".join(f'<a href="{cs}/{slug(c)}/">{E(c)} ({len(v)})</a>' for c, v in sorted(cities.items()))
        intro, off, faq, nb = county_seo(st, cn, d, items); ad = datetime.datetime.fromisoformat(d["as_of"]).strftime("%b %-d, %Y")
        body = (f'<h1>{cn} County, {sn} sheriff sales</h1><p class="muted">{len(items)} upcoming · Data as of {asof(d["as_of"])} · '
                f'Source: <a href="{d["source"]}" rel="nofollow">official {cn} County Sheriff list</a></p>'
                f'<div class="card"><h2 style="margin-top:0">How {cn} County sheriff sales work</h2><ul>{intro}</ul>{off}</div><div class="card"><b>Cities and towns:</b> {clinks or "—"}</div>'
                + (table(items) if items else "<p>No upcoming sales listed right now.</p>") + faq_html(faq) + nb_html(st, nb) + DISC + NL)
        page(f"{cs.strip('/')}/index.html", f"{cn} County {sn} Sheriff Sales – {len(items)} Upcoming Foreclosure Auctions (as of {ad})", f"{len(items)} upcoming {cn} County, {sn} sheriff sales and foreclosure auctions as of {ad}, from the official county list: dates, addresses, appraisals, minimum bids, and how sales work.",
             body, [{"@context": "https://schema.org", "@type": "ItemList", "numberOfItems": len(items), "itemListElement": [{"@type": "ListItem", "position": n + 1, "url": BASE + i["url"]} for n, i in enumerate(items[:200])]}, faq_ld(faq)],
             [("Home", "/"), (sn, f"/{st}/"), (f"{cn} County", f"{cs}/")]); urls.append(f"{cs}/")
    guides = build_guides(st, urls)
    allitems.sort(key=lambda i: i["sale_date"]); oldest = min(asof(d["as_of"]) for _, _, d, _ in counties)
    grid = "".join(f'<a href="{cs}/"><b>{len(it)}</b>{cn} County<br><span class="muted">as of {asof(d["as_of"])}</span></a>' for cn, cs, d, it in sorted(counties, key=lambda x: -len(x[3])))
    body = (f'<h1>Upcoming {sn} sheriff sales</h1><p>Free list of foreclosure sheriff sales compiled from lists published by county sheriffs. '
            f'<span class="muted">{len(allitems)} upcoming sales in {len(counties)} counties · data as of {oldest} or later</span></p>{NL}'
            f'<h2 id="counties">Counties</h2><div class="grid">{grid}</div><h2>Next 7 days</h2>'
            + table([i for i in allitems if i["sale_date"] <= (datetime.date.today() + datetime.timedelta(days=7)).isoformat()], True) + picks(st, allitems) + (('<h2>Counties we don\'t list yet</h2><p class="muted">Guides with official links and rules:</p><p>' + " · ".join(f'<a href="{u}">{E(n)}</a>' for n, u in guides) + '</p>') if guides else "") + DISC)
    page(f"{st}/index.html", f"{sn} Sheriff Sales – Upcoming Foreclosure Auctions | {BRAND['name']}", f"Free list of upcoming {sn} sheriff sales.", body, None, [("Home", "/"), (sn, f"/{st}/")])
    urls.append(f"/{st}/"); return (st, sn, len(allitems), len(counties), oldest)
def main():
    shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT); open(os.path.join(OUT, "style.css"), "w").write(CSS); open(os.path.join(OUT, ".nojekyll"), "w").close(); shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(OUT, "assets"))
    urls = ["/"]; stats = [x for x in (build_state(st, urls) for st in STATES) if x]
    grid = "".join(f'<a href="/{st}/"><b>{n}</b>{sn}<br><span class="muted">{c} counties · as of {o}</span></a>' for st, sn, n, c, o in stats)
    body = (f'<h1>{E(BRAND["tagline"])}</h1><p>Free, plain-English lists of upcoming sheriff sales, compiled from lists published by county sheriffs. Pick your state:</p>'
            f'<div class="grid">{grid}</div>{NL}{DISC}')
    page("index.html", f'{BRAND["name"]} – {BRAND["tagline"]}', "Free lists of upcoming sheriff sales and foreclosure auctions by state and county.", body,
         {"@context": "https://schema.org", "@type": "WebSite", "name": BRAND["name"], "url": BASE + "/"})
    today = datetime.date.today().isoformat()
    open(os.path.join(OUT, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
        "".join(f"<url><loc>{BASE}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls) + "</urlset>")
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    print(len(urls), "pages;", stats)
main()
