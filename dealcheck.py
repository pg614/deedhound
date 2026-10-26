"""Deal Check: transparent Strong/Fair/Pass grade from published official fields only."""
import json, os, datetime, html
ROOT=os.path.dirname(os.path.abspath(__file__))
DC=json.load(open(os.path.join(ROOT,"config.json"))).get("deal_check",{})
def E(s): return html.escape(str(s)) if s is not None else ""
def usd(v): return f"${v:,.0f}"
def d(s): return datetime.datetime.fromisoformat(s).strftime("%b %-d, %Y")
def fact(e,name):
    for f in (e or {}).get("facts",[]):
        if f[0]==name: return f[1]
COLORS={"Strong":"#1b7f3b","Fair":"#b7791f","Pass":"#b42318","Not enough data":"#5b6475"}
def grade(st,i,e):
    """returns (grade, why[list of str], summary sentence parts dict)"""
    why=[]; src=f'official {i["county"].replace("-"," ").title()} County sheriff list, as of {d(i["as_of"])}'
    esrc=f'{e["source"]}, retrieved {d(e["retrieved"])}' if e else None
    if st=="ohio":
        price=i.get("opening_bid"); pl="minimum bid"
        mv=fact(e,"Auditor market value – total") or fact(e,"Auditor appraised total")
        if mv: val,vl,vs=mv,"county auditor market value",esrc
        else: val,vl,vs=i.get("appraised_value"),"sheriff's court-ordered appraisal",src
        sm,fm=DC["strong_max_ratio"],DC["fair_max_ratio"]
    else:
        price=i.get("upset_amount"); pl="approx. judgment/upset amount owed to the lender"
        val,vl,vs=fact(e,"Net assessed value"),"town's net assessed value (MOD-IV tax list)",esrc
        sm,fm=DC["nj_strong_max_ratio"],DC["nj_fair_max_ratio"]
    info={"price":price,"pl":pl,"val":val,"vl":vl}
    if not price: why.append(f"The {pl} is not published on the {src}.")
    if not val: why.append(f"No official {vl} is matched to this property yet.")
    if not price or not val: return "Not enough data",why,info
    if val<DC["min_value_usd"]:
        why.append(f"Official value {usd(val)} is under {usd(DC['min_value_usd'])}, often a vacant lot or partial interest."); return "Not enough data",why,info
    r=price/val; info["r"]=r
    if r<DC["min_ratio_plausible"]:
        why.append(f"Published {pl} {usd(price)} is under {DC['min_ratio_plausible']:.0%} of the official value {usd(val)}; this is usually a placeholder or a no-minimum later sale, not the real price. Check the official notice."); info.pop("r"); return "Not enough data",why,info
    why.append(f"{pl[0].upper()+pl[1:]}: {usd(price)} (source: {src}).")
    why.append(f"{vl[0].upper()+vl[1:]}: {usd(val)} (source: {vs}).")
    g="Strong" if r<=sm else "Fair" if r<=fm else "Pass"
    why.append(f"{usd(price)} ÷ {usd(val)} = {r:.0%}. Our rule: {sm:.0%} or less = Strong, up to {fm:.0%} = Fair, above = Pass.")
    if st=="ohio" and vl.startswith("sheriff"): why.append("Ohio law (ORC 2329.20) usually sets the first-sale minimum at 2/3 (67%) of the appraisal, so most first sales grade Fair.")
    if st=="new-jersey": why.append("NJ assessed values are not market values; each town's assessment ratio differs, so treat this as a rough guide. The lender can bid up to what it is owed, so the final price may differ.")
    tax=fact(e,"Last year's property tax") or fact(e,"Annual property tax")
    if tax: why.append(f"Yearly property tax on record: {usd(tax)} (source: {esrc}). Back taxes owed are not published here; check the county treasurer/tax collector.")
    else: why.append("Back taxes are not published on this list; check the county treasurer/tax collector.")
    p=i.get("times_postponed") or 0
    if p: why.append(f"Postponed {p} time(s) per the official status history.")
    if p>=DC["postponements_downgrade_at"] and g!="Pass":
        g={"Strong":"Fair","Fair":"Pass"}[g]; why.append(f"Grade lowered one step because of {p} postponements (sale may not happen).")
    why.append("Occupancy: not stated by the official source.")
    return g,why,info
