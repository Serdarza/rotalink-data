import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import iller  # noqa: E402
from model import birlestir, cakisma, from_osm, kamp_turu, turkce_ad, ucret  # noqa: E402

TODAY = date(2026, 10, 8)


def _el(**tags):
    lat = tags.pop("lat", 36.8)
    lon = tags.pop("lon", 30.7)
    return {"type": "node", "id": tags.pop("id", 1), "lat": lat, "lon": lon, "tags": tags}


def test_81_il_ve_alti_il_secimi():
    assert len(iller.ILLER) == 81
    sec = iller.sec({"mugla", "İstanbul", "olmayan"})
    assert [a for a, _ in sec] == ["İstanbul", "Muğla"]


def test_bilinmeyen_alan_null_ve_ucret_fiyat_degil():
    rec = from_osm("Antalya", _el(name="Karaöz Kamp", fee="yes", charge="250 TL", toilets="yes"), TODAY)
    assert rec["fiyat"] is None
    assert rec["ucret"] == "ucretli"
    assert rec["tuvalet"] is True
    assert rec["dus"] is None
    assert rec["denize_yakin"] is None
    assert rec["dogrulama"] == "acik_veri"


def test_yasak_tabelasi_yayinlanmaz():
    assert from_osm("Muğla", _el(name="sign: camping strictly forbidden"), TODAY) is None
    old = from_osm("Muğla", _el(id=4, name="Orman Kamp"), TODAY)
    old["ad"] = "sign: camping strictly forbidden"
    items, reviews, stats = birlestir([old], [], set(), set(), TODAY, {})
    assert stats["aktif"] == 0
    assert reviews[0]["tur"] == "kamp_yasak"


def test_turkce_olmayan_ad_yayinlanmaz_silinmez():
    for ad in ("Kaş Camping", "Kekova camping", "Mustafa's Place", "Olympos Woods",
               "Serbest kamp", "Nirvana Camping & Restaurant", "Ada Camping"):
        assert turkce_ad(ad), ad
    for ad in ("Место под палатку", "Кемпинг", "2 tents", "Place for tent", "Nice view",
               "1", "Camping", "Dort darf man nicht mehr übernachten!!", "geschlossen",
               "Camp, good place for tent and Hamak", "Wild camp"):
        assert not turkce_ad(ad), ad
    rec = from_osm("Muğla", _el(id=5, name="Place for tent"), TODAY)
    items, reviews, stats = birlestir([], [rec], {"Muğla"}, set(), TODAY, {})
    assert stats["aktif"] == 0 and len(items) == 1
    assert items[0]["durum"] == "inceleme"
    assert reviews[0]["tur"] == "turkce_olmayan_ad"
    tr = from_osm("Muğla", _el(id=6, name="Place for tent", **{"name:tr": "Çadır Alanı"}), TODAY)
    assert tr["ad"] == "Çadır Alanı"


def test_yasak_ve_glamping():
    assert from_osm("Muğla", _el(name="Orman", access="no"), TODAY) is None
    assert from_osm("Muğla", _el(name="Eski", abandoned="yes"), TODAY) is None
    assert kamp_turu({"glamping": "yes"}, "Tepe") == "glamping"
    assert ucret({}) == "bilinmiyor"


def test_yakin_kayit_tekrar_etmez_uzak_kayit_kalir():
    a = from_osm("Antalya", _el(id=1, name="Olimpos Kamp"), TODAY)
    b = from_osm("Antalya", _el(id=2, name="Olimpos Kampı", lat=36.8004, lon=30.7004), TODAY)
    c = from_osm("Antalya", _el(id=3, name="Olimpos Kamp", lat=37.1, lon=30.7), TODAY)
    assert cakisma(a, b) == "ayni"
    assert cakisma(a, c) is None
    items, reviews, stats = birlestir([], [a, b, c], {"Antalya"}, set(), TODAY, {})
    assert stats["aktif"] == 2
    assert reviews[0]["tur"] == "mukerrer"
    assert all(r["id"] != b["id"] for r in items)


def test_kaynak_kaybolunca_kayit_silinmez():
    old = from_osm("İzmir", _el(id=9, name="Eski Kamp"), TODAY)
    items, reviews, _ = birlestir([old], [], {"İzmir"}, set(), TODAY, {})
    assert items[0]["durum"] == "inceleme"
    assert reviews[0]["tur"] == "kaynak_bulunamadi"
    items2, reviews2, _ = birlestir([old], [], set(), {"İzmir"}, TODAY, {})
    assert items2[0]["durum"] == "aktif" and reviews2 == []
