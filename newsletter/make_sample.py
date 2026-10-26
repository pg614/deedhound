"""Build a SAMPLE weekly digest (static files only; nothing is sent). Run after build.py."""
import json,datetime,html,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A=json.load(open(os.path.join(R,'site_items.json')));t=datetime.date.today();end=(t+datetime.timedelta(14)).isoformat()
G=["camden","gloucester","burlington"]
it=sorted([i for i in A if i["county"] in G and t.isoformat()<=i["sale_date"]<=end],key=lambda i:({"Strong":0,"Fair":1,"Pass":2}.get(i["grade"],3),i["sale_date"]))
B="https://pg614.github.io/deedhound"; C={"Strong":"#1b7f3b","Fair":"#b7791f","Pass":"#b42318","Not enough data":"#5b6475"}
def u(v): return f"${v:,.0f}" if v else "not published"
def dt(s): return datetime.date.fromisoformat(s).strftime("%a %b %-d")
td='style="padding:10px;border-bottom:1px solid #ddd"'
rows="".join(f'<tr><td {td}><span style="background:{C[i["grade"]]};color:#fff;padding:2px 8px;border-radius:10px;font-weight:700">{i["grade"]}</span></td><td {td}><a href="{B}{i["url"]}">{html.escape(i["address"] or "")}</a>, {html.escape(i["city"] or "")}<br><small>{i["county_name"]} County</small></td><td {td}>{dt(i["sale_date"])}</td><td {td}>{u(i.get("upset_amount"))}</td></tr>' for i in it[:25])
n={g:sum(i["grade"]==g for i in it) for g in C}
h=f'''<!doctype html><html><body style="margin:0;background:#f6f7f9;font:19px/1.5 Arial,sans-serif;color:#1d2433"><div style="max-width:680px;margin:0 auto;background:#fff;padding:24px">
<p style="color:#b42318;font-weight:700">SAMPLE ONLY · not sent · data as of {t:%b %-d, %Y}</p><h1 style="color:#1f3a5f">DeedHound weekly: South Jersey sheriff sales</h1>
<p>{len(it)} sales in Camden, Gloucester and Burlington counties over the next 2 weeks ({t:%b %-d}–{datetime.date.fromisoformat(end):%b %-d}). Deal Check: {n["Strong"]} Strong, {n["Fair"]} Fair, {n["Pass"]} Pass, {n["Not enough data"]} not enough data. Showing the first 25, best grades first.</p>
<table style="width:100%;border-collapse:collapse;font-size:17px"><tr style="background:#1f3a5f;color:#fff"><th style="padding:10px;text-align:left">Deal Check</th><th style="padding:10px;text-align:left">Property</th><th style="padding:10px;text-align:left">Sale</th><th style="padding:10px;text-align:left">Approx. owed to lender*</th></tr>{rows}</table>
<p style="font-size:15px;color:#5b6475">*Approx. judgment/upset amount as published by the County Sheriff; the opening bid is announced at the sale. Deal Check compares it with the town's assessed value (NJ assessment ratios vary). NJ winners pay a 20% deposit at the sale (N.J.S.A. 2A:50-64). Sales are often postponed. Not financial advice: inspect, run a title/lien search, and verify with the Sheriff before bidding.</p></div></body></html>'''
o=os.path.join(R,'newsletter','sample');os.makedirs(o,exist_ok=True)
open(os.path.join(o,'weekly.html'),'w').write(h)
txt=f"SAMPLE ONLY - not sent - data as of {t:%b %-d, %Y}\nDeedHound weekly: South Jersey sheriff sales\n{len(it)} sales next 2 weeks. Strong {n['Strong']}, Fair {n['Fair']}, Pass {n['Pass']}, Not enough data {n['Not enough data']}.\n\n"+"\n".join(f"[{i['grade']}] {i['address']}, {i['city']} ({i['county_name']}) - sale {dt(i['sale_date'])} - approx. owed {u(i.get('upset_amount'))}\n  {B}{i['url']}" for i in it[:25])+"\n\nApprox. judgment/upset as published by the Sheriff. NJ deposit 20% at sale (N.J.S.A. 2A:50-64). Not financial advice; verify with the Sheriff.\n"
open(os.path.join(o,'weekly.txt'),'w').write(txt);print(len(it),n)
