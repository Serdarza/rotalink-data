#!/usr/bin/env python3
"""Conservatively add only MEB teacherhouses that have a verifiable OSM POI.
The MEB directory supplies city, district and phone, not a street address.
Do not guess addresses or coordinates; skip unmatched/ambiguous POIs.
"""
import json,re,time,requests,unicodedata
from pathlib import Path

DB=Path("master_database_updated.json")
REPORT=Path("scripts/reports/meb_ogretmenevi_20261027.json")
GEO_REPORT=Path("scripts/reports/meb_teacherhouse_geocoding_20261027.json")
SKIP={11,12,17,23,31,41,51,120,154,182,226,243,251,262,282,304,311,328,329,332,333,334,335,339,353,354,375,390,421,464,513}
TRANS=str.maketrans({"ı":"i","İ":"i","ş":"s","Ş":"s","ğ":"g","Ğ":"g","ü":"u","Ü":"u","ö":"o","Ö":"o","ç":"c","Ç":"c"})
def norm(s):
    s=str(s or "").translate(TRANS).lower()
    s="".join(x for x in unicodedata.normalize("NFD",s) if unicodedata.category(x)!="Mn")
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()
def actual_city(city):
    if norm(city)=="k maras":return "Kahramanmaraş"
    return city
def is_teacher(t):
    return "ogretmen" in norm(t.get("isim","")) or norm(t.get("tip",""))=="ogretmenevi"
def existing_in_district(src,facilities):
    district=norm(src["ilce"])
    city=norm(actual_city(src["il"]))
    for f in facilities:
        if norm(f.get("il"))!=city or not is_teacher(f):continue
        name=norm(f.get("isim"))
        addr=norm(f.get("adres"))
        if district in ("merkez","buyuksehir"):
            # Do not create a possibly duplicated central institution.
            if (city in name or "merkez" in name or norm(src["isim"]).split(" ")[0] in name.split()):
                return True
        elif district in name.split() or district in addr.split():
            return True
    return False
def strict_geocode(src):
    city=actual_city(src["il"]); district=src["ilce"]
    src_label=src["isim"].replace("ve Akşam Sanat Okulu","").replace("ve Akşam Akşam Sanat Okulu","").strip()
    if norm(src_label) in ("ogretmenevi","ogretmen evi"):
        src_label=district+" Öğretmenevi"
    names=[src_label+","+district+","+city+",Türkiye",
           district+" Öğretmenevi,"+city+",Türkiye"]
    session=requests.Session()
    session.headers.update({"User-Agent":"RotalinkPublicFacilityAudit/1.0 (rotalink.tr; public nonprofit directory audit)"})
    for q in names:
        time.sleep(1.3)
        try:
            response=session.get("https://nominatim.openstreetmap.org/search",
                params={"q":q,"format":"jsonv2","addressdetails":1,"namedetails":1,"limit":5},
                timeout=15)
            if response.status_code!=200:continue
            results=response.json()
        except Exception as e:
            print("geocoding error:",type(e).__name__,str(e)[:70],flush=True)
            continue
        for d in results:
            label=norm(d.get("name","") or d.get("namedetails",{}).get("name",""))
            if "ogretmen" not in label:continue
            display=norm(d.get("display_name",""))
            if norm(city) not in display:continue
            if norm(district) not in ("merkez","buyuksehir") and norm(district) not in display:continue
            adr=d.get("address",{})
            road=adr.get("road") or adr.get("pedestrian") or adr.get("residential")
            if not road:continue
            kind=norm(str(d.get("type",""))+" "+str(d.get("category","")))
            if not any(x in kind for x in ["hotel","hostel","guest","tourism","amenity","building","government","community"]):
                continue
            pieces=[adr.get("neighbourhood") or adr.get("suburb"),road,adr.get("house_number"),district,city]
            address=", ".join(str(x) for x in pieces if x)
            return {"adres":address,"latitude":float(d["lat"]),"longitude":float(d["lon"]),"osm_id":d.get("osm_id"),"osm_type":d.get("osm_type"),"poi_name":d.get("name"),"query":q}
    return None
def main():
    db=json.loads(DB.read_text(encoding="utf-8")); fac=db["tesisler"]
    before=json.loads(DB.read_text(encoding="utf-8"))["tesisler"]
    src=json.loads(REPORT.read_text(encoding="utf-8"))
    new=[]; skipped=[]; looked=0
    for row in src["unmatched"]:
        if row["sira"] in SKIP:
            continue
        if existing_in_district(row,fac):
            skipped.append({"source":row,"reason":"existing possible institution in same district/city"})
            continue
        looked+=1
        geo=strict_geocode(row)
        if not geo:
            skipped.append({"source":row,"reason":"street-level coordinate and named POI not independently verified"})
            continue
        city=actual_city(row["il"])
        name=row["isim"].replace(" ve Akşam Sanat Okulu","").strip()
        if norm(name) in ("ogretmenevi","ogretmen evi"):
            name=row["ilce"]+" Öğretmenevi"
        if any(norm(x.get("isim"))==norm(name) and norm(x.get("il"))==norm(city) for x in fac):
            skipped.append({"source":row,"reason":"same normalized facility already exists"})
            continue
        item={"isim":name,"tip":"Öğretmenevi","il":city,"adres":geo["adres"],"telefon":row["telefon"],
            "latitude":geo["latitude"],"longitude":geo["longitude"]}
        fac.append(item)
        new.append({"source":row,"facility":item,"verification":geo})
    assert fac[:len(before)]==before,"existing data modified"
    GEO_REPORT.parent.mkdir(parents=True,exist_ok=True)
    GEO_REPORT.write_text(json.dumps({"looked_up":looked,"added_count":len(new),"added":new,"skipped":skipped},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if new:DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"looked_up":looked,"added_count":len(new),"added":new,"skipped_count":len(skipped)},ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
