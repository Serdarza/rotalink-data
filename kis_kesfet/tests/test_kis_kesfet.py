import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import extract  # noqa: E402
import merge  # noqa: E402
import model  # noqa: E402
from common import DATA, save_json  # noqa: E402


def test_ozel_termal_yazilmaz():
    rec = model.yeni_kayit(
        kategori="termal",
        il="Ankara",
        isim="Özel Termal Otel",
        resmi_kaynak="https://hsgm.saglik.gov.tr/kaplica.pdf",
        today="2026-10-22",
        kurum_turu="Özel tesis",
        kisa="özel",
        tesis_sinifi="ozel",
    )
    assert rec is None


def test_kamu_termal_resmi_kaynakla_eklenir():
    rec = model.yeni_kayit(
        kategori="termal",
        il="Ankara",
        isim="Haymana Belediye Kaplıcası",
        resmi_kaynak="https://hsgm.saglik.gov.tr/kaplica.pdf",
        today="2026-10-22",
        kurum_turu="Belediye",
        kisa="kamu kaplıcası",
        tesis_sinifi="kamu",
    )
    assert rec is not None
    assert rec["id"].startswith("termal-")


def test_ticari_alan_yeni_kayitta_yok():
    rec = model.yeni_kayit(
        kategori="kayak",
        il="Bursa",
        isim="Uludağ Kayak Merkezi",
        resmi_kaynak="https://ornek-kayak-oteli.com/pist",
        today="2026-10-22",
        kurum_turu="Kış sporları merkezi",
        kisa="x",
    )
    assert rec is None


def test_kayak_pdf_yalniz_metinde_olan_imza():
    text = "Zigana Mountain Ski Areas Gümüşhane Ergan Mountain Erzincan"
    found = extract.kayak_pdf(text)
    names = {isim for _il, isim in found}
    assert "Zigana Kayak Merkezi" in names
    assert "Ergan Kayak Merkezi" in names
    assert "Kartepe Kayak Merkezi" not in names


def test_hsgm_ozel_satir_atilir():
    text = "\n".join(
        [
            "Haymana Belediyesi Medrese Kaplıcası Ankara",
            "Mutlular Özel Kaplıca Tesisi Bursa",
        ]
    )
    found = extract.hsgm_kamu(text)
    assert found == [("Ankara", "Medrese Kaplıcası")]


def test_dkmp_kis_park_secer_sahili_atlar():
    html = """
    <table>
    <tr><td>20<br></td><td>Bursa</td><td>Uludağ</td><td>2.Bölge</td></tr>
    <tr><td>9<br></td><td>Antalya</td><td>Beydağları Sahil</td><td>6.Bölge</td></tr>
    <tr><td>32<br></td><td>Kastamonu-Çankırı</td><td>Ilgaz Dağı</td><td>10.Bölge</td></tr>
    </table>
    """
    found = extract.dkmp_kis(html)
    names = {isim for _il, isim in found}
    assert any("Uludağ" in n for n in names)
    assert any("Ilgaz" in n for n in names)
    assert not any("Sahil" in n for n in names)


def test_birlestir_kategori_disina_tasmaz(tmp_path, monkeypatch):
    monkeypatch.setattr(merge, "DATA", tmp_path)
    save_json(
        tmp_path / "kayak.json",
        {
            "kayitlar": [
                {
                    "id": "kayak-bursa-uludag",
                    "kategori": "kayak",
                    "il": "Bursa",
                    "isim": "Uludağ Kayak Merkezi",
                    "kurumTuru": "Kış sporları merkezi",
                    "kisaAciklama": "x",
                    "adres": "",
                    "telefon": "",
                    "kullanimTuru": "",
                    "resmiKaynak": "https://www.ktb.gov.tr/uludag",
                    "sonDogrulama": "2026-10-22",
                }
            ]
        },
    )
    save_json(tmp_path / "termal.json", {"kayitlar": []})
    save_json(
        tmp_path / "kis_gezisi.json",
        {
            "kayitlar": [
                {
                    "id": "gezi-bursa-uludag-mp",
                    "kategori": "kisGezisi",
                    "il": "Bursa",
                    "isim": "Uludağ Milli Parkı",
                    "kurumTuru": "Milli park",
                    "kisaAciklama": "x",
                    "adres": "",
                    "telefon": "",
                    "kullanimTuru": "",
                    "resmiKaynak": "https://www.tarimorman.gov.tr/DKMP/Menu/27/Milli-Parklar",
                    "sonDogrulama": "2026-10-22",
                }
            ]
        },
    )
    out = merge.birlestir("2026-10-22")
    assert [r["kategori"] for r in out["kayitlar"]] == ["kayak", "kisGezisi"]
