import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import menu  # noqa: E402
import prices  # noqa: E402

TODAY = date(2026, 10, 8)
URL = "https://www.kayseri.bel.tr/menu.pdf"


def _menu(isim, urunler, kontrol=None, **extra):
    m = {"il": "Kayseri", "isim": isim, "kapsam": "tesis", "kaynak": URL, "kaynak_adi": "Kayseri Belediyesi",
         "belge": "Menü", "yil": 2026, "kategoriler": [{"ad": "Ana yemekler", "urunler": urunler}]}
    if kontrol:
        m.update({"kontrol": kontrol, "dogrulama": kontrol, "durum": "guncel"})
    m.update(extra)
    return m


def _key(isim):
    return prices.facility_key("Kayseri", isim)


def test_price_change_recorded_with_previous_price():
    prev = [_menu("A", [{"ad": "Köfte", "fiyat": 220}], "2026-09-05")]
    found = {_key("A"): _menu("A", [{"ad": "Köfte", "fiyat": 250}, {"ad": "Ayran", "fiyat": 40}])}
    res = prices.update_items(prev, found, set(), set(), TODAY, {}, touch_checked=True)
    urunler = {p["ad"]: p for p in res.items[0]["kategoriler"][0]["urunler"]}
    assert urunler["Köfte"]["fiyat"] == 250
    assert urunler["Köfte"]["onceki"] == {"fiyat": 220, "tarih": "2026-09-05"}
    assert res.changes == [{"tarih": "2026-10-08", "il": "Kayseri", "isim": "A", "urun": "Köfte",
                            "eski": 220, "yeni": 250, "kaynak": URL}]
    assert res.stats.guncellenen_fiyat == 1 and res.stats.yeni_fiyat == 1
    assert res.items[0]["kontrol"] == res.items[0]["dogrulama"] == "2026-10-08"


def test_suspicious_change_needs_review_and_keeps_old_price():
    prev = [_menu("A", [{"ad": "Köfte", "fiyat": 250}], "2026-09-05")]
    found = {_key("A"): _menu("A", [{"ad": "Köfte", "fiyat": 25000}])}
    res = prices.update_items(prev, found, set(), set(), TODAY, {}, touch_checked=True)
    assert res.items[0]["kategoriler"][0]["urunler"][0]["fiyat"] == 250
    assert res.reviews[0]["tur"] == "buyuk_degisim" and res.reviews[0]["yeni"] == 25000
    assert res.changes == []
    approvals = {"buyuk_degisim": [res.reviews[0]["onay_anahtari"]]}
    res2 = prices.update_items(prev, found, set(), set(), TODAY, approvals, touch_checked=True)
    assert res2.items[0]["kategoriler"][0]["urunler"][0]["fiyat"] == 25000 and not res2.reviews


def test_legacy_products_without_unit_match_by_name():
    prev = [_menu("A", [{"ad": "Köfte", "fiyat": 220}, {"ad": "Çay", "fiyat": 20}], "2026-09-05")]
    found = {_key("A"): _menu("A", [{"ad": "Köfte", "fiyat": 220, "birim": "porsiyon"},
                                    {"ad": "Çay", "fiyat": 25, "birim": "bardak"}])}
    res = prices.update_items(prev, found, set(), set(), TODAY, {}, touch_checked=True)
    assert res.stats.yeni_fiyat == 0 and res.stats.guncellenen_fiyat == 1
    assert [c["urun"] for c in res.changes] == ["Çay"]


def test_losing_most_products_keeps_old_menu_for_review():
    old = [{"ad": n, "fiyat": 50} for n in ("Çay", "Kahve", "Ayran", "Tost")]
    prev = [_menu("A", old, "2026-09-05")]
    found = {_key("A"): _menu("A", [{"ad": "Çay", "fiyat": 50}])}
    res = prices.update_items(prev, found, set(), set(), TODAY, {}, touch_checked=True)
    assert res.items == prev
    assert res.reviews[0]["tur"] == "urun_kaybi"
    found = {_key("A"): _menu("A", old[:3])}
    res = prices.update_items(prev, found, set(), set(), TODAY, {}, touch_checked=True)
    assert res.changes[0]["urun"] == "Tost" and res.changes[0]["yeni"] is None


def test_missing_source_keeps_last_verified_prices():
    prev = [_menu("A", [{"ad": "Çay", "fiyat": 20}], "2026-06-01"), _menu("B", [{"ad": "Çay", "fiyat": 20}], "2026-06-01")]
    res = prices.update_items(prev, {}, {_key("A")}, set(), TODAY, {}, touch_checked=True)
    out = {i["isim"]: i for i in res.items}
    assert out["A"]["durum"] == "kaynak_bulunamadi"
    assert out["A"]["dogrulama"] == "2026-06-01" and out["A"]["kontrol"] == "2026-10-08"
    assert out["A"]["kategoriler"][0]["urunler"][0]["fiyat"] == 20
    assert out["B"]["durum"] == "guncel" and out["B"]["kontrol"] == "2026-06-01"
    assert res.stats.kaynak_bulunamayan == 1


