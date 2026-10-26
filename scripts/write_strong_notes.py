"""One-time writer for data/notes/strong_notes.json: checklist bullets built only from fields on each Strong listing.
Keeps existing notes; only adds notes for Strong listings that lack one. Run after build.py."""
import json, os, re, datetime
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = json.load(open(os.path.join(R, "site_items.json"))); ENR = json.load(open(os.path.join(R, "data/enrich/enrich.json")))
P = os.path.join(R, "data/notes/strong_notes.json"); N = json.load(open(P)) if os.path.exists(P) else {}
def usd(v): return f"${v:,.0f}"
def fact(e, n):
    for f in (e or {}).get("facts", []):
        if f[0] == n: return f[1]
today = datetime.date.today().isoformat()
for i in A:
    if i.get("grade") != "Strong": continue
    k = i["url"].strip("/")
    if k in N: continue
    oh = k.startswith("ohio/"); d = i["dc"]; e = ENR.get(i.get("auction_id") or f'{i.get("county")}|{i["case_number"]}|{i["address"]}')
    b = []
    imp = fact(e, "Assessed improvement value"); bld = fact(e, "Auditor market value – building")
    lot = re.search(r"vacant|\blot\b", i["address"] or "", re.I) or (str(fact(e, "Property class")) == "1") or imp == 0 or bld == 0
    if lot: b.append("This looks like a vacant lot (the address or tax record says so), so the value is mostly or all land. Check zoning and whether you can build on it.")
    if oh:
        b.append(f'The minimum bid ({usd(d["price"])}) is {d["r"]:.0%} of the {d["vl"]} ({usd(d["val"])}). Other bidders can push the price up on sale day.')
        if i.get("appraised_value") and "auditor" in d["vl"] and abs(i["appraised_value"] - d["val"]) / d["val"] > 0.25:
            b.append(f'The sheriff\'s appraisal ({usd(i["appraised_value"])}) and the auditor\'s value ({usd(d["val"])}) differ a lot. Look up both before you decide what it is worth.')
        if (i.get("sale_type") or "").lower().startswith("tax"): b.append("This is a tax foreclosure sale. Ask the county treasurer what taxes and assessments stay with the property.")
    else:
        b.append(f'The amount owed to the lender ({usd(d["price"])}) is {d["r"]:.0%} of the town\'s assessed value ({usd(d["val"])}). In New Jersey this is the lender\'s figure, not the final price, and assessed value is not market value.')
    tax = fact(e, "Last year's property tax"); atax = fact(e, "Annual property tax (after credits)")
    due = (fact(e, "Past-due taxes on county record") or 0) + (fact(e, "Past-due special assessments on county record") or 0)
    if due: b.append(f"The county record shows {usd(due)} in past-due taxes and assessments" + (f" (the yearly tax is about {usd(atax)})" if atax else "") + ". Ask the county treasurer what must be paid and who pays it.")
    elif atax: b.append(f"The yearly tax on the county record is about {usd(atax)}, with no past-due amount listed. Confirm with the county treasurer.")
    else: b.append((f"Last year's tax bill on record was {usd(tax)}. " if tax else "") + "Unpaid back taxes are not on the sheriff's list, so check with the county treasurer or town tax collector.")
    if i.get("times_postponed"): b.append(f'Already postponed {i["times_postponed"]} time(s). Check the official listing the day before the sale.')
    b.append("Drive by and look from the street: the official record doesn't say whether anyone lives there." if not lot else "Run a title and lien search: mortgages, liens or HOA dues may not be wiped out by this sale.")
    if len(b) < 5 and not lot: b.append("Run a title and lien search: other liens may survive the sale.")
    N[k] = {"bullets": b[:5], "as_of": i["as_of"][:10], "written": today}
json.dump(N, open(P, "w"), indent=1); print(len(N), "notes")
