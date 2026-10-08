"""Yayımlanmış menü fiyatlarını yeni tarama sonucuyla karşılaştırır.

Kurallar:
  * Değişen fiyat için değişiklik kaydı (eski / yeni / tarih) ve fiyat geçmişi tutulur; geçmiş silinmez.
  * Eski fiyatın 3 katından fazla ya da üçte birinden az değişim otomatik yayımlanmaz:
    eski fiyat korunur, inceleme kuyruğuna yazılır (onaylar.json ile onaylanabilir).
  * Kaynağı artık bulunamayan tesisin fiyatları silinmez; durum "kaynak_bulunamadi" olur,
    son doğrulama tarihi korunur.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

MAX_RATIO = 3.0
STATUS_OK = "guncel"
STATUS_NOT_FOUND = "kaynak_bulunamadi"


def fold_key(s: str) -> str:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosucgiosuaiu")
    return " ".join(s.translate(tr).lower().split())


def facility_key(il: str, isim: str) -> str:
    return f"{fold_key(il)}|{fold_key(isim)}"


def product_key(p: dict) -> str:
    return f"{fold_key(p['ad'])}|{p.get('birim', '')}"


@dataclass
class Stats:
    fiyat_bulunan_tesis: int = 0
    guncellenen_fiyat: int = 0
    yeni_fiyat: int = 0
    kaynak_bulunamayan: int = 0
    inceleme: int = 0


@dataclass
class UpdateResult:
    items: list[dict]
    changes: list[dict] = field(default_factory=list)
    reviews: list[dict] = field(default_factory=list)
    stats: Stats = field(default_factory=Stats)


def _products(item: dict) -> dict[str, tuple[str, dict]]:
    return {product_key(p): (c["ad"], p) for c in item.get("kategoriler", []) for p in c.get("urunler", [])}


def big_change(old: float, new: float) -> bool:
    return old > 0 and new > 0 and (new / old > MAX_RATIO or old / new > MAX_RATIO)


def update_items(prev_items: list[dict], found: dict[str, dict], not_found: set[str], keep: set[str],
                 today: date, approvals: dict, touch_checked: bool) -> UpdateResult:
    """found: tesis anahtarı → yeni menü (kategoriler/urunler, kaynak, kapsam...).
    not_found: sitesi tarandığı hâlde menüsü bulunamayan tesisler.
    keep: inceleme bekleyen ya da sitesine ulaşılamayan tesisler (dokunulmaz).
    touch_checked: aylık tam taramada True → 'kontrol' tarihi bugüne çekilir."""
    t = today.isoformat()
    approved = set(approvals.get("buyuk_degisim", []))
    prev = {facility_key(p["il"], p["isim"]): p for p in prev_items}
    res = UpdateResult(items=[])
    held: set[str] = set()

    for k, new in found.items():
        old = prev.get(k)
        old_products = _products(old) if old else {}
        by_name = {fold_key(p["ad"]): p for _c, p in old_products.values() if not p.get("birim")}
        new_keys = {product_key(p) for c in new["kategoriler"] for p in c["urunler"]}
        new_names = {fold_key(p["ad"]) for c in new["kategoriler"] for p in c["urunler"]}
        missing = [p for pk, (_c, p) in old_products.items()
                   if pk not in new_keys and not (not p.get("birim") and fold_key(p["ad"]) in new_names)]
        if old_products and len(missing) > len(old_products) / 2:
            res.reviews.append({
                "tur": "urun_kaybi", "il": new["il"], "isim": new["isim"], "kaynak": new["kaynak"],
                "detay": f"Yeni belgede eski {len(old_products)} üründen {len(missing)} tanesi yok; "
                         "eski fiyatlar korundu.",
            })
            held.add(k)
            continue
        for p in missing:
            res.changes.append({"tarih": t, "il": new["il"], "isim": new["isim"], "urun": p["ad"],
                                "eski": p["fiyat"], "yeni": None, "kaynak": new["kaynak"]})
        cats = []
        for c in new["kategoriler"]:
            urunler = []
            for p in c["urunler"]:
                pk = product_key(p)
                prod = {key: p[key] for key in ("ad", "fiyat", "birim") if p.get(key) not in (None, "")}
                prior = old_products.get(pk, (None, None))[1] or by_name.get(fold_key(p["ad"]))
                if prior is None:
                    res.stats.yeni_fiyat += 1
                elif prior["fiyat"] != p["fiyat"]:
                    approval_key = f"{k}|{pk}|{p['fiyat']}"
                    if big_change(prior["fiyat"], p["fiyat"]) and approval_key not in approved:
                        prod["fiyat"] = prior["fiyat"]
                        if prior.get("onceki"):
                            prod["onceki"] = prior["onceki"]
                        res.reviews.append({
                            "tur": "buyuk_degisim", "il": new["il"], "isim": new["isim"], "urun": p["ad"],
                            "eski": prior["fiyat"], "yeni": p["fiyat"], "kaynak": new["kaynak"],
                            "onay_anahtari": approval_key,
                        })
                    else:
                        prod["onceki"] = {"fiyat": prior["fiyat"], "tarih": old.get("dogrulama") or old.get("kontrol")}
                        res.changes.append({
                            "tarih": t, "il": new["il"], "isim": new["isim"], "urun": p["ad"],
                            "eski": prior["fiyat"], "yeni": p["fiyat"], "kaynak": new["kaynak"],
                        })
                        res.stats.guncellenen_fiyat += 1
                elif prior.get("onceki"):
                    prod["onceki"] = prior["onceki"]
                urunler.append(prod)
            cats.append({"ad": c["ad"], "urunler": urunler})
        item = {key: v for key, v in new.items() if key != "kategoriler"}
        item["kategoriler"] = cats
        item["durum"] = STATUS_OK
        unchanged = old is not None and _same_published(old, item)
        if unchanged:
            item["kontrol"] = t if touch_checked else old.get("kontrol", t)
            item["dogrulama"] = t if touch_checked else old.get("dogrulama", old.get("kontrol", t))
        else:
            item["kontrol"] = t
            item["dogrulama"] = t
        res.items.append(item)
        res.stats.fiyat_bulunan_tesis += 1

    for k, old in prev.items():
        if k in found and k not in held:
            continue
        item = dict(old)
        item.setdefault("dogrulama", old.get("kontrol"))
        if k in not_found and k not in keep and k not in held:
            item["durum"] = STATUS_NOT_FOUND
            res.stats.kaynak_bulunamayan += 1
        else:
            item.setdefault("durum", STATUS_OK)
        if touch_checked and k in not_found:
            item["kontrol"] = t
        res.items.append(item)

    res.items.sort(key=lambda x: (fold_key(x["il"]), fold_key(x["isim"])))
    res.stats.inceleme = len(res.reviews)
    return res


def _same_published(old: dict, new: dict) -> bool:
    keys = ("kapsam", "kaynak", "yil", "kategoriler", "durum", "kaynak_tarihi")
    return all(old.get(k) == new.get(k) for k in keys)


def update_history(history: dict, items: list[dict], today: date) -> int:
    """Her yayımlanan ürün fiyatı, son kayıttan farklıysa geçmişe eklenir. Eklenen kayıt sayısını döner."""
    added = 0
    for it in items:
        if it.get("durum") == STATUS_NOT_FOUND:
            continue
        fh = history.setdefault(facility_key(it["il"], it["isim"]), {})
        for c in it["kategoriler"]:
            for p in c["urunler"]:
                h = fh.setdefault(product_key(p), [])
                if not h or h[-1]["fiyat"] != p["fiyat"]:
                    h.append({"tarih": today.isoformat(), "fiyat": p["fiyat"], "kaynak": it["kaynak"]})
                    added += 1
    return added