def badge(g): return f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;color:#fff;background:{COLORS[g]};font-weight:700;font-size:16px;white-space:nowrap">{E(g)}</span>'
def summary(st,i,g,info,fdate):
    s=[f'This property is scheduled for sheriff sale on {fdate(i["sale_date"])}.']
    if info.get("r") is not None:
        s.append(f'The {info["pl"]} is {usd(info["price"])}, which is {info["r"]:.0%} of the {info["vl"]} of {usd(info["val"])}.')
    elif info["price"] and info["val"]: s.append(f'The published {info["pl"]} is {usd(info["price"])} and the {info["vl"]} is {usd(info["val"])}; see Deal Check below for why we did not grade it.')
    elif info["price"]: s.append(f'The {info["pl"]} is {usd(info["price"])}; no official value is matched yet.')
    else: s.append(f'The {info["pl"]} is not published yet.')
    s.append("Back taxes and whether anyone lives there are not stated by the official source.")
    return '<p style="font-size:21px;line-height:1.5">'+E(" ".join(s))+'</p>'
def deal_html(g,why):
    return (f'<div class="card" style="border-left:6px solid {COLORS[g]}"><h2 style="margin-top:0">Deal Check: {badge(g)}</h2>'
      '<b>Why</b><ul>'+"".join(f"<li>{E(w)}</li>" for w in why)+'</ul><p class="muted">Deal Check is a simple math check of published numbers, not an appraisal and not financial advice. '
      'It does not know the condition, liens, title problems, or back taxes. Inspect from the street, run a title/lien search, and verify everything with the county before you bid.</p></div>')
def ohio_deposit(i):
    a=i.get("appraised_value")
    if i.get("deposit"): return f'{usd(i["deposit"])} as published by the Sheriff.'
    if a: return f'{usd(2000 if a<=10000 else 5000 if a<=200000 else 10000)} for this appraisal under Ohio law (ORC 2329.211, residential: $2,000 / $5,000 / $10,000 by appraised value). Confirm with the Sheriff.'
    return 'Set by Ohio law (ORC 2329.211): $2,000, $5,000 or $10,000 depending on appraised value. Confirm with the Sheriff.'
def bid_html(st,i,cn,bid,fdate,inf):
    if st=="ohio":
        dep=ohio_deposit(i); steps=[f'Register free on the official {cn} County sale site ahead of time.','Have your deposit in place before the deadline (wire or ACH; see county rules).','Bid online on the sale day. If you win, the balance is usually due within about 30 days after the court confirms the sale.']
        link=f'<a href="{E(bid)}" rel="nofollow">{E(bid)}</a>'
    else:
        dep="20% of your winning bid, paid right when the sale ends, in cash or certified/cashier's check to the County Sheriff (N.J.S.A. 2A:50-64)."
        steps=["Check the official listing the day before, since NJ sales are often postponed.","Go to the sheriff sale in person at the time and place on the official notice; bring certified funds for the 20% deposit.","Balance is due later (usually within about 30 days); the owner can still redeem during the 10 days after the sale."]
        link=f'<a href="{E(i["source_url"])}" rel="nofollow">Official {cn} County Sheriff listing</a>'
    ex=("".join(f"<li>{E(x)}</li>" for x in (inf or {}).get("facts",[])[:2]))
    return (f'<div class="card" style="border:3px solid #f5b82e"><h2 style="margin-top:0">How to bid</h2><div class="kv"><div><b>Sale date</b></div><div>{fdate(i["sale_date"])}'
      +(' (time: see official notice)' )+f'</div><div><b>Where to bid</b></div><div>{link}</div><div><b>Deposit</b></div><div>{E(dep)}</div></div>'
      '<ol>'+"".join(f"<li>{E(s)}</li>" for s in steps)+'</ol>'+(f'<p class="muted">County rules:</p><ul class="muted">{ex}</ul>' if ex else "")+'</div>')
