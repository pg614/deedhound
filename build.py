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
STATES = {"ohio": ("Ohio", "OH"), "pennsylvania": ("Pennsylvania", "PA"), "kentucky": ("Kentucky", "KY"), "new-jersey": ("New Jersey", "NJ")}
def E(s): return html.escape(str(s)) if s is not None else ""
def slug(s): return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
def usd(v): return "—" if v is None else f"${v:,.0f}"
def fdate(d): return datetime.date.fromisoformat(d).strftime("%a, %b %-d, %Y")
def asof(a): return datetime.datetime.fromisoformat(a).strftime("%b %-d, %Y %-I:%M %p ET")
CSS = open(os.path.join(ROOT, "assets_src", "style.css")).read().replace("NAVY", BRAND["navy"]).replace("GOLD", BRAND["gold"])
DISC = ('<p class="warn"><b>Verify before you bid.</b> This is an unofficial summary of public sheriff-sale listings. Sales are often cancelled or '
        'postponed. Always confirm details with the official legal notice and the county sheriff\'s official sale site linked on each page. Not legal or financial advice.</p>')
SUB = "https://deedhound.beehiiv.com/subscribe"
INDEXNOW_KEY = CFG.get("indexnow_key", "")
NL = ('<div class="nlstrip"><div><h2>Get the weekly sheriff sale email</h2><p>One plain, easy-to-read email each week with the best new sheriff sale picks. Free. Unsubscribe anytime.</p></div>'
      '<a class="sbtn big" href="/newsletter/">Sign up free →</a></div>')
BAR = ('<div class="sbar"><div class="w"><span>📬 Get the week\'s best sheriff sale picks by email. <b>Free.</b></span>'
       '<a class="sbtn" href="/newsletter/">Sign up free</a></div></div>')
THEME_HEAD = '<script>(function(){try{var t=localStorage.getItem("theme")}catch(e){}if(t!=="light"&&t!=="dark")t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.setAttribute("data-theme",t)})()</script>'
THEME_FOOT = '<script>(function(){var b=document.getElementById("thm"),d=document.documentElement;function sync(){var k=d.getAttribute("data-theme")==="dark";b.querySelector(".ic").textContent=k?"☀️":"🌙";b.querySelector(".tx").textContent=k?"Light mode":"Dark mode";b.setAttribute("aria-pressed",k)}sync();b.onclick=function(){var t=d.getAttribute("data-theme")==="dark"?"light":"dark";d.setAttribute("data-theme",t);try{localStorage.setItem("theme",t)}catch(e){}sync()}})()</script>'
def _abs(u): return u if not u or u.startswith("http") else BASE + "/" + u.lstrip("/")
OG_IMG = BASE + "/assets/deedhound-logo.jpg"
LD_IMG = OG_IMG
def _vfrom(i, d):
    v = i.get("first_seen") or i.get("as_of") or d.get("as_of")
    return v or None
def _ldesc(i, full, ab):
    p = [f'Sheriff sale of {full}.']
    if i.get("case_number"): p.append(f'Case {i["case_number"]}.')
    if i.get("sale_type"): p.append(f'{i["sale_type"]}.')
    if i.get("appraised_value"): p.append(f'Appraised ${i["appraised_value"]:,.0f}.')
    if i.get("opening_bid"): p.append(f'Minimum bid ${i["opening_bid"]:,.0f}.')
    out = ""
    for x in p:
        if len(out) + len(x) + 1 > 299: break
        out = (out + " " + x).strip()
    return out
OGIMG = f'<meta property="og:image" content="{OG_IMG}"><meta name="twitter:image" content="{OG_IMG}">'
GA_ID = CFG.get("ga4_measurement_id", "")
GA_HEAD = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag("js",new Date());gtag("config","{GA_ID}");</script>') if GA_ID else ""
GA_FOOT = ('<script>(function(){if(!window.gtag)return;var sent={};function loc(el){if(!el||!el.closest)return"page";if(el.closest(".sbar"))return"bar";if(el.closest(".hd"))return"header";if(el.closest(".sigrow"))return"hero";if(el.closest(".hero"))return"hero";if(el.closest("footer"))return"footer";if(el.closest("[data-beehiiv-form],.card:has(script[data-beehiiv-form])"))return"beehiiv_form";if(location.pathname.indexOf("/newsletter/")===0)return"newsletter_page";return"card"}'
    'function ev(l,how){gtag("event","newsletter_signup",{location:l,method:how,page_path:location.pathname})}'
    'var RX=/(newsletter|subscribe|sign.?up|waitlist|join|beehiiv)/i;'
    'document.addEventListener("click",function(e){var a=e.target.closest&&e.target.closest("a,button,input[type=submit]");if(!a)return;var h=a.getAttribute("href")||"";if(/\\/newsletter\\/|beehiiv/i.test(h)||(a.tagName!=="A"&&RX.test(a.textContent+" "+(a.value||""))))ev(loc(a),"click")},true);'
    'document.addEventListener("submit",function(e){var f=e.target;if(RX.test((f.action||"")+" "+(f.className||"")+" "+(f.id||"")))ev(loc(f),"submit")},true);'
    'window.addEventListener("blur",function(){setTimeout(function(){var f=document.activeElement;if(f&&f.tagName==="IFRAME"&&/beehiiv/i.test(f.src||"")&&!sent[f.src]){sent[f.src]=1;ev(loc(f),"iframe_focus")}},0)})})()</script>') if GA_ID else ""