def test_weekly_run_does_not_bump_check_date_when_unchanged():
    prev = [_menu("A", [{"ad": "Çay", "fiyat": 20}], "2026-09-05")]
    found = {_key("A"): _menu("A", [{"ad": "Çay", "fiyat": 20}])}
    res = prices.update_items(prev, found, set(), set(), TODAY, {}, touch_checked=False)
    assert res.items == prev


def test_history_appends_only_changes():
    hist = {}
    items = [_menu("A", [{"ad": "Köfte", "fiyat": 220}], "2026-09-05")]
    assert prices.update_history(hist, items, date(2026, 9, 5)) == 1
    assert prices.update_history(hist, items, date(2026, 9, 12)) == 0
    items[0]["kategoriler"][0]["urunler"][0]["fiyat"] = 250
    prices.update_history(hist, items, TODAY)
    assert [h["fiyat"] for h in hist[_key("A")]["kofte|"]] == [220, 250]


def test_units_and_menu_category():
    items = menu.parse_menu(["KAHVALTI", "Serpme kahvaltı 2 kişilik 900 TL", "Çay (bardak) 20 TL",
                             "Çocuk menüsü 180 TL", "Köfte porsiyon 250 TL", "Kuzu şiş 1 kg 1.800 TL"])
    got = {i.name: (i.unit, i.category) for i in items}
    assert got["Serpme kahvaltı 2 kişilik"] == ("kişilik", "Kahvaltı")
    assert got["Çay (bardak)"] == ("bardak", "Sıcak içecekler")
    assert got["Çocuk menüsü"][1] == "Menüler"
    assert got["Köfte"][0] == "porsiyon"
    assert got["Kuzu şiş 1 kg"][0] == "kg"


def _doc(url, title, items, year=2026, lm=None):
    return menu.Doc(url, "pdf", title, title, year, [menu.MenuItem(n, p, "Ana yemekler") for n, p in items],
                    title, lm, "", True)


def _fac(isim, sites):
    rec = {"il": "Kayseri", "ilce": "Melikgazi", "isim": isim, "aciklama": ""}
    return menu.Facility(rec, menu.municipality_of(rec), sites)


def test_fuzzy_name_match_requires_review():
    fac = _fac("Atatürk Parkı Sosyal Tesisleri", ["kayseri.bel.tr"])
    sr = menu.SiteResult("kayseri.bel.tr", True, docs=[_doc(URL, "Atatürk Sosyal Tesisi Menü", [("Köfte", 250)] * 1)])
    m, review = menu.pick_menu(fac, {"kayseri.bel.tr": sr}, TODAY)
    assert m is None and review["tur"] == "belirsiz_eslesme"
    m2, _ = menu.pick_menu(fac, {"kayseri.bel.tr": sr}, TODAY, {"eslesme": [review["onay_anahtari"]]})
    assert m2 is not None and m2["kapsam"] == "tesis"


def test_exact_name_variant_matches():
    fac = _fac("Atatürk Sosyal Tesisleri", ["kayseri.bel.tr"])
    sr = menu.SiteResult("kayseri.bel.tr", True, docs=[_doc(URL, "Atatürk Parkı Sosyal Tesisleri Menü", [("Köfte", 250)])])
    m, review = menu.pick_menu(fac, {"kayseri.bel.tr": sr}, TODAY)
    assert m is not None and m["kapsam"] == "tesis" and review is None


def test_conflicting_undated_sources_need_review_dated_newest_wins():
    fac = _fac("Atatürk Sosyal Tesisleri", ["kayseri.bel.tr"])
    a = _doc("https://kayseri.bel.tr/a.pdf", "Atatürk Sosyal Tesisleri fiyat", [("Köfte", 250)])
    b = _doc("https://kayseri.bel.tr/b.html", "Atatürk Sosyal Tesisleri menü", [("Köfte", 220)])
    sr = menu.SiteResult("kayseri.bel.tr", True, docs=[a, b])
    m, review = menu.pick_menu(fac, {"kayseri.bel.tr": sr}, TODAY)
    assert m is None and review["tur"] == "celiskili_kaynak"
    a.last_modified = "Wed, 01 Oct 2026 08:00:00 GMT"
    m, review = menu.pick_menu(fac, {"kayseri.bel.tr": sr}, TODAY)
    assert m["kaynak"] == a.url and m["kaynak_tarihi"] == "2026-10-01" and review is None


def test_doc_cache_roundtrip():
    d = _doc(URL, "Menü", [("Köfte", 250)])
    d.sha256 = "abc"
    back = menu.Doc.from_cache(URL, d.to_cache())
    assert back.items == d.items and back.sha256 == "abc" and back.year == 2026
