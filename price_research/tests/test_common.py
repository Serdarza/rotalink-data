import json
import sys
from datetime import date
from pathlib import Path

PR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PR))

import common  # noqa: E402
from common import (digits, norm, period_end, resmi_alan_adi, source_numbers, tarife_expired,  # noqa: E402
                    tarife_prices, year_price_phrase)
from validate import new_errors, validate_data  # noqa: E402


def test_source_numbers_turkish_formats():
    n = source_numbers("Tek kişilik 1.500,00 TL | Çift 2 250 TL | Suit 3,750 | Ek yatak 450,50")
    assert {1500.0, 2250.0, 3750.0, 450.5} <= n


def test_tarife_prices_and_expiry():
    tar = {"donem": "01.01.2026 – 30.06.2026",
           "tablolar": [{"satirlar": [{"ad": "Tek", "fiyatlar": {"sivil": 1200, "kamu": 900}}]}]}
    assert sorted(tarife_prices(tar)) == [900.0, 1200.0]
    assert period_end(tar["donem"]) == date(2026, 6, 30)
    assert tarife_expired(tar, date(2026, 7, 1))
    assert not tarife_expired(tar, date(2026, 6, 30))
    assert not tarife_expired({"donem": "2026 yılı"}, date(2027, 1, 2))


def test_year_price_phrase():
    assert year_price_phrase("2026 Yılı Konaklama Ücretleri", 2026)
    assert year_price_phrase("Fiyat listesi (01.01.2026)", 2026)
    assert not year_price_phrase("Haber 12.03.2026. Okulumuzda tören yapıldı.", 2026)


def test_resmi_alan_adi():
    common.RESMI_EK = set()
    assert resmi_alan_adi("https://ankara.meb.gov.tr/x.pdf")
    assert resmi_alan_adi("https://www.adana.pol.tr/")
    assert not resmi_alan_adi("https://www.tatilsitesi.com/")
    common.RESMI_EK = {"ornekogretmenevi.com"}
    assert resmi_alan_adi("https://www.ornekogretmenevi.com/fiyat")
    common.RESMI_EK = set()


def test_norm_digits():
    assert norm("Öğretmenevi ÇANKAYA") == "ogretmenevi cankaya"
    assert digits("0 (312) 555 12 34") == "5551234"


def _entry(**kw):
    e = {"il": "Ankara", "isim": "Test Tesisi", "fiyat_sivil": "1.000 TL", "fiyat_kamu_personeli": None,
         "fiyat_kurum_personeli": None, "kaynak": "https://ankara.meb.gov.tr/", "gecerlilik": "2026",
         "tarife": {"dogrulama": "resmi_kaynak", "kategoriler": [{"id": "sivil", "ad": "Sivil"}],
                    "tablolar": [{"satirlar": [{"ad": "Tek", "fiyatlar": {"sivil": 1000}}]}]}}
    e.update(kw)
    return e


def test_validate_ok_and_errors():
    keys = {("Ankara", "Test Tesisi")}
    assert validate_data({"tesisler": [_entry()]}, keys) == []
    bad = _entry()
    bad["tarife"] = {**bad["tarife"], "dogrulama": "uydurma"}
    errs = validate_data({"tesisler": [_entry(), bad]}, keys)
    assert errs and new_errors([], errs)


def test_new_errors_ignores_legacy():
    keys = {("Ankara", "Test Tesisi")}
    before = validate_data({"tesisler": [_entry(), _entry()]}, keys)  # yinelenen kayıt
    after = validate_data({"tesisler": [_entry(), _entry()]}, keys)
    assert before and new_errors(before, after) == []


def test_repo_files_are_valid_json():
    root = PR.parent
    for p in (root / "fiyatlar.json", PR / "sources.json", PR / "kurumlar.json", PR / "config.json"):
        json.loads(p.read_text(encoding="utf-8"))
    assert json.loads((PR / "config.json").read_text(encoding="utf-8"))["canli"] in (True, False)
