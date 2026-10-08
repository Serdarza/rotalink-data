"""Kamp kaydı eşleme, tekrar engeli ve inceleme kuyruğu.

Bilinmeyen alan null kalır. OSM ücreti resmî fiyat sayılmaz.
Kamp yasağı veya terk işareti olan yer yayımlanmaz.
"""
from __future__ import annotations

import math
from datetime import date

from iller import fold

ATIF = "© OpenStreetMap katkıları (ODbL)"
NEAR_M = 200
FAR_M = 2000


def tri(value) -> bool | None:
    if value is None:
        return None
    f = fold(str(value))
    if f in {"yes", "true", "designated", "1"}:
        return True
    if f in {"no", "false", "0"}:
        return False
    return None


def uygunsuz_ad(ad: str) -> bool:
    """Kamp yasağı tabelası veya yasak ifadesi kamp alanı değildir."""
    f = fold(ad)
    if f.startswith("sign"):
        return True
    return any(x in f for x in ("yasak", "forbidden", "kamp yapilmaz"))


def yasak(tags: dict) -> bool:
    if fold(str(tags.get("abandoned") or "")) in {"yes", "true"}:
        return True
    if fold(str(tags.get("disused") or "")) == "yes":
        return True
    if fold(str(tags.get("access") or "")) == "no":
        return True
    camping = fold(str(tags.get("camping") or ""))
    return camping in {"no", "forbidden"}


def kamp_turu(tags: dict, ad: str) -> str:
    blob = fold(" ".join([
        ad, str(tags.get("operator") or ""), str(tags.get("camp_site") or ""),
    ]))
    if "glamping" in blob or fold(str(tags.get("glamping") or "")) in {"yes", "true"}:
        return "glamping"
    if "milli park" in blob or "tabiat park" in blob:
        return "milli_park"
    if "belediye" in blob:
        return "belediye"
    tents, caravans = tri(tags.get("tents")), tri(tags.get("caravans"))
    if tags.get("tourism") == "caravan_site" or (caravans is True and tents is False):
        return "karavan"
    if tents is True and caravans is not True:
        return "cadir"
    return "kamping"


def ucret(tags: dict) -> str:
    fee = tri(tags.get("fee"))
    if fee is True:
        return "ucretli"
    if fee is False:
        return "ucretsiz"
    return "bilinmiyor"


def _text(*values) -> str | None:
    for v in values:
        s = " ".join(str(v or "").split())
        if s:
            return s
    return None


def _web(tags: dict) -> str | None:
    raw = _text(tags.get("website"), tags.get("contact:website"))
    if not raw:
        return None
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "https://" + raw
    if " " in raw or "@" in raw.split("/")[2]:
        return None
    return raw


def from_osm(il: str, element: dict, today: date) -> dict | None:
    tags = element.get("tags") or {}
    ad = _text(tags.get("name:tr"), tags.get("name"))
    if not ad or yasak(tags) or uygunsuz_ad(ad):
        return None
    if element.get("type") == "node":
        lat, lon = element.get("lat"), element.get("lon")
    else:
        center = element.get("center") or {}
        lat, lon = center.get("lat"), center.get("lon")
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if not (35.0 <= lat <= 43.0 and 25.0 <= lon <= 45.5):
        return None
    osm_type = element.get("type") or "node"
    osm_id = element.get("id")
    ilce = _text(tags.get("addr:district"), tags.get("addr:subdistrict"))
    adres = _text(tags.get("addr:full"), " ".join(x for x in (
        tags.get("addr:street") or "", tags.get("addr:housenumber") or "") if x))
    return {
        "id": f"osm-{osm_type}-{osm_id}",
        "ad": ad,
        "il": il,
        "ilce": ilce,
        "adres": adres,
        "enlem": round(lat, 6),
        "boylam": round(lon, 6),
        "telefon": _text(tags.get("phone"), tags.get("contact:phone")),
        "web": _web(tags),
        "kaynak_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
        "kaynak_turu": "acik_veri",
        "atif": ATIF,
        "kamp_turu": kamp_turu(tags, ad),
        "cadir": tri(tags.get("tents")),
        "karavan": tri(tags.get("caravans")),
        "motokaravan": tri(tags.get("motorhome")),
        "elektrik": tri(tags.get("power_supply")),
        "tuvalet": tri(tags.get("toilets")),
        "dus": tri(tags.get("shower")),
        "icme_suyu": tri(tags.get("drinking_water")),
        "atik": tri(tags.get("sanitary_dump_station")),
        "wifi": tri(tags.get("internet_access")),
        "otopark": tri(tags.get("parking")),
        "denize_yakin": None,
        "fiyat": None,
        "fiyat_birim": None,
        "ucret": ucret(tags),
        "rezervasyon": None,
        "son_kontrol": today.isoformat(),
        "dogrulama": "acik_veri",
        "durum": "aktif",
    }