LM = {}
def page(path, title, desc, body, ld=None, crumbs=None, top=""):
    canon = BASE + "/" + path.replace("index.html", "")
    lds = (ld if isinstance(ld, list) else [ld]) if ld else []
    if crumbs: lds.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + u} for i, (n, u) in enumerate(crumbs)]})
    nav = " › ".join(f'<a href="{u}">{E(n)}</a>' for n, u in crumbs) if crumbs else ""
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{GA_HEAD}
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canon}">{THEME_HEAD}<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Libre+Franklin:wght@400;600;700&family=Playfair+Display:wght@800&display=swap"><link rel="stylesheet" href="/style.css"><link rel="icon" href="{BRAND.get("favicon","")}"><link rel="apple-touch-icon" href="{BRAND.get("apple_icon","")}"><meta name="theme-color" content="{BRAND["navy"]}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canon}"><meta property="og:type" content="website"><meta property="og:site_name" content="{E(BRAND["name"])}"><meta property="og:locale" content="en_US">{OGIMG}<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}">
{''.join(f'<script type="application/ld+json">{json.dumps(x)}</script>' for x in lds)}</head><body>
<a class="skip" href="#main">Skip to content</a><header class="hd"><div class="w nav"><a class="logo" href="/"><img src="/assets/deedhound-logo.jpg" alt="" width="48" height="48"><span>DeedHound<small>{E(BRAND["tagline"])}</small></span></a><nav aria-label="States">{"".join(f'<a href="/{k}/">{v[0]}</a>' for k,v in STATES.items())}</nav><span class="sp"></span><button class="thm" type="button" id="thm" aria-label="Switch light or dark mode"><span class="ic" aria-hidden="true">🌙</span><span class="tx">Dark mode</span></button><a class="sbtn hdcta" href="/newsletter/">Free email</a></div></header>
{top}<main class="w" id="main">{('<p class="crumb">'+nav+'</p>') if nav else ""}{body}</main>
<footer class="ft"><div class="w"><div class="fcols"><div><b>DeedHound</b><p>Data compiled from lists published by county sheriffs' offices. Bidding happens on each county's official sale site.</p></div><div><b>States</b><p>{" · ".join(f'<a href="/{k}/">{v[0]}</a>' for k,v in STATES.items())}</p></div><div><b>Guides</b><p><a href="/deal-check/">How Deal Check works</a> · <a href="/financing/">How to pay</a> · <a href="/newsletter/">Free weekly email</a></p></div></div>{DISC}</div></footer>{THEME_FOOT}{GA_FOOT}</body></html>"""
    if path.startswith("kentucky/"): doc = doc.replace("County Sheriff list", "County Master Commissioner list").replace("as published by the Sheriff", "as published by the Master Commissioner").replace(' County Sheriff"', ' County Master Commissioner"').replace("Kentucky sheriff sales", "Kentucky master commissioner sales").replace("Kentucky Sheriff Sales", "Kentucky Master Commissioner Sales").replace("County sheriff sales work", "County master commissioner sales work").replace("Kentucky sheriff sale ·", "Kentucky master commissioner sale ·")
    fp = os.path.join(OUT, path); os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, "w").write(_bp(doc))
def table(items, show_county=False):
    def row(i):
        v = i["appraised_value"] or i.get("upset_amount")
        return (f'<tr><td data-l="Deal Check">{DCK.badge(i["grade"]) if i.get("grade") else ""}</td><td class="adr"><a href="{i["url"]}">{E(i["address"] or "Address not published")}</a><span>{E(i["city"])}' + (f' · {E(i["county_name"])} Co.' if show_county else "") + '</span></td>'
                f'<td data-l="Sale date">{fdate(i["sale_date"])}</td><td class="n" data-l="Appraised / owed*">{usd(v)}</td><td class="n" data-l="Min. bid">{usd(i["opening_bid"])}</td><td class="lend" data-l="Lender">{E((i.get("plaintiff") or "—")[:28])}</td></tr>')
    return ('<div class="scroll"><table class="tbl"><thead><tr><th>Deal Check</th><th>Property</th><th>Sale date</th><th class="n">Appraised / owed*</th><th class="n">Min. bid</th><th>Lender</th></tr></thead><tbody>'
            + "".join(row(i) for i in items) + '</tbody></table></div>')
REGION = {"ohio": {"montgomery":"Southwest","wood":"Northwest","allen":"Northwest","stark":"Northeast","lorain":"Northeast","medina":"Northeast","richland":"North Central",
   "portage":"Northeast","trumbull":"Northeast","mahoning":"Northeast","summit":"Northeast","clermont":"Southwest","clark":"Southwest"},
  "new-jersey": {"bergen":"North","essex":"North","hudson":"North","passaic":"North","morris":"North","union":"North","hunterdon":"Central","middlesex":"Central","monmouth":"Central","ocean":"Central",
   "burlington":"South","camden":"South","gloucester":"South","salem":"South","cumberland":"South","atlantic":"South","cape-may":"South"},
  "pennsylvania": {"philadelphia":"Southeast","montgomery":"Southeast","lehigh":"Lehigh Valley"},
  "kentucky": {"jefferson":"Louisville area","fayette":"Lexington area"}}
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
import dealcheck as DCK
NOTES_P = os.path.join(ROOT, "data", "notes", "strong_notes.json"); NOTES = json.load(open(NOTES_P)) if os.path.exists(NOTES_P) else {}; NEED_NOTES = []
def note_html(i):
    n = NOTES.get(i["url"].strip("/"))
    if i.get("grade") != "Strong": return ""
    if not n: NEED_NOTES.append(i["url"].strip("/")); return ""
    return ('<div class="card" style="font-size:20px"><h2 style="margin-top:0">What to check before bidding</h2><ul>' + "".join(f"<li>{E(b)}</li>" for b in n["bullets"]) +
            f'</ul><p class="muted">AI-written checklist based on public records as of {datetime.date.fromisoformat(n["as_of"]).strftime("%b %-d, %Y")}. Not financial advice.</p></div>')
GRADES={}
INFO = json.load(open(os.path.join(ROOT, "ref", "county_info.json")))
LAW = {"ohio": [
  ("What is the minimum bid at an Ohio sheriff sale?", "For most foreclosure sales the property cannot sell for less than two-thirds of its court-ordered appraised value (Ohio Revised Code 2329.20). If it does not sell, it is typically offered again at a second sale with no minimum, as published for each property.", "https://codes.ohio.gov/ohio-revised-code/section-2329.20"),
  ("How much deposit do I need?", "For residential property, Ohio law sets the deposit by appraised value: $2,000 if appraised at $10,000 or less, $5,000 if over $10,000 up to $200,000, and $10,000 if over $200,000 (Ohio Revised Code 2329.211). The plaintiff/judgment creditor is not required to make a deposit.", "https://codes.ohio.gov/ohio-revised-code/section-2329.211"),
  ("Can the owner still stop the sale?", "An Ohio owner can redeem the property by paying the judgment, interest and costs any time before the court confirms the sale (Ohio Revised Code 2329.33). Sales are also often cancelled or postponed, so always re-check the official list.", "https://codes.ohio.gov/ohio-revised-code/section-2329.33")],
 "pennsylvania": [
  ("How do Philadelphia and Montgomery County sheriff sales work?", "Both counties hold sheriff sales online at Bid4Assets. You register free, send a deposit before the auction ($10,000 for mortgage foreclosure sales; $1,500 for Philadelphia tax sales, plus a $35 fee), and bid online. Philadelphia wants 10% plus a buyer's premium the next business day and the balance within 15 days; Montgomery wants the full balance within 12 calendar days.", "https://phillysheriff.com/frequently-asked-questions-about-online-sheriff-sales/"),
  ("How do Lehigh County sheriff sales work?", "Lehigh County holds sales in person at 10:00 AM at the courthouse, 455 West Hamilton Street, Allentown. The winner pays 10% right away by certified or cashier's check, plus poundage and transfer taxes; the balance is due within 30 days or the deposit can be forfeited. The lender can adjourn a sale up to 130 days.", "https://www.lehighcounty.org/Departments/Sheriffs-Office/Sheriff-Sale"),
  ("Do I get clear title at a Pennsylvania sheriff sale?", "Not guaranteed. Properties are sold as-is, and the sheriffs say bidders are responsible for searching liens and mortgages that may not be paid off from the sale (the 'Schedule of Distribution'). Get a title search before you bid.", "https://phillysheriff.com/real-estate/conditions-of-sale-mortgage/")],
 "kentucky": [
  ("Is there a minimum bid at a Kentucky master commissioner sale?", "Kentucky law does not set a fixed minimum bid. But if a court-ordered sale brings less than two-thirds (2/3) of the court appraisal, the former owner can buy the property back (redeem it) within six months of the sale by repaying the price plus 10% a year interest and certain costs (KRS 426.530). Buyers who want to avoid that risk bid at least 2/3 of the appraisal.", "https://apps.legislature.ky.gov/law/statutes/statute.aspx?id=45200"),
  ("How do I pay if I win?", "The Jefferson and Fayette commissioners' published terms: pay cash, or pay a 10% deposit at the sale and post a bond for the balance, which is due within 30 days with interest (KRS 426.705 bond). Check each sale's official notice.", "https://faycom.info/upcoming/"),
  ("Who runs the sale?", "In Kentucky, foreclosure sales ordered by the circuit court are held by the court's Master Commissioner, not the sheriff. Jefferson County sales are held at the Hall of Justice in Louisville; Fayette County sales at 120 North Limestone in Lexington unless held online.", "https://www.jeffcomm.org/")],
 "new-jersey": [
  ("Can a New Jersey sheriff sale be postponed?", "Yes. Under N.J.S.A. 2A:17-36 (as amended by P.L.2019, c.71) the sheriff may make up to five adjournments: two at the lender's request, two at the debtor's request, and one if both agree, each up to 30 calendar days. A court may order more for cause. That is why many listings show several postponements.", "https://pub.njleg.state.nj.us/Bills/2018/PL19/71_.PDF"),
  ("How much deposit does the winning bidder pay?", "State law (N.J.S.A. 2A:50-64, P.L.2019, c.71) requires the successful bidder to pay a 20 percent deposit, in cash or by certified or cashier's check payable to the county sheriff, immediately when the sale ends.", "https://pub.njleg.state.nj.us/Bills/2018/PL19/71_.PDF"),
  ("What happens in the 10 days after the sale?", "Under N.J. Court Rule 4:65-5 the sheriff delivers the deed unless a motion objecting to the sale is served within 10 days after the sale (or later, before the deed is delivered). The owner's right to redeem generally runs through that 10-day period, as the Appellate Division explained in MSND Financial v. 187 Loveladies Holdings (2024).", "https://www.njcourts.gov/system/files/court-opinions/2024/a1744-23.pdf")]}
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
ALL = []; SEEN = set(); DUPS = []; MERGED = []; SIDX = []
def build_state(st, urls):
    sn, ab = STATES[st]; today = datetime.date.today().isoformat(); counties = []; allitems = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data", st, "*.json"))):
        d = json.load(open(f)); cn = d["county"].replace("-", " ").title(); cs = f"/{st}/{slug(cn)}-county"
        items = sorted([i for i in d["items"] if i["sale_date"] >= today and not DEAD.search(i["status"] or "")], key=lambda i: (i["sale_date"], i["address"] or ""))
        mg = {}
        for i in items:  # some lists (e.g. Stark) post the 1st and 2nd sale date of one case as separate rows: merge them
            k = (i.get("case_number"), i.get("address"))
            if k[0] and k in mg:
                f = mg[k]; f["next_sale_date"] = f.get("next_sale_date") or i["sale_date"]; MERGED.append(k); continue
            mg[k] = i
        items = list(mg.values())
        for i in items:
            i["county_name"] = cn; u0 = f'{cs}/{slug(i["city"]) or "unknown-city"}/{slug(i["address"])}-{slug(i["case_number"])}'.rstrip("-"); u = u0; k = 2
            while u in SEEN: u = f"{u0}-{k}"; k += 1
            SEEN.add(u); i["url"] = u + "/"
            if k > 2: DUPS.append((u0, i.get("case_number"), i.get("sale_date"), i.get("parcel_id")))
        counties.append((cn, cs, d, items)); allitems += items; ALL.extend(items)
    if not counties: return None
    for cn, cs, d, items in counties:
        cities = {}
        for i in items: cities.setdefault(i["city"] or "Unknown city", []).append(i)
        bid = f"https://{d['county'].replace('-','')}.sheriffsaleauction.ohio.gov" if st == "ohio" else d["source"] if st == "kentucky" else "https://salesweb.civilview.com/"
        _tc = {}
        for i in items: _tc[(i["address"], i["city"], i["sale_date"])] = _tc.get((i["address"], i["city"], i["sale_date"]), 0) + 1
        for i in items:
            full = f'{i["address"]}, {i["city"]}, {ab} {i["zip"] or ""}'.strip()
            _shurl = "https://salesweb.civilview.com/" if st == "new-jersey" else d["source"]
            ld = {"@context": "https://schema.org", "@type": "Event", "name": f"Sheriff sale: {full}", "startDate": i["sale_date"],
                  "eventStatus": "https://schema.org/EventScheduled", "organizer": {"@type": "Organization", "name": f"{cn} County Sheriff", "url": _shurl},
                  "location": {"@type": "Place", "name": full, "address": {"@type": "PostalAddress", "streetAddress": i["address"], "addressLocality": i["city"], "postalCode": i["zip"], "addressRegion": ab, "addressCountry": "US"}},
                  "offers": {"@type": "Offer", **({"price": i["opening_bid"], "priceCurrency": "USD"} if i["opening_bid"] else {}), "url": i["source_url"], "availability": "https://schema.org/InStock", "validFrom": _vfrom(i, d)},
                  "endDate": i["sale_date"], "description": _ldesc(i, full, ab),
                  "performer": {"@type": "Organization", "name": f"{cn} County Sheriff", "url": _shurl}}
            if LD_IMG: ld["image"] = LD_IMG
            kv = [("Sale date", fdate(i["sale_date"]) + f' ({E(i["sale_type"])})'), ("Address", E(full)), ("County", cn), ("Appraised value", usd(i["appraised_value"])),
                  ("Minimum / opening bid", usd(i["opening_bid"]) + (f' <span class="muted">({i["opening_bid"]/i["appraised_value"]:.0%} of appraisal)</span>' if i["opening_bid"] and i["appraised_value"] else ""))]
            if i.get("next_sale_date"): kv.append(("Next sale date if no bid", E(i["next_sale_date"]) + ' <span class="muted">as published by the Sheriff</span>'))
            if i.get("upset_amount"): kv.append(("Debt amount*" if st == "pennsylvania" else "Approx. upset / judgment*", usd(i["upset_amount"]) + ' <span class="muted">*as published by the Sheriff; excludes interest and fees</span>'))
            kv += [("Case number", E(i["case_number"])), ("Sheriff #", E(i.get("sheriff_number") or "—")), (i.get("parcel_kind") or "Parcel ID", E(i["parcel_id"] or "—"))]
            kv += [(k, E(i[f])) for k, f in (("Book & Writ", "book_writ"), ("Ward", "ward"), ("Municipality", "municipality"), ("Property type (Sheriff)", "description")) if i.get(f)]
            kv += [
                  ("Plaintiff / lender", E(i["plaintiff"]) if i["plaintiff"] else '<span class="muted">Not on this county\'s published list — see the court docket</span>'), ("Plaintiff\'s attorney", E(i.get("attorney") or "—")),
                  ("Current status", E(i["status"])), ("Status history", hist_html(i))]
            _e = ENR.get(i.get("auction_id") or f'{i.get("county")}|{i["case_number"]}|{i["address"]}'); g, why, info = DCK.grade(st, i, _e); i["grade"] = g; i["dc"] = info; GRADES.setdefault(st, {}).setdefault(g, 0); GRADES[st][g] += 1
            body = (f'<h1>{E(i["address"])}, {E(i["city"])} {DCK.badge(g)}</h1><p class="muted">{cn} County, {sn} sheriff sale · Data as of {asof(i["as_of"])}</p>' + tiles_html(info, i) + DCK.summary(st, i, g, info, fdate) + DCK.bid_html(st, i, cn, bid, fdate, INFO.get(f"{st}/{slug(cn)}")) + DCK.deal_html(g, why) + note_html(i) +
                    '<div class="card kv">' + "".join(f"<div><b>{k}</b></div><div>{v}</div>" for k, v in kv) + '</div>' + enrich_html(i, full) +
                    f'<p><a href="{E(i["source_url"])}" rel="nofollow">See this listing on the official {cn} County Sheriff list →</a>'
                    + (f'<br><a href="{bid}" rel="nofollow">Register / bid on the official {cn} County sale site →</a>' if st == "ohio" else "") + f'</p>{DISC}{NL}')
            page(i["url"].strip("/") + "/index.html", (f'{i["address"]}, {i["city"]} {ab}' if i.get("address") else f'{cn} County {ab} case {i["case_number"]}') + f' – Sheriff Sale {fdate(i["sale_date"])}' + (f' (Case {i["case_number"]})' if _tc[(i["address"], i["city"], i["sale_date"])] > 1 else "") + f' | {BRAND["name"]}',
                 f'Sheriff sale {fdate(i["sale_date"])}: {full}. Case {i["case_number"]}.', body, {k: v for k, v in ld.items() if v} if i.get("address") and i.get("city") else None,
                 [("Home", "/"), (sn, f"/{st}/"), (f"{cn} County", f"{cs}/"), (i["city"], f'{cs}/{slug(i["city"]) or "unknown-city"}/'), (i["address"], i["url"])]); urls.append(i["url"]); LM[i["url"]] = str(i.get("as_of") or "")[:10]
        SIDX.append({"t": f"{cn} County, {ab}", "s": "county", "n": len(items), "u": f"{cs}/"})
        for c, its in cities.items():
            u = f"{cs}/{slug(c)}/"
            SIDX.append({"t": f"{c}, {ab}", "s": f"{cn} County", "n": len(its), "u": u, "z": sorted({str(i["zip"])[:5] for i in its if i.get("zip")})})
            page(u.strip("/") + "/index.html", f"{c}, {cn} County {ab} Sheriff Sales ({len(its)} upcoming) | {BRAND['name']}", f"{len(its)} upcoming sheriff sales in {c}, {cn} County, {sn}.",
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
             [("Home", "/"), (sn, f"/{st}/"), (f"{cn} County", f"{cs}/")]); urls.append(f"{cs}/"); LM[f"{cs}/"] = str(d.get("as_of") or "")[:10]
    guides = build_guides(st, urls)
    allitems.sort(key=lambda i: i["sale_date"]); oldest = min(asof(d["as_of"]) for _, _, d, _ in counties)
    grid = "".join(f'<a href="{cs}/"><b>{len(it)}</b>{cn} County<br><span class="muted">as of {asof(d["as_of"])}</span></a>' for cn, cs, d, it in sorted(counties, key=lambda x: -len(x[3])))
    body = (f'<h1>Upcoming {sn} sheriff sales</h1><p>Free list of foreclosure sheriff sales compiled from lists published by county sheriffs. '
            f'<span class="muted">{len(allitems)} upcoming sales in {len(counties)} counties · data as of {oldest} or later</span></p>{NL}'
            + top_deals(st, 6) + f'<h2 id="counties">Counties</h2><div class="grid">{grid}</div><h2>Next 7 days</h2>'
            + table([i for i in allitems if i["sale_date"] <= (datetime.date.today() + datetime.timedelta(days=7)).isoformat()], True) + picks(st, allitems) + (('<h2>Counties we don\'t list yet</h2><p class="muted">Guides with official links and rules:</p><p>' + " · ".join(f'<a href="{u}">{E(n)}</a>' for n, u in guides) + '</p>') if guides else "") + DISC)
    page(f"{st}/index.html", f"{sn} Sheriff Sales – Upcoming Foreclosure Auctions | {BRAND['name']}", f"Free list of upcoming {sn} sheriff sales.", body, None, [("Home", "/"), (sn, f"/{st}/")])
    urls.append(f"/{st}/"); return (st, sn, len(allitems), len(counties), oldest)
def top_deals(st, n):
    sn = STATES[st][0]; t = datetime.date.today().isoformat()
    c = sorted([i for i in ALL if i["url"].startswith(f"/{st}/") and i.get("grade") == "Strong" and i["sale_date"] >= t and i.get("address")], key=lambda i: i["dc"]["r"])[:n]
    if not c: return f"<h2>Top Strong deals in {sn}</h2><p>No upcoming listings grade Strong right now.</p>"
    lab = {"ohio": "Min. bid", "pennsylvania": "Min. bid / debt"}.get(st, "Owed to lender")
    li = "".join(f'<a class="dcard" href="{i["url"]}"><div class="ct">{DCK.badge("Strong")}<span class="date">{fdate(i["sale_date"])}</span></div><h3>{E(i["address"])}</h3><p class="loc">{E(i["city"])}, {STATES[st][1]} · {E(i["county_name"])} County</p><div class="nums"><div><small>{lab}</small><b>{usd(i["dc"]["price"])}</b></div><div><small>Value</small><b>{usd(i["dc"]["val"])}</b></div><div><small>Price ÷ value</small><b>{i["dc"]["r"]:.0%}</b></div></div>' + ('<p class="chk">Check first: ' + E(NOTES[i["url"].strip("/")]["bullets"][-1 if len(NOTES[i["url"].strip("/")]["bullets"])<2 else 0]) + '</p>' if i["url"].strip("/") in NOTES else "") + f'<p class="asof">Data as of {asof(i["as_of"])}</p></a>' for i in c)
    return f'<div class="sh"><h2>Top Strong deals in {sn}</h2><a href="/{st}/">See all {sn} sales →</a></div><p class="muted">Upcoming sales only, lowest price-to-value first.</p><div class="cgrid">{li}</div>'
def tiles_html(info, i):
    t = []
    if info.get("price"): t.append((info["pl"][:1].upper() + info["pl"][1:], usd(info["price"]), ""))
    if info.get("val"): t.append((info["vl"][:1].upper() + info["vl"][1:], usd(info["val"]), ""))
    if info.get("r") is not None: t.append(("Price is", f'{info["r"]:.0%}', "of value"))
    t.append(("Sale date", datetime.date.fromisoformat(i["sale_date"]).strftime("%b %-d"), datetime.date.fromisoformat(i["sale_date"]).strftime("%A")))
    return '<div class="ltiles">' + "".join(f'<div><small>{E(a)}</small><b>{b}</b>{f"<small>{E(c)}</small>" if c else ""}</div>' for a, b, c in t) + '</div>'
BEEHIIV = '<script async src="https://subscribe-forms.beehiiv.com/v3/loader.js" data-beehiiv-form="8cc00e28-eb77-4416-834b-c8a35f27f00f"></script>'
def home_top(stats):
    tot = sum(x[2] for x in stats); nc = sum(x[3] for x in stats); ns = len(stats); strong = sum(1 for i in ALL if i.get("grade") == "Strong")
    oldest = min((x[4] for x in stats), key=lambda s: datetime.datetime.strptime(s, "%b %d, %Y %I:%M %p ET"))
    tiles = [(f"{tot:,}", "upcoming sales"), (f"{nc}", "counties tracked"), (f"{ns}", "states"), (f"{strong:,}", "graded Strong")]
    chips = "".join(f'<a class="chip" href="/{st}/">{sn} <span>{n:,}</span></a>' for st, sn, n, c, o in stats)
    return (f'<section class="top"><div class="w hero"><span class="pill">Updated daily · data as of {oldest} or later</span>'
            f'<h1>Stop digging through {nc} sheriff websites.<br><em>We already did.</em></h1>'
            f'<p class="lead">Every upcoming sheriff sale in {", ".join(x[1] for x in stats[:-1])} and {stats[-1][1]}, with the minimum bid, the official value and a plain-English Deal Check. Free.</p>'
            '<form class="search" id="srch" action="/" role="search" onsubmit="return false"><label for="q" class="vh">Search a county, city or ZIP code</label><input id="q" type="search" autocomplete="off" placeholder="County, city or ZIP — e.g. Elyria or 44035" aria-controls="sres"><button class="cta" type="submit">Find sales</button><ul id="sres" class="sres" role="listbox" hidden></ul></form>'
            f'<nav class="chips" aria-label="Browse by state">{chips}</nav>'
            '<div class="tiles">' + "".join(f'<div class="tile"><b>{a}</b><span>{b}</span></div>' for a, b in tiles) + '</div></div></section>'
            '<section class="w sigrow" id="signup"><div><h2>Get the Friday list, free</h2><p>New sales, price changes and postponements in one plain email each week. Unsubscribe anytime.</p></div><div class="bh">' + BEEHIIV + f'<p class="muted">Form not showing? <a href="{SUB}">Sign up on Beehiiv →</a></p></div></section>'
            '<script src="/search.js" defer></script>')
def home_hero():
    return ('<p class="dcline">Each sale gets a quick Strong / Fair / Pass first look, with the math shown. <a href="/deal-check/"><b>How it works →</b></a></p>'
            '<p class="warn callnote"><b>Sales can be cancelled up to the last minute, so call the sheriff that morning.</b></p>' + top_deals("ohio", 6) + top_deals("pennsylvania", 6) + top_deals("kentucky", 6) + top_deals("new-jersey", 6))
def how_page(urls):
    c = DCK.DC
    body = (f'<h1>How Deal Check works</h1><div class="card" style="font-size:20px"><p>Deal Check divides a price by an official value:</p><ul>'
      f'<li><b>Ohio:</b> the published minimum/opening bid ÷ the county auditor market value (or, if we have not matched the auditor record, the sheriff\'s court-ordered appraisal). Ohio law (ORC 2329.20) usually sets the first-sale minimum at two-thirds of the appraisal, so many first sales grade Fair.</li>'
      f'<li><b>New Jersey:</b> no opening bid is published, so we use the approximate amount owed to the lender (judgment/upset) ÷ the town\'s net assessed value from the state MOD-IV tax list. Towns assess at different ratios, so treat it as a rough guide.</li>'
            f'<li><b>Kentucky:</b> no opening bid is published, so we use the judgment amount the sale must raise (from the Master Commissioner\'s notice) ÷ the commissioner\'s court-ordered appraisal. If a sale brings under 2/3 of the appraisal, the owner can redeem within 6 months (KRS 426.530). Strong: {c.get("ky_strong_max_ratio",0.5):.0%} or less; Fair: up to {c.get("ky_fair_max_ratio",0.75):.0%}.</li>'
      f'<li><b>Pennsylvania:</b> the published minimum bid (Philadelphia tax sales) or, if none, the debt amount the Sheriff publishes ÷ an official value: the City of Philadelphia Office of Property Assessment (OPA) market value. Montgomery County assesses at 1996 base-year values, which are far below today\'s prices, and Lehigh County\'s assessment lookup is not open to automated use, so Montgomery and Lehigh listings show "Not enough data" (Montgomery\'s county record is still shown on each listing). Tax sales with no published minimum bid show "Not enough data", because the tax debt is usually far below what the home will sell for. The lender can bid up to what it is owed, so the final price may be higher.</li></ul>'
      f'<p><b>Strong</b>: {c["strong_max_ratio"]:.0%} or less (Ohio) / {c["pa_strong_max_ratio"]:.0%} or less (PA) / {c["nj_strong_max_ratio"]:.0%} or less (NJ). <b>Fair</b>: up to {c["fair_max_ratio"]:.0%} (Ohio) / {c["pa_fair_max_ratio"]:.0%} (PA) / {c["nj_fair_max_ratio"]:.0%} (NJ). PA uses the same limits as NJ because both compare a debt-type number to a tax value. <b>Pass</b>: above that.</p>'
      f'<p>A grade drops one step after {c["postponements_downgrade_at"]} or more postponements. <b>Not enough data</b> means a number is missing, the official value is under {usd(c["min_value_usd"])}, or the published price is under {c["min_ratio_plausible"]:.0%} of value (usually a placeholder).</p>'
      '<p>Every listing shows its numbers, sources and "as of" dates in a "Why" list.</p><p><a href="/financing/"><b>How to pay for a sheriff sale →</b></a></p></div>'
      '<p class="warn"><b>Not financial advice.</b> Deal Check does not know the condition, occupancy, liens, title problems or back taxes. Inspect, run a title and lien search, and verify with the county before you bid.</p>')
    page("deal-check/index.html", f"How Deal Check Works | {BRAND['name']}", "How DeedHound grades sheriff sales Strong, Fair or Pass from published bids and official values.", body, None, [("Home", "/"), ("How Deal Check works", "/deal-check/")]); urls.append("/deal-check/")
def newsletter_page(urls):
    body = ('<h1>Get the weekly sheriff sale email</h1><p style="font-size:21px">One plain, easy-to-read email each week with the best new sheriff sale and foreclosure auction picks in Ohio, Pennsylvania, Kentucky and New Jersey, each with a simple Deal Check grade. Free. Unsubscribe anytime.</p>'
            '<div class="card bh"><script async src="https://subscribe-forms.beehiiv.com/v3/loader.js" data-beehiiv-form="8cc00e28-eb77-4416-834b-c8a35f27f00f"></script>'
            f'<p class="muted">Form not showing? <a class="sbtn" href="{SUB}">Sign up on our Beehiiv page →</a></p></div>'
            '<p class="muted">We never sell your email. Emails are sent through Beehiiv.</p>')
    page("newsletter/index.html", "Free weekly sheriff sale email – DeedHound", "Sign up for a free weekly email of the best sheriff sale picks in Ohio, Pennsylvania, Kentucky and New Jersey.", body, None, [("Home", "/"), ("Email signup", "/newsletter/")])
    urls.append("/newsletter/")
def main():
    shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT); open(os.path.join(OUT, "style.css"), "w").write(CSS); open(os.path.join(OUT, ".nojekyll"), "w").close(); _h=urllib.parse.urlparse(BASE).hostname or ""; (_h and not _h.endswith("github.io") and not BASE_PATH) and open(os.path.join(OUT, "CNAME"), "w").write(_h + "\n"); shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(OUT, "assets"))
    urls = ["/"]; stats = [x for x in (build_state(st, urls) for st in STATES) if x]; how_page(urls); import financing; financing.build(page, urls, BRAND); newsletter_page(urls)
    grid = "".join(f'<a href="/{st}/"><b>{n:,}</b>{sn}<br><span class="muted">{c} counties · as of {o}</span></a>' for st, sn, n, c, o in stats)
    body = (home_hero() + f'<h2>{E(BRAND["tagline"])}</h2><p>Free, plain-English lists of upcoming sheriff sales, compiled from lists published by county sheriffs. Pick your state:</p>'
            f'<div class="grid">{grid}</div>')
    page("index.html", f'{BRAND["name"]} – {BRAND["tagline"]}', "Free lists of upcoming sheriff sales and foreclosure auctions by state and county.", body,
         [{"@context": "https://schema.org", "@type": "WebSite", "name": BRAND["name"], "url": BASE + "/", "description": BRAND["tagline"]},
          {"@context": "https://schema.org", "@type": "Organization", "name": BRAND["name"], "url": BASE + "/", **({"logo": _abs(BRAND["logo"])} if BRAND.get("logo") else {})}], None, home_top(stats))
    json.dump(sorted(SIDX, key=lambda x: -x["n"]), open(os.path.join(OUT, "search.json"), "w"), separators=(",", ":"))
    shutil.copy(os.path.join(ROOT, "assets_src", "search.js"), os.path.join(OUT, "search.js"))
    today = datetime.date.today().isoformat()
    open(os.path.join(OUT, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
        "".join(f"<url><loc>{BASE}{u}</loc><lastmod>{LM.get(u) or today}</lastmod></url>" for u in dict.fromkeys(urls)) + "</urlset>")
    open(os.path.join(OUT, "urls.txt"), "w").write("".join(f"{BASE}{u}\n" for u in dict.fromkeys(urls)))
    if INDEXNOW_KEY: open(os.path.join(OUT, INDEXNOW_KEY + ".txt"), "w").write(INDEXNOW_KEY)
    llms = [f"# {BRAND['name']}", "", f"> {BRAND['tagline']}. Free, unofficial lists of upcoming sheriff sales and foreclosure auctions compiled daily from lists published by county sheriffs and Kentucky master commissioners. Always verify with the official county source before bidding; not legal or financial advice.", "",
            "## States", ""] + [f"- [{sn} sheriff sales]({BASE}/{st}/): {n} upcoming sales in {c} counties, data as of {o} or later" for st, sn, n, c, o in stats] + ["", "## Guides", "",
            f"- [How Deal Check works]({BASE}/deal-check/): how listings are graded Strong / Fair / Pass from published bids and official values",
            f"- [How to pay for a sheriff sale]({BASE}/financing/)", f"- [Free weekly email]({BASE}/newsletter/)", "", "## Optional", "", f"- [Sitemap]({BASE}/sitemap.xml): every county, city and listing page", ""]
    open(os.path.join(OUT, "llms.txt"), "w").write("\n".join(llms))
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    print("Strong listings needing notes:", len(NEED_NOTES), NEED_NOTES[:20]); print("GRADES", json.dumps(GRADES)); json.dump(ALL, open(os.path.join(ROOT,'site_items.json'),'w'), default=str); print(len(urls), "pages;", stats, "dup-slugs:", len(DUPS), "merged 2nd-sale rows:", len(MERGED)); [print(" ", x) for x in DUPS[:25]]
main()
