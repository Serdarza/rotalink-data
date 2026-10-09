import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import iller  # noqa: E402
import resmi  # noqa: E402
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


_OGM_SAYFA = """
<h1>Kefe Yaylası Orman Parkı</h1>
<h3 class="subtitle mb-4" id="ozellikler">Özellikler</h3>
<div class="feature-item"><img alt="Çadırlı Kamp " /><span>Çadırlı Kamp </span></div>
<div class="feature-item"><span>Otopark</span></div>
<h3 class="subtitle mb-4" id="aktiviteler">Aktiviteler</h3>
<div class="feature-item"><span>Piknik</span></div>
<h3 class="subtitle mb-4" id="harita">Haritada Göster</h3>
<iframe src="https://maps.google.com/maps?q=37.625326197038,29.382593929768&hl=tr-TR"></iframe>
<h3 class="subtitle mb-4" id="iletisim-bilgileri">İletişim Bilgileri</h3>
<strong>Adres</strong> <span>Kocapınar Mah. 20430 Serinhisar / DENİZLİ</span>
<strong>Telefon</strong> <span>(444) 852 0_ __</span>
"""


def test_ogm_kamp_sayfasi_resmi_kayit():
    rec = resmi.ogm_kayit(_OGM_SAYFA, "https://benimormanim.ogm.gov.tr/orman-parklari/kefe-306", "306", TODAY)
    assert rec["id"] == "ogm-306" and rec["il"] == "Denizli" and rec["ilce"] == "Serinhisar"
    assert rec["enlem"] == 37.625326 and rec["cadir"] is True and rec["otopark"] is True
    assert rec["telefon"] is None and rec["fiyat"] is None and rec["tuvalet"] is None
    assert rec["dogrulama"] == "resmi" and "Orman Genel" in rec["atif"]
    piknik = _OGM_SAYFA.replace("Çadırlı Kamp", "Kameriye")
    assert resmi.ogm_kayit(piknik, "u", "1", TODAY) is None
    assert resmi._telefon("(053) 030 86 51") is None
    assert resmi._telefon("0 (232) 617 19 17") == "0232 617 19 17"
    aliaga = _OGM_SAYFA.replace("Kocapınar Mah. 20430 Serinhisar / DENİZLİ", "Çamlık Mevkii /Aliağa / İZMİR")
    assert resmi.ogm_kayit(aliaga, "u", "2", TODAY)["ilce"] == "Aliağa"


def test_ogm_kaybolursa_incelemeye_alinir_osm_tekrari_elenir():
    rec = resmi.ogm_kayit(_OGM_SAYFA, "u", "306", TODAY)
    osm = from_osm("Denizli", _el(id=7, name="Kefe Yaylası", lat=37.6254, lon=29.3826), TODAY)
    items, reviews, stats = birlestir([], [rec, osm], {"Denizli"}, set(), TODAY, {})
    assert stats["aktif"] == 1 and items[0]["id"] == "ogm-306"
    items2, reviews2, _ = birlestir([rec], [], set(), set(), TODAY, {}, frozenset({"ogm-"}))
    assert items2[0]["durum"] == "inceleme" and reviews2[0]["tur"] == "kaynak_bulunamadi"
    items3, _, _ = birlestir([rec], [], set(), set(), TODAY, {})
    assert items3[0]["durum"] == "aktif"


def test_ktb_belgeli_eslesme():
    doc = ('[{"belgeNo":"20972","tesisAdi":"KELES GÖL KAMP","belgeTuru":"x","belgeDurumu":"Belgeli Tesisler",'
           '"tesisTuru":"Kamping","tesisSinifi":null,"sehir":"BURSA","ilce":"KELES"},'
           '{"belgeNo":"1","tesisAdi":"YOK KAMP","belgeTuru":"x","belgeDurumu":"Belgeli Tesisler",'
           '"tesisTuru":"Kamping","tesisSinifi":null,"sehir":"İZMİR","ilce":"SELÇUK"}]')
    belgeli = resmi.ktb_kampingler(doc)
    assert [b["il"] for b in belgeli] == ["Bursa", "İzmir"]
    rec = from_osm("Bursa", _el(id=8, name="Keles Göl Camping"), TODAY)
    n, reviews = resmi.ktb_esle([rec], belgeli, TODAY)
    assert n == 1 and rec["bakanlik_belge_no"] == "20972"
    assert reviews[0]["tur"] == "ktb_konum_yok"


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