def hav(a: dict, b: dict) -> float:
    r = 6371000.0
    p1, p2 = math.radians(a["enlem"]), math.radians(b["enlem"])
    dp, dl = math.radians(b["enlem"] - a["enlem"]), math.radians(b["boylam"] - a["boylam"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def _ratio(a: str, b: str) -> float:
    import difflib
    return difflib.SequenceMatcher(None, fold(a), fold(b)).ratio()


def cakisma(a: dict, b: dict) -> str | None:
    """'ayni' yakın tekrar, 'belirsiz' aynı ile benzer ad ama ara mesafe, yoksa None."""
    if a["id"] == b["id"] or fold(a["il"]) != fold(b["il"]):
        return "ayni" if a["id"] == b["id"] else None
    dist = hav(a, b)
    same = fold(a["ad"]) == fold(b["ad"])
    similar = _ratio(a["ad"], b["ad"]) >= 0.82
    if dist <= NEAR_M and (same or similar):
        return "ayni"
    if same and NEAR_M < dist <= FAR_M:
        return "belirsiz"
    return None


def _keep_price(old: dict, new: dict, history: dict, today: date, changes: list) -> None:
    """Eski resmî fiyat, yeni kayıtta fiyat yoksa korunur. OSM fiyat yazmaz."""
    if new.get("fiyat") is None and old.get("fiyat") is not None:
        new["fiyat"] = old["fiyat"]
        new["fiyat_birim"] = old.get("fiyat_birim")
    elif old.get("fiyat") is not None and new.get("fiyat") is not None and old["fiyat"] != new["fiyat"]:
        history.setdefault(new["id"], []).append({
            "tarih": today.isoformat(), "eski": old["fiyat"], "yeni": new["fiyat"],
            "kaynak": new.get("kaynak_url"),
        })
        changes.append(new["id"])


def birlestir(prev: list[dict], found: list[dict], scanned: set[str], failed: set[str],
              today: date, history: dict) -> tuple[list[dict], list[dict], dict]:
    """Dönen: yayımlanacak kayıtlar (inceleme dahil, silinmez), yeni inceleme kayıtları, sayaçlar."""
    reviews: list[dict] = []
    kept: list[dict] = []
    seen_ids: set[str] = set()
    for rec in found:
        twin = next((k for k in kept if cakisma(rec, k) == "ayni"), None)
        if twin:
            reviews.append({
                "tur": "mukerrer", "id": rec["id"], "diger": twin["id"],
                "il": rec["il"], "ad": rec["ad"], "tarih": today.isoformat(),
            })
            continue
        unsure = next((k for k in kept if cakisma(rec, k) == "belirsiz"), None)
        if unsure:
            rec = dict(rec)
            rec["durum"] = "inceleme"
            rec["dogrulama"] = "inceleniyor"
            reviews.append({
                "tur": "belirsiz_mukerrer", "id": rec["id"], "diger": unsure["id"],
                "il": rec["il"], "ad": rec["ad"], "tarih": today.isoformat(),
            })
        kept.append(rec)
        seen_ids.add(rec["id"])

    prev_by = {p["id"]: p for p in prev}
    out: list[dict] = []
    for rec in kept:
        old = prev_by.get(rec["id"])
        merged = dict(rec)
        if old:
            _keep_price(old, merged, history, today, [])
        out.append(merged)

    scanned_ok = {fold(x) for x in scanned - failed}
    for old in prev:
        if old["id"] in seen_ids:
            continue
        item = dict(old)
        if fold(old.get("il", "")) in scanned_ok and str(old.get("id", "")).startswith("osm-"):
            if item.get("durum") != "inceleme":
                item["durum"] = "inceleme"
                item["son_kontrol"] = today.isoformat()
                reviews.append({
                    "tur": "kaynak_bulunamadi", "id": item["id"], "il": item.get("il"),
                    "ad": item.get("ad"), "tarih": today.isoformat(),
                    "detay": "Kayıt silinmedi; kaynak bu taramada yok.",
                })
        out.append(item)

    for rec in out:
        if rec.get("durum") == "aktif" and uygunsuz_ad(rec.get("ad") or ""):
            rec["durum"] = "inceleme"
            rec["dogrulama"] = "inceleniyor"
            reviews.append({
                "tur": "kamp_yasak", "id": rec["id"], "il": rec.get("il"),
                "ad": rec.get("ad"), "tarih": today.isoformat(),
                "detay": "Kamp yasağı veya tabela kaydı yayımlanmadı.",
            })

    out.sort(key=lambda r: (fold(r.get("il", "")), fold(r.get("ad", ""))))
    aktif = [r for r in out if r.get("durum") == "aktif"]
    stats = {
        "aktif": len(aktif),
        "inceleme": sum(1 for r in out if r.get("durum") == "inceleme"),
        "cadir": sum(1 for r in aktif if r.get("cadir") is True),
        "karavan": sum(1 for r in aktif if r.get("karavan") is True or r.get("kamp_turu") == "karavan"),
        "fiyat_dogrulanmis": sum(1 for r in aktif if r.get("fiyat") is not None and r.get("dogrulama") == "resmi"),
    }
    return out, reviews, stats
