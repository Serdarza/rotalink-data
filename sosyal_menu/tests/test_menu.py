import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import menu  # noqa: E402

TODAY = date(2026, 10, 1)


def test_parse_price_formats():
    assert menu.parse_price("15,00") == 15.0
    assert menu.parse_price("1.250,50") == 1250.5
    assert menu.parse_price("12.5") == 12.5
    assert menu.parse_price("40") == 40.0
    assert menu.parse_price("abc") is None


def test_split_item_fatsa_lines():
    assert menu.split_item(menu.clean_line("BARDAK ÇAY 15,00")) == ("BARDAK ÇAY", 15.0)
    assert menu.split_item(menu.clean_line("KAHVALTI TABAĞI 160,00 TL 180,00 TL")) == ("KAHVALTI TABAĞI", 180.0)
    assert menu.split_item(menu.clean_line("KIYMALI PİDE 1,5 340,00")) == ("KIYMALI PİDE 1,5", 340.0)


def test_split_item_ordu_tariff_line():
    line = menu.clean_line("1 2464 S.K.97. md. ÇAY Adet ₺10,00 10% 31.12.2026")
    assert menu.split_item(line) == ("ÇAY", 10.0)


def test_nice_name_all_caps():
    assert menu.nice_name("BARDAK ÇAY") == "Bardak çay"


def test_split_item_rejects_phone_numbers():
    assert menu.split_item(menu.clean_line("Tel: 0452 423 10 10")) is None


def test_parse_menu_headers_and_exclusions():
    lines = [
        "SICAK İÇECEKLER",
        "Bardak Çay 15 TL",
        "Türk Kahvesi 60 TL",
        "SALON KİRALAMA",
        "Düğün Salonu (4 saat) 25.000 TL",
        "Kokteyl paketi 450 TL",
        "TATLILAR",
        "Künefe 150 TL",
        "Sütlaç",
        "90 TL",
        "Adres: Cumhuriyet Mah. No: 12",
        "Peynirli Tost / With Cheese Toast 120 TL",
        "Isirgan Corbasi 12 Hoskiran Kavurmasi 46",
    ]
    items = menu.parse_menu(lines)
    got = {(i.name, i.price, i.category) for i in items}
    assert ("Bardak Çay", 15.0, "Sıcak içecekler") in got
    assert ("Türk Kahvesi", 60.0, "Sıcak içecekler") in got
    assert ("Künefe", 150.0, "Tatlılar") in got
    assert ("Sütlaç", 90.0, "Tatlılar") in got
    assert ("Peynirli Tost", 120.0, "Atıştırmalıklar") in got
    names = {i.name for i in items}
    assert not any("Hoskiran" in n for n in names)
    assert not any("Düğün" in n or "Kokteyl" in n or "Adres" in n for n in names)


def test_categorize():
    assert menu.categorize("Soğuk Çay") == "Soğuk içecekler"
    assert menu.categorize("Çay") == "Sıcak içecekler"
    assert menu.categorize("Tavuklu Salata") == "Salatalar"
    assert menu.categorize("Su Böreği") != "Soğuk içecekler"
    assert menu.categorize("Su 0,5 lt") == "Soğuk içecekler"
    assert menu.categorize("Mercimek Çorbası") == "Çorbalar"
    assert menu.categorize("Kuru incir 150g") == "Atıştırmalıklar"


def test_official_url():
    assert menu.official_url("https://www.fatsa.bel.tr/menu")
    assert menu.official_url("https://tesislerimiz.ibb.istanbul/")
    assert not menu.official_url("https://lezzetrotam.com/fatsa")
    assert not menu.official_url("http://1.2.3.4/menu")
    assert not menu.official_url("https://user:pw@fatsa.bel.tr/")
    assert not menu.official_url("https://fatsa.bel.tr:8443/")
    assert not menu.official_url("javascript:alert(1)")
    assert not menu.official_url("https://fatsa.bel.tr.evil.com/")


def test_municipality_of():
    m = menu.municipality_of({"il": "Ordu", "ilce": "Fatsa", "isim": "Fatsa Belediyesi Sosyal Tesisleri"})
    assert m is not None and m.key == "Ordu|Fatsa"
    m = menu.municipality_of({"il": "Adana", "ilce": "Seyhan", "isim": "Adana Büyükşehir Belediyesi Sosyal Tesisi"})
    assert m is not None and m.key == "Adana|"
    assert menu.municipality_of({"il": "Ordu", "ilce": "Fatsa", "isim": "Öğretmenevi"}) is None


def test_implicit_municipality_and_loose_names():
    m = menu.municipality_of({"il": "İstanbul", "ilce": "Avcılar", "isim": "Avcılar Sosyal Tesisleri"})
    assert m is not None and m.key == "İstanbul|Avcılar"
    rec = {"il": "İstanbul", "ilce": "Ataşehir", "isim": "Ataşehir Kent Lokantası"}
    assert menu.municipality_of(rec) is None
    toks = menu.distinctive_tokens(rec, None)
    assert not menu.mentions_facility("ATA KÜLTÜR KAFE T.C. Ataşehir Belediyesi Kent", toks)


def test_non_food_fees_and_portions_rejected():
    assert menu.parse_menu(["TATLILAR", "c) Pasta İmalat 13.125,00", "e) Beher yemek asansörleri için 3.697"]) == []
    assert menu.split_item(menu.clean_line("İsbendek levrek ızgara 3/ 4")) is None


def test_recent_enough():
    new = menu.Doc("https://x.bel.tr/a.pdf", "pdf", "", "", 2026, [], "", None)
    old = menu.Doc("https://x.bel.tr/b.pdf", "pdf", "", "", 2021, [], "", None)
    assert menu.recent_enough(new, TODAY)
    assert not menu.recent_enough(old, TODAY)


def _item(isim, kontrol, fiyat=15.0):
    return {"il": "Ordu", "isim": isim, "kapsam": "tesis", "kaynak": "https://fatsa.bel.tr/a.pdf", "yil": 2026,
            "kategoriler": [{"ad": "Sıcak içecekler", "urunler": [{"ad": "Çay", "fiyat": fiyat}]}],
            "kontrol": kontrol}


def test_merge_keeps_unchanged_date_and_updates_changed():
    prev = [_item("A", "2026-09-01"), _item("B", "2026-09-01")]
    found = {"ordu|a": {k: v for k, v in _item("A", "").items() if k != "kontrol"},
             "ordu|b": {k: v for k, v in _item("B", "", fiyat=20.0).items() if k != "kontrol"}}
    out = {x["isim"]: x for x in menu.merge(prev, found, set(), TODAY, keep_all=False)}
    assert out["A"]["kontrol"] == "2026-09-01"
    assert out["B"]["kontrol"] == TODAY.isoformat()


def test_merge_unreachable_and_removed():
    prev = [_item("A", "2026-09-01"), _item("B", "2026-09-01"), _item("C", "2025-01-01")]
    out = {x["isim"] for x in menu.merge(prev, {}, {"ordu|a", "ordu|c"}, TODAY, keep_all=False)}
    # A: site down, recent → kept. B: site up but no menu anymore → dropped. C: down too long → dropped.
    assert out == {"A"}
    assert len(menu.merge(prev, {}, set(), TODAY, keep_all=True)) == 3
