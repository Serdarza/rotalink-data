import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bul  # noqa: E402
import gonder  # noqa: E402


def test_belediye_adi_tahmin_etmez():
    assert bul.belediye_adi({"isim": "Seyhan Belediyesi Sosyal Tesisi"}) == "Seyhan"
    assert bul.belediye_adi({"isim": "Marina", "aciklama": "Adana Büyükşehir Belediyesi'ne aittir."}) == "Adana Büyükşehir"
    assert bul.belediye_adi({"isim": "İBB Florya Sosyal Tesisleri"}) == "İstanbul Büyükşehir"
    assert bul.belediye_adi({"isim": "Gemi Cafe", "aciklama": "Sahilde kafe."}) is None


def test_alan_adi_yalniz_resmi():
    assert bul.aday_alanlar("Adana Büyükşehir", "Adana") == ["adana.bel.tr"]
    assert bul.aday_alanlar("Taşova", "Amasya")[0] == "tasova.bel.tr"
    assert bul.fetch("https://ornek.com/") is None
    assert bul.fetch("file:///etc/passwd") is None


def test_yalniz_kurumsal_eposta():
    alan = "suluova.bel.tr"
    assert bul.uygun_eposta("hilalmasa@suluova.bel.tr", alan)
    assert bul.uygun_eposta("bilgi@suluova.bel.tr", alan)
    assert bul.uygun_eposta("suluova@suluova.bel.tr", alan)
    assert not bul.uygun_eposta("adem.ayvali@suluova.bel.tr", alan)
    assert not bul.uygun_eposta("suluovabelediyesi@hs01.kep.tr", alan)
    assert not bul.uygun_eposta("info@gmail.com", alan)
    assert bul.en_iyi({"info@x.bel.tr", "bilgiedinme@x.bel.tr", "halkmasasi@x.bel.tr"}) == "bilgiedinme@x.bel.tr"
    assert bul._cf_decode("422b2c242d02") == "info@"


def test_mail_basligi_enjeksiyonu_engellenir():
    assert gonder.gecerli_adres("bilgi@tasova.bel.tr")
    assert not gonder.gecerli_adres("bilgi@tasova.bel.tr\nBcc: x@y.com")
    assert not gonder.gecerli_adres("bilgi@gmail.com")
    assert gonder.temiz_satir("A\r\nBcc: x") == "A Bcc: x"


def test_basvuru_metni_ve_alti_ay_kurali():
    rec = {"belediye": "Taşova Belediyesi", "il": "Amasya", "eposta": "info@tasova.bel.tr",
           "tesisler": ["Taşova Belediyesi Sosyal Tesisleri"]}
    kimlik = {"ad": "Ad Soyad", "tc": "", "adres": "Adres", "eposta": "a@b.com", "telefon": ""}
    msg = gonder.mesaj(rec, kimlik, "gonderen@b.com")
    govde = msg.get_content()
    assert "4982" in govde and "Taşova Belediyesi Sosyal Tesisleri" in govde
    assert msg["To"] == "info@tasova.bel.tr" and msg["Reply-To"] == "a@b.com"
    from datetime import date
    assert not gonder.zamani_geldi({"son": "2026-08-01"}, date(2026, 10, 9))
    assert gonder.zamani_geldi({"son": "2026-01-01"}, date(2026, 10, 9))
    assert gonder.zamani_geldi(None, date(2026, 10, 9))
