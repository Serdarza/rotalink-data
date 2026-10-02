"""Tesis il/ilçe denetimi: koordinat poligonu + adres metni + mevcut overlay."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

HERE = Path(__file__).parent
DATA = HERE.parent.parent
CACHE = HERE / ".cache"
GB_URL = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/TUR/{lvl}/geoBoundaries-TUR-{lvl}.geojson"


def _boundaries(lvl):
    """geoBoundaries (OSM, ODbL) sabit sürüm; ilk çalıştırmada indirilir."""
    path = CACHE / f"{lvl.lower()}.geojson"
    if not path.exists():
        import urllib.request
        CACHE.mkdir(exist_ok=True)
        urllib.request.urlretrieve(GB_URL.format(lvl=lvl), path)
    return json.load(open(path, encoding="utf-8"))["features"]


OSM_FIX = {
    "Ardahan": "Merkez",
    "Giresun District": "Merkez",
    "Prince Islands": "Adalar",
    "Imbros": "Gökçeada",
    "Karakeçeli": "Karakeçili",
    "Gediz Merkez": "Gediz",
    "İbradi": "İbradı",
    "Ayvacik": "Ayvacık",
    "Ilıç": "İliç",
    "Ulukisla": "Ulukışla",
    "Şarkîkaraağaç": "Şarkikaraağaç",
}
IL_FIX = {"Hakkâri": "Hakkari"}
KKTC = ["Lefkoşa", "Gazimağusa", "Girne", "Güzelyurt", "İskele", "Lefke"]
KKTC_ALIAS = {"magosa": "Gazimağusa", "famagusta": "Gazimağusa", "kyrenia": "Girne", "nicosia": "Lefkoşa",
              "morphou": "Güzelyurt", "trikomo": "İskele", "lapta": "Girne", "alsancak": "Girne",
              "dipkarpaz": "İskele", "gonyeli": "Lefkoşa", "gönyeli": "Lefkoşa"}


def norm(s):
    t = s or ""
    for a, b in (("ç", "c"), ("Ç", "c"), ("ğ", "g"), ("Ğ", "g"), ("ı", "i"), ("İ", "i"), ("I", "i"),
                 ("ö", "o"), ("Ö", "o"), ("ş", "s"), ("Ş", "s"), ("ü", "u"), ("Ü", "u"), ("â", "a"),
                 ("Â", "a"), ("î", "i"), ("û", "u")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", t.lower())


def clean_osm(name):
    if name in OSM_FIX:
        return OSM_FIX[name]
    if re.search(r"merkez", name, re.I) and name != "Merkezefendi":
        return "Merkez"
    return name


# ---- referans ----
adm1 = _boundaries("ADM1")
adm2 = _boundaries("ADM2")
il_geoms = [(IL_FIX.get(f["properties"]["shapeName"], f["properties"]["shapeName"]), shape(f["geometry"])) for f in adm1]
districts = []  # (il, ilce, geom)
for f in adm2:
    g = shape(f["geometry"])
    p = g.representative_point()
    il = next(n for n, s in il_geoms if s.contains(p))
    districts.append((il, clean_osm(f["properties"]["shapeName"]), g))
tree = STRtree([d[2] for d in districts])
REF = defaultdict(list)
for il, ilce, _ in districts:
    REF[il].append(ilce)
REF["Kıbrıs"] = KKTC[:]
REF_N = {il: {norm(x): x for x in v} for il, v in REF.items()}
IL_N = {norm(il): il for il in REF}
METRO = {il for il, v in REF.items() if "Merkez" not in v and il != "Kıbrıs"}


def poly_lookup(lat, lon):
    if not lat or not lon:
        return None
    pt = Point(lon, lat)
    for i in tree.query(pt):
        if districts[i][2].contains(pt):
            return districts[i][0], districts[i][1]
    return None


def dist_km(lat, lon, il, ilce):
    pt = Point(lon, lat)
    best = None
    for dil, dn, g in districts:
        if dil == il and dn == ilce:
            d = g.distance(pt) * 111
            best = d if best is None else min(best, d)
    return best


def address_districts(adres, il):
    """Adresteki ilçe adayları; 'İlçe/İL' kalıbı önceliklidir."""
    if not isinstance(adres, str) or not adres or il not in REF_N:
        return []
    ref = REF_N[il]
    found = []
    il_names = {norm(il)} | ({"kktc", "kibris"} if il == "Kıbrıs" else set())
    # "İlçe/İL", "İlçe - İL", "İlçe, İL" kalıpları
    for m in re.finditer(r"([A-Za-zÇĞİIÖŞÜçğıöşüâîû0-9\.\- ]{2,60}?)\s*[/\-–—,]\s*([A-Za-zÇĞİIÖŞÜçğıöşüâîû]+)\s*(?=$|[\s,.;)(—–\-])", adres):
        left, right = m.group(1).strip(), m.group(2).strip()
        if norm(right) not in il_names:
            continue
        words = [w for w in re.split(r"[\s\-,.]+", left) if w]
        for k in range(min(3, len(words)), 0, -1):
            cand = " ".join(words[-k:])
            n = norm(cand)
            if n in ref:
                found.append(("slash", ref[n]))
                break
            if n == norm(il) or n == norm(il) + "merkez" or n == "merkez":
                if "merkez" in ref:
                    found.append(("slash", "Merkez"))
                    break
    # serbest metin: kelime sınırında ilçe adı
    toks = re.findall(r"[A-Za-zÇĞİIÖŞÜçğıöşüâîû0-9]+", adres)
    ntoks = [norm(t) for t in toks]
    for i in range(len(ntoks)):
        for k in (3, 2, 1):
            if i + k > len(ntoks):
                continue
            n = "".join(ntoks[i:i + k])
            if n in ref and ref[n] != "Merkez":
                # "X Mahallesi/Caddesi/Sokak" ise ilçe değil sokak adı olabilir
                nxt = ntoks[i + k] if i + k < len(ntoks) else ""
                if nxt.startswith(("mah", "cad", "cd", "sok", "sk", "bul", "blv", "kosk")):
                    continue
                found.append(("text", ref[n]))
    if il == "Kıbrıs":
        for t in ntoks:
            if t in KKTC_ALIAS:
                found.append(("text", KKTC_ALIAS[t]))
    return found


def overlay_norm(ilce, il):
    if not ilce:
        return None
    n = norm(ilce)
    ref = REF_N.get(il, {})
    if n in ref:
        return ref[n]
    if n in (norm(il), norm(il) + "merkez", "merkez") and "merkez" in ref:
        return "Merkez"
    return None


def main():
    master = json.load(open(DATA / "master_database_updated.json", encoding="utf-8"))
    tes = master["tesisler"]
    adres_ov = json.load(open(DATA / "tesisler_adres.json", encoding="utf-8"))["items"]
    ov = {(norm(r["il"]), norm(r["isim"])): r for r in adres_ov}

    coord_count = Counter((round(r["latitude"], 5), round(r["longitude"], 5)) for r in tes)
    addr_names = defaultdict(set)
    for r in tes:
        if isinstance(r["adres"], str) and len(re.findall(r"\w+", r["adres"])) > 3:
            addr_names[norm(r["adres"])].add(norm(r["isim"]))
    shared_addr = {a for a, names in addr_names.items() if len(names) > 1}

    out = []
    for idx, r in enumerate(tes):
        il_raw = r["il"]
        il = IL_N.get(norm(il_raw))
        rec = {"idx": idx, "isim": r["isim"], "il": il_raw, "tip": r["tip"]}
        if il is None:
            rec.update(karar="belirsiz", neden="il referansta yok")
            out.append(rec)
            continue
        if il != il_raw:
            rec["il_std"] = il
        o = ov.get((norm(il_raw), norm(r["isim"])))
        adr_ov = o["adres"] if o else ""
        lat, lon = r.get("latitude") or 0, r.get("longitude") or 0
        poly = poly_lookup(lat, lon)
        shared = coord_count[(round(lat, 5), round(lon, 5))] > 1

        def pick(cands):
            slash = sorted({c for s, c in cands if s == "slash"})
            text = sorted({c for s, c in cands if s == "text"})
            if len(slash) == 1:
                return slash[0], False
            if slash:
                return None, True
            if len(text) == 1:
                return text[0], False
            return None, len(text) > 1

        addr_shared = isinstance(r["adres"], str) and norm(r["adres"]) in shared_addr
        addr_sh, _ = pick(address_districts(r["adres"], il))
        addr, addr_conflict = (None, False) if addr_shared else pick(address_districts(r["adres"], il))
        addr_src = "adres"
        rec["ortak_adres"] = addr_shared
        if addr is None and not addr_conflict:
            addr, _ = pick(address_districts(adr_ov, il))
            addr_src = "eşlenik adres"
        name_hits = sorted({c for s, c in address_districts(r["isim"], il) if s == "text"})
        name = name_hits[0] if len(name_hits) == 1 else None
        ovl = overlay_norm(o["ilce"], il) if o else None
        rec.update(adres=r["adres"], adres_ov=adr_ov, ov_ilce=o["ilce"] if o else None, mevcut=r.get("ilce"),
                   poly=poly, shared=shared, addr=addr, addr_src=addr_src, name=name, ovl=ovl)

        poly_il, poly_ilce = (poly or (None, None))
        poly_in_il = poly is not None and poly_il == il
        poly_ok = poly_in_il and not shared

        karar, kaynak, uyari = None, None, None
        if poly_in_il and addr == poly_ilce:
            karar, kaynak = poly_ilce, f"konum+{addr_src}"
        elif poly_ok and addr is None and not addr_conflict and name in (None, poly_ilce):
            karar, kaynak = poly_ilce, "konum" + ("+ad" if name else "")
        elif poly_ok and addr is None and not addr_conflict and name and name != poly_ilce:
            d = dist_km(lat, lon, il, name)
            if d is not None and d < 2.0:
                karar, kaynak = poly_ilce, f"konum (ad {name}, sınıra {d:.1f} km)"
        elif poly_ok and addr and addr != poly_ilce:
            d = dist_km(lat, lon, il, addr)
            if d is not None and d < 2.0:
                karar, kaynak = addr, f"{addr_src} (konum sınıra {d:.1f} km)"
            elif addr_src == "adres" and name == addr:
                karar, kaynak, uyari = addr, "adres+ad", f"koordinat {poly_ilce} içinde, kontrol edilmeli"
            elif addr_src != "adres" and name == poly_ilce:
                karar, kaynak = poly_ilce, "konum+ad"
        elif not poly_ok and addr and addr_src == "adres" and name in (None, addr):
            karar, kaynak = addr, "adres" + ("+ad" if name else "")
            if poly is not None and not shared:
                uyari = f"koordinat {poly_il}/{poly_ilce} içinde, kontrol edilmeli"

        if karar is None and poly_in_il and name == poly_ilce:
            karar, kaynak = poly_ilce, "konum+ad"
            if addr and addr != poly_ilce:
                uyari = f"adreste {addr} yazıyor, kontrol edilmeli"
        if karar is None and addr_shared and addr_sh:
            if poly_in_il and addr_sh == poly_ilce:
                karar, kaynak = addr_sh, "konum+adres"
            elif name == addr_sh:
                karar, kaynak = addr_sh, "adres+ad"
                if poly is not None:
                    uyari = f"koordinat {poly_il}/{poly_ilce} içinde, kontrol edilmeli"

        if karar is None:
            why = []
            if poly is None:
                why.append("koordinat ilçe sınırına düşmüyor" if il != "Kıbrıs" else "KKTC sınır verisi yok")
            elif poly_il != il:
                why.append(f"koordinat {poly_il}/{poly_ilce} içinde")
            else:
                why.append(f"konum {poly_ilce}" + (" (koordinat başka tesisle ortak)" if shared else ""))
            if addr_conflict:
                why.append("adreste birden çok ilçe")
            elif addr:
                why.append(f"{addr_src} {addr}")
            else:
                why.append("adreste ilçe yok")
            if name:
                why.append(f"adda {name}")
            rec.update(karar="belirsiz", neden="; ".join(why), oneri=ovl)
        else:
            rec.update(karar=karar, kaynak=kaynak)
            if uyari:
                rec["uyari"] = uyari
        out.append(rec)

    json.dump(out, open(CACHE / "audit_out.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    c = Counter("belirsiz" if x["karar"] == "belirsiz" else "ok" for x in out)
    print(c)
    print(Counter(x.get("kaynak", x.get("neden", ""))[:40] for x in out).most_common(30))
    ch = [x for x in out if x["karar"] != "belirsiz" and x.get("ovl") and x["ovl"] != x["karar"]]
    print("overlay ile farklı:", len(ch))
    for x in ch:
        print(" C|", x["il"], "|", x["isim"], "| kayıt:", x["ov_ilce"], "->", x["karar"], "|", x["kaynak"], "|", x["adres"])
    for x in out:
        if x.get("uyari"):
            print(" U|", x["il"], "|", x["isim"], "|", x["karar"], "|", x["uyari"], "|", x["adres"])
    for x in out:
        if x["karar"] == "belirsiz":
            print(" B|", x["il"], "|", x["isim"], "|", x["neden"], "| öneri:", x.get("oneri"), "|", x.get("adres"))


if __name__ == "__main__":
    main()
