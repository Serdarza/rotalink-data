#!/usr/bin/env python3
"""Compare official MEB teacherhouse telephone list with Rotalink facilities.
Existing fields are immutable: only append a verified telefon2 to exact matches.
Ambiguous/unmatched facilities are exported for later manual research.
"""
import json, re, unicodedata, difflib, requests
from pathlib import Path
from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime, timezone

SOURCE = "https://dhgm.meb.gov.tr/edestek/ogretmenevi/ogretmenevi_liste.aspx"
DB = Path("master_database_updated.json")
REPORT = Path("scripts/reports/meb_ogretmenevi_20261027.json")
TRANSLATE = str.maketrans({"ı":"i","İ":"i","ş":"s","Ş":"s","ğ":"g","Ğ":"g","ü":"u","Ü":"u","ö":"o","Ö":"o","ç":"c","Ç":"c"})
REMOVE = set("ve aksam sanat okulu mudurlugu ogretmenevi ogretmen evi aso".split())
def norm(x):
    x = str(x or "").translate(TRANSLATE).lower()
    x = "".join(y for y in unicodedata.normalize("NFD", x) if unicodedata.category(y) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", x))
def basic_name(name, city):
    words = [w for w in norm(name).split() if w not in REMOVE]
    if words and words[0] == norm(city): words.pop(0)
    return " ".join(words)
def phones(p):
    result=set()
    for v in re.split(r"\s*(?:/|;|\||\bve\b)\s*",str(p or "")):
        v=re.sub(r"\D","",v)
        if v.startswith("0090"): v="0"+v[4:]
        if v.startswith("90") and len(v)==12: v="0"+v[2:]
        if len(v)==10: v="0"+v
        if len(v)==11: result.add(v)
    return result
def source_data():
    # The MEB endpoint has an incomplete HTTPS certificate chain on GitHub-hosted runners.
    # Restrict this exceptional unverified request to the fixed official HTTPS host.
    res=requests.get(SOURCE,headers={"User-Agent":"Mozilla/5.0","Accept-Language":"tr-TR,tr;q=0.9"},timeout=80,verify=False)
    res.raise_for_status()
    res.encoding=res.apparent_encoding or "utf-8"
    soup=BeautifulSoup(res.text,"html.parser")
    rows=[]
    for tr in soup.select("tr"):
        vals=[c.get_text(" ",strip=True).replace("\u00a0"," ").strip() for c in tr.find_all(["td","th"],recursive=False)]
        if len(vals)<5 or not re.fullmatch(r"\d+",vals[0]): continue
        number,city,district,name,phone=vals[:5]
        if "ogretmen" not in norm(name) or len(phones(phone))!=1: continue
        rows.append({"sira":int(number),"il":city,"ilce":district,"isim":name,"telefon":phone,"key":next(iter(phones(phone)))})
    rows=list({r["sira"]:r for r in rows}.values())
    print("MEB record count",len(rows),"examples",rows[:3],flush=True)
    if len(rows)<300: raise RuntimeError("MEB table could not be parsed in full. Database not modified.")
    return rows
def main():
    original=DB.read_text(encoding="utf-8")
    db=json.loads(original)
    before=db["tesisler"]
    by_city=defaultdict(list)
    for i,f in enumerate(before):
        if "ogretmen" in norm(f.get("isim")) or "ogretmen" in norm(f.get("tip")):
            by_city[norm(f.get("il"))].append(i)
    equal=[]; additions=[]; ambiguous=[]; unmatched=[]; full=[]; assigned=set()
    for src in source_data():
        opts=[]
        for i in by_city[norm(src["il"])]:
            f=before[i]; a=basic_name(src["isim"],src["il"]); b=basic_name(f["isim"],src["il"])
            has_phone=src["key"] in (phones(f.get("telefon"))|phones(f.get("telefon2")))
            ratio=difflib.SequenceMatcher(None,a,b).ratio() if a and b else 0.0
            exact=a==b and bool(a)
            district=norm(src["ilce"])
            locality=norm(f.get("isim","")+" "+f.get("ilce","")+" "+f.get("adres",""))
            district_match=district not in ("merkez","buyuksehir","") and district in locality.split()
            score=(140 if has_phone else 0)+(85 if exact else 0)+(40 if ratio>.92 else 18 if ratio>.80 else 0)+(25 if district_match else 0)
            opts.append((score,i,has_phone,exact,ratio,district_match))
        opts.sort(reverse=True)
        top=opts[0] if opts else None
        second=opts[1][0] if len(opts)>1 else -1000
        if top is None or top[0]<30:
            unmatched.append(src);continue
        score,i,has_phone,exact,ratio,dmatch=top
        confident=(has_phone and score-second>=20) or (exact and score-second>=25) or (ratio>.85 and dmatch and score-second>=35 and score>=65)
        if not confident or i in assigned:
            ambiguous.append({"source":src,"candidates":[{"name":before[z]["isim"],"score":s} for s,z,*_ in opts[:3]]})
            continue
        assigned.add(i)
        f=before[i]; full.append((src["sira"],f["isim"]))
        if has_phone:
            equal.append({"source":src["isim"],"db":f["isim"]})
        elif f.get("telefon2","").strip() or len(phones(f.get("telefon")))>1:
            ambiguous.append({"source":src,"db":f["isim"],"reason":"Two phone slots already occupied"})
        else:
            f["telefon2"]=src["telefon"].strip()
            additions.append({"il":src["il"],"source":src["isim"],"db":f["isim"],"telefon":f.get("telefon"),"telefon2":f["telefon2"]})
    report={"source":SOURCE,"timestamp":datetime.now(timezone.utc).isoformat(),"official_count":len(equal)+len(additions)+len(ambiguous)+len(unmatched),
            "database_count":len(before),"counts":{"same_phone":len(equal),"second_added":len(additions),"ambiguous":len(ambiguous),"unmatched":len(unmatched)},
            "second_added":additions,"ambiguous":ambiguous,"unmatched":unmatched}
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    prev=json.loads(original)["tesisler"]
    assert len(prev)==len(before)
    for i,(a,b) in enumerate(zip(prev,before)):
        if a!=b:
            assert not a.get("telefon2") and dict(b,telefon2=None)==dict(a,telefon2=None),(i,a.get("isim"))
    if additions:
        DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"counts":report["counts"],"matched_examples":additions[:15],"ambiguous_examples":ambiguous[:8],"missing_examples":unmatched[:12]},ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
