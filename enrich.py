#!/usr/bin/env python3
"""Enrich sales with official public parcel data (county auditor / NJ MOD-IV). 2s rate limit; never invents values."""
import json, glob, os, re, time, datetime, urllib.parse, urllib.request
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, "data", "enrich")
UA = {"User-Agent": "DeedHoundBot/0.1 (public-records research; contact paulgravesjr@gmail.com)"}
NOW = datetime.datetime.now().astimezone().isoformat(timespec="minutes"); _last = [0.0]
def get(url, params):
    w = 2 - (time.time() - _last[0]); time.sleep(max(0, w)); _last[0] = time.time()
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=60))
def ms(v): return datetime.datetime.fromtimestamp(v / 1000).date().isoformat() if v else None
def key(i): return i.get("auction_id") or f'{i.get("county")}|{i["case_number"]}|{i["address"]}'
def num(v): return v if v not in (None, 0, "") else None
NJ = "https://services2.arcgis.com/XVOqAjTOJ5P6ngMu/arcgis/rest/services/Parcels_Composite_NJ_WM/FeatureServer/0"
NJ_PAGE = "https://njogis-newjersey.opendata.arcgis.com/datasets/newjersey::parcels-and-mod-iv-composite-of-nj-web-mercator-3857"
LOR = "https://services1.arcgis.com/vGBb7WYV10mOJRNM/arcgis/rest/services/OwnershipParcels_2025_Public_View/FeatureServer/1"
STK = "https://scgisa.starkcountyohio.gov/arcgis/rest/services/Auditor/StarkCountyParcels/FeatureServer/0"
AB = {"STREET": "ST", "AVENUE": "AVE", "ROAD": "RD", "DRIVE": "DR", "LANE": "LN", "COURT": "CT", "PLACE": "PL", "BOULEVARD": "BLVD", "TERRACE": "TER",
      "CIRCLE": "CIR", "PARKWAY": "PKWY", "HIGHWAY": "HWY", "AVE.": "AVE", "ST.": "ST", "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}
def variants(a):
    a = re.sub(r"\s+", " ", re.split(r",| UNIT | APT ", (a or "").upper())[0]).strip()
    if not re.match(r"^\d", a): return []
    short = " ".join(AB.get(t, t) for t in a.split())
    return list({a, short})
def nj_county(st_file, cache):
    d = json.load(open(st_file)); county = d["county"].replace("-", " ").upper(); items = d["items"]; want = {}
    for i in items:
        for v in variants(i["address"]): want.setdefault(v, []).append(i)
    keys = list(want); rows = []
    for n in range(0, len(keys), 40):
        inlist = ",".join("'" + k.replace("'", "''") + "'" for k in keys[n:n + 40])
        r = get(NJ + "/query", {"where": f"COUNTY='{county}' AND PROP_LOC IN ({inlist})", "outFields": "PROP_LOC,MUN_NAME,PCLBLOCK,PCLLOT,PROP_CLASS,LAND_VAL,IMPRVT_VAL,NET_VALUE,LAST_YR_TX,BLDG_DESC,CALC_ACRE,YR_CONSTR,PCLLASTUPD,PAMS_PIN", "returnGeometry": "false", "f": "json"})
        rows += [f["attributes"] for f in r.get("features", [])]
    hit = 0
    for i in items:
        c = [r for r in rows if r["PROP_LOC"] in variants(i["address"])]
        city = (i["city"] or "").upper().split()
        if len({r["MUN_NAME"] for r in c}) > 1: c = [r for r in c if city and city[0] in r["MUN_NAME"]]
        if len({r["PAMS_PIN"] for r in c}) != 1: continue
        r = c[0]; hit += 1
        cache[key(i)] = {"source": "NJ MOD-IV tax list via NJ Office of GIS parcel composite (NJOGIS / NJ Division of Taxation)", "source_url": NJ_PAGE, "retrieved": NOW,
            "data_date": ms(r["PCLLASTUPD"]), "photo": None, "photo_note": None, "parcel": f'Block {r["PCLBLOCK"]}, Lot {r["PCLLOT"]} ({r["MUN_NAME"].title()})',
            "facts": [x for x in [("Year built", num(r["YR_CONSTR"])), ("Building description (assessor code)", (r["BLDG_DESC"] or "").strip() or None),
                ("Lot size", f'{r["CALC_ACRE"]:.2f} acres' if r["CALC_ACRE"] else None), ("Property class", r["PROP_CLASS"]),
                ("Assessed land value", r["LAND_VAL"], "usd"), ("Assessed improvement value", r["IMPRVT_VAL"], "usd"), ("Net assessed value", r["NET_VALUE"], "usd"),
                ("Last year's property tax", r["LAST_YR_TX"], "usd")] if x[1] not in (None, 0, "")],
            "note": "NJ assessed values can differ from market value (each town has its own assessment ratio)."}
    return d["county"], len(items), hit
def lorain(items, cache):
    hit = 0
    for i in items:
        pid = re.sub(r"\D", "", i.get("parcel_id") or "")
        if not pid: continue
        f = get(LOR + "/query", {"where": f"PARCELID='{pid}'", "outFields": "PARCELID,SITEADDRESS,RESFLRAREA,BLDGAREA,RESYRBLT,BEDROOMS,BATHS,HALFBATHS,MARKETLAND,MARKETBUILDING,MARKETTOTAL,TAXANNUALREALCREDIT,TAXUNPAID,TAXDELINQSPECASSESS,TAXCURRENTSPECASSESS,USEDSCRP,ACRES,IMAGE_URL", "returnGeometry": "false", "f": "json"}).get("features", [])
        if len(f) != 1: continue
        r = f[0]["attributes"]; hit += 1
        cache[key(i)] = {"source": "Lorain County Auditor (official county GIS parcel layer)", "source_url": LOR, "retrieved": NOW, "data_date": None, "photo": (r["IMAGE_URL"] if r["IMAGE_URL"] and "blocked" not in r["IMAGE_URL"] else None), "photo_note": "Photo: Lorain County Auditor", "parcel": r["PARCELID"],
            "facts": [x for x in [("Use", (r["USEDSCRP"] or "").strip().title() or None), ("Living area", f'{r["RESFLRAREA"]:,} sq ft' if r["RESFLRAREA"] else (f'{r["BLDGAREA"]:,} sq ft' if r["BLDGAREA"] else None)),
                ("Year built", num(r["RESYRBLT"])), ("Bedrooms", num(r["BEDROOMS"])), ("Bathrooms", (f'{r["BATHS"]} full' + (f', {r["HALFBATHS"]} half' if r["HALFBATHS"] else "")) if r["BATHS"] else None),
                ("Lot size", f'{r["ACRES"]:.2f} acres' if r["ACRES"] else None), ("Auditor market value – land", r["MARKETLAND"], "usd"), ("Auditor market value – building", r["MARKETBUILDING"], "usd"),
                ("Auditor market value – total", r["MARKETTOTAL"], "usd"), ("Annual property tax (after credits)", r["TAXANNUALREALCREDIT"], "usd"), ("Past-due taxes on county record", r["TAXUNPAID"], "usd"), ("Past-due special assessments on county record", r["TAXDELINQSPECASSESS"], "usd"), ("Current special assessments on county record", r["TAXCURRENTSPECASSESS"], "usd")] if x[1] not in (None, 0, "")], "note": None}
    return hit
def stark(items, cache):
    hit = 0
    for i in items:
        pid = re.sub(r"\D", "", i.get("parcel_id") or "").lstrip("0")
        if not pid: continue
        f = get(STK + "/query", {"where": f"PIN='{pid}'", "outFields": "PIN,TAXYR,LAND_USE_DESCRIPTION,ACRES,APPRAISED_LAND_VALUE,APPRAISED_BUILDING_VALUE,APPRAISED_TOTAL_VALUE,TOTAL_BILLED,UpdatedDate", "returnGeometry": "false", "f": "json"}).get("features", [])
        if len(f) != 1: continue
        r = f[0]["attributes"]; hit += 1
        cache[key(i)] = {"source": "Stark County Auditor (official county GIS parcel layer)", "source_url": STK, "retrieved": NOW, "data_date": ms(r["UpdatedDate"]),
            "photo": None, "photo_note": None, "parcel": r["PIN"],
            "facts": [x for x in [("Use", (r["LAND_USE_DESCRIPTION"] or "").strip().title() or None), ("Lot size", f'{r["ACRES"]:.2f} acres' if r["ACRES"] else None), ("Tax year", r["TAXYR"]),
                ("Auditor appraised land", r["APPRAISED_LAND_VALUE"], "usd"), ("Auditor appraised building", r["APPRAISED_BUILDING_VALUE"], "usd"),
                ("Auditor appraised total", r["APPRAISED_TOTAL_VALUE"], "usd"), ("Tax billed on county record (may include past-due amounts)", r["TOTAL_BILLED"], "usd")] if x[1] not in (None, 0, "")], "note": None}
    return hit
PHL = "https://phl.carto.com/api/v2/sql"
PHL_PAGE = "https://opendataphilly.org/datasets/philadelphia-properties-and-assessment-history/"
MONT = "https://mapservices.pasda.psu.edu/server/rest/services/pasda/MontgomeryCounty/MapServer/14"
MONT_PAGE = "https://www.pasda.psu.edu/ (Montgomery County, PA parcels, Dec 2025 release from the county)"
def philadelphia(items, cache):
    """City of Philadelphia Office of Property Assessment (OPA) data via the City's open-data Carto API, matched on the OPA # the Sheriff publishes."""
    ids = sorted({re.sub(r"\D", "", i.get("parcel_id") or "") for i in items} - {""}); rows = {}
    for n in range(0, len(ids), 100):
        q = ("SELECT parcel_number,location,market_value,taxable_land,taxable_building,exempt_land,exempt_building,assessment_date,year_built,total_livable_area,"
             "number_of_bedrooms,number_of_bathrooms,category_code_description,building_code_description FROM opa_properties_public WHERE parcel_number IN (" + ",".join(f"'{x}'" for x in ids[n:n + 100]) + ")")
        for r in get(PHL, {"q": q}).get("rows", []): rows.setdefault(r["parcel_number"], []).append(r)
    hit = 0
    for i in items:
        c = rows.get(re.sub(r"\D", "", i.get("parcel_id") or ""), [])
        if len(c) != 1: continue
        r = c[0]; hit += 1
        cache[key(i)] = {"source": "City of Philadelphia Office of Property Assessment (OPA), via the City's open-data API", "source_url": PHL_PAGE, "retrieved": NOW,
            "data_date": (r["assessment_date"] or "")[:10] or None, "photo": None, "photo_note": None, "parcel": f'OPA # {r["parcel_number"]} ({r["location"]})',
            "facts": [x for x in [("Use", (r["category_code_description"] or "").strip().title() or None), ("Building type (OPA code)", (r["building_code_description"] or "").strip().title() or None),
                ("Living area", f'{r["total_livable_area"]:,.0f} sq ft' if r["total_livable_area"] else None), ("Year built", num(r["year_built"]) if r["year_built"] not in ("0", "0000") else None),
                ("Bedrooms", num(r["number_of_bedrooms"])), ("Bathrooms", num(r["number_of_bathrooms"])),
                ("OPA taxable land", r["taxable_land"], "usd"), ("OPA taxable building", r["taxable_building"], "usd"), ("OPA market value", r["market_value"], "usd")] if x[1] not in (None, 0, "")],
            "note": "Philadelphia OPA market values are the City's mass-appraisal estimates, not a sale price or inspection."}
    return hit
def montgomery_pa(items, cache):
    """Montgomery County, PA Board of Assessment Appeals data, as published to PASDA (Pennsylvania Spatial Data Access, the Commonwealth's open GIS clearinghouse)."""
    hit = 0
    for i in items:
        pins = [re.sub(r"\D", "", p) for p in re.split(r"&|,| and ", i.get("parcel_id") or "")]; pins = [p for p in pins if len(p) == 12]
        if len(pins) != 1: continue  # several parcels sold together: we do not add them up
        f = get(MONT + "/query", {"where": f"PARCEL='{pins[0]}'", "outFields": "PARCEL,LOCATION1,ASSESSMENT,ASMT_CHGDA,YEAR_BUILT,SFLA,LAND_ACRES,EST_CO_TAX,EST_MUNI_T,EST_SCH_TA,Muni_Name", "returnGeometry": "false", "f": "json"}).get("features", [])
        if len(f) != 1: continue
        r = f[0]["attributes"]; hit += 1
        tax = sum(r[k] or 0 for k in ("EST_CO_TAX", "EST_MUNI_T", "EST_SCH_TA")) or None
        cache[key(i)] = {"source": "Montgomery County, PA assessment records (Dec 2025 parcel release on PASDA, the Commonwealth's open GIS clearinghouse)", "source_url": MONT, "retrieved": NOW,
            "data_date": "2025-12", "photo": None, "photo_note": None, "parcel": f'{r["PARCEL"]} ({(r["LOCATION1"] or "").strip()})',
            "facts": [x for x in [("Living area", f'{r["SFLA"]:,} sq ft' if r["SFLA"] else None), ("Year built", num(r["YEAR_BUILT"])), ("Lot size", f'{r["LAND_ACRES"]:.2f} acres' if r["LAND_ACRES"] else None),
                ("Assessment last changed", (r["ASMT_CHGDA"] or "").strip() or None), ("County assessed value", r["ASSESSMENT"], "usd"), ("Estimated yearly property tax (county + town + school)", tax, "usd")] if x[1] not in (None, 0, "")],
            "note": "Montgomery County assesses at 1996 base-year values, so assessed values are usually well below today's market value."}
    return hit
if __name__ == "__main__" and os.environ.get("ENRICH_ONLY") == "pa":
    P = os.path.join(OUT, "enrich.json"); cache = json.load(open(P)) if os.path.exists(P) else {}; rep = []
    for name, fn in (("philadelphia", philadelphia), ("montgomery", montgomery_pa)):
        fp = os.path.join(ROOT, f"data/pennsylvania/{name}.json")
        if not os.path.exists(fp): continue
        its = json.load(open(fp))["items"]; rep.append(("PA", name, len(its), fn(its, cache))); print(rep[-1], flush=True)
    json.dump(cache, open(P, "w"), indent=1); json.dump(rep, open(os.path.join(OUT, "report_pa.json"), "w")); raise SystemExit
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); cache = {}; report = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data/new-jersey/*.json"))):
        try: report.append(("NJ",) + nj_county(f, cache))
        except Exception as e: report.append(("NJ", f, 0, f"error {e}"))
        print(report[-1], flush=True)
    for name, fn in (("lorain", lorain), ("stark", stark)):
        its = json.load(open(os.path.join(ROOT, f"data/ohio/{name}.json")))["items"]; report.append(("OH", name, len(its), fn(its, cache))); print(report[-1], flush=True)
    for name, fn in (("philadelphia", philadelphia), ("montgomery", montgomery_pa)):
        fp = os.path.join(ROOT, f"data/pennsylvania/{name}.json")
        if os.path.exists(fp):
            try: its = json.load(open(fp))["items"]; report.append(("PA", name, len(its), fn(its, cache)))
            except Exception as e: report.append(("PA", name, 0, f"error {e}"))
            print(report[-1], flush=True)
    json.dump(cache, open(os.path.join(OUT, "enrich.json"), "w"), indent=1); json.dump(report, open(os.path.join(OUT, "report.json"), "w"))
    print(len(cache), "enriched")
