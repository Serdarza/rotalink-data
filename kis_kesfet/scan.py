"""Aylık kategori taraması. Yalnız resmî sayfada görünen yer eklenir; silinmez."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import (  # noqa: E402
    DATA,
    KATEGORI_DOSYA,
    REPORTS,
    SOURCES,
    fetch,
    http_url,
    load_json,
    resmi_alan_adi,
    save_json,
    temiz_html,
)
from extract import anahtarlar_var, dkmp_kis, hsgm_kamu, kayak_pdf  # noqa: E402
from merge import birlestir  # noqa: E402
from model import ayni_yer, dogrula, yeni_kayit  # noqa: E402

KISA = {
    "kayak": "Kültür ve Turizm Bakanlığı kayak merkezleri kaynağında yer alır.",
    "termal": "Sağlık Bakanlığı lisanslı kamu/belediye kaplıcası olarak kayıtlıdır.",
    "kisGezisi": "Tarım ve Orman Bakanlığı milli park listesinde yer alır.",
}
KURUM = {
    "kayak": "Kış sporları merkezi",
    "termal": "Belediye",
    "kisGezisi": "Milli park",
}


def _dry() -> bool:
    return os.environ.get("DRY_RUN", "").lower() in {"1", "true", "yes"}


def _metin_kaynak(url: str, ham: str) -> str:
    if url.lower().split("?")[0].endswith(".pdf") or ham[:5] == "%PDF-":
        return ham
    return temiz_html(ham)


def _ekle(kayitlar: list[dict], rec: dict | None, eklenen: list[str]) -> None:
    if rec is None:
        return
    if any(ayni_yer(rec, x) for x in kayitlar):
        return
    kayitlar.append(rec)
    eklenen.append(rec["id"])


def tara(kategori: str, today: str) -> dict:
    path = DATA / KATEGORI_DOSYA[kategori]
    blob = load_json(path, {"kayitlar": []})
    kayitlar = blob.get("kayitlar") if isinstance(blob, dict) else []
    if not isinstance(kayitlar, list):
        kayitlar = []
    kaynaklar = load_json(SOURCES / f"{kategori}.json", {})
    rapor = {
        "kategori": kategori,
        "tarih": today,
        "dogrulanan": 0,
        "erisilemeyen": [],
        "eklenen": [],
        "atlanan": [],
    }

    for rec in kayitlar:
        if not isinstance(rec, dict):
            continue
        url = http_url(rec.get("resmiKaynak") or "")
        if not url:
            continue
        ok, ham, _status = fetch(url)
        if not ok:
            rapor["erisilemeyen"].append(rec.get("id") or url)
            continue
        metin = _metin_kaynak(url, ham)
        if anahtarlar_var(metin, [rec.get("isim", ""), rec.get("il", "")]):
            rec["sonDogrulama"] = today
            rapor["dogrulanan"] += 1

    for kat in kaynaklar.get("kataloglar") or []:
        url = http_url((kat or {}).get("url") or "")
        tur = (kat or {}).get("tur") or ""
        if not url or not resmi_alan_adi(url):
            rapor["atlanan"].append(f"katalog:{tur}")
            continue
        ok, ham, _status = fetch(url)
        if not ok:
            rapor["erisilemeyen"].append(url)
            continue
        adaylar: list[tuple[str, str]] = []
        if tur == "kayak_pdf":
            adaylar = kayak_pdf(_metin_kaynak(url, ham))
        elif tur == "hsgm_pdf":
            adaylar = hsgm_kamu(_metin_kaynak(url, ham))
        elif tur == "dkmp_html":
            adaylar = dkmp_kis(ham)
        for il, isim in adaylar:
            rec = yeni_kayit(
                kategori=kategori,
                il=il,
                isim=isim,
                resmi_kaynak=url,
                today=today,
                kurum_turu=KURUM[kategori],
                kisa=KISA[kategori],
                tesis_sinifi="kamu" if kategori == "termal" else "",
            )
            _ekle(kayitlar, rec, rapor["eklenen"])

    for aday in kaynaklar.get("adaylar") or []:
        if not isinstance(aday, dict):
            continue
        url = http_url(aday.get("url") or "")
        isim = (aday.get("isim") or "").strip()
        il = (aday.get("il") or "").strip()
        anahtar = aday.get("anahtar") or [isim, il]
        if not url or not isim or not il:
            rapor["atlanan"].append(aday.get("id") or isim)
            continue
        if not resmi_alan_adi(url):
            rapor["atlanan"].append(aday.get("id") or url)
            continue
        ok, ham, _status = fetch(url)
        if not ok:
            rapor["erisilemeyen"].append(url)
            continue
        if not anahtarlar_var(_metin_kaynak(url, ham), list(anahtar)):
            rapor["atlanan"].append(aday.get("id") or isim)
            continue
        rec = yeni_kayit(
            kategori=kategori,
            il=il,
            isim=isim,
            resmi_kaynak=url,
            today=today,
            kurum_turu=aday.get("kurumTuru") or KURUM[kategori],
            kisa=aday.get("kisaAciklama") or KISA[kategori],
            tesis_sinifi="kamu" if kategori == "termal" else "",
            verilen_id=aday.get("id") or "",
        )
        _ekle(kayitlar, rec, rapor["eklenen"])

    gecersiz = [r for r in kayitlar if isinstance(r, dict) and dogrula(r, yeni=False)]
    kayitlar = [r for r in kayitlar if isinstance(r, dict) and not dogrula(r, yeni=False)]
    if gecersiz:
        rapor["atlanan"].extend(r.get("id", "?") for r in gecersiz)

    out = {
        "kategori": kategori,
        "sonTarama": today,
        "kayitlar": kayitlar,
    }
    if not _dry():
        save_json(path, out)
        save_json(DATA / "kis_kesfet.json", birlestir(today))
    save_json(REPORTS / f"{kategori}-{today}.json", rapor)
    return rapor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kategori", required=True, choices=sorted(KATEGORI_DOSYA))
    args = parser.parse_args()
    rapor = tara(args.kategori, date.today().isoformat())
    print(
        f"{rapor['kategori']}: dogrulanan={rapor['dogrulanan']} "
        f"eklenen={len(rapor['eklenen'])} erisilemeyen={len(rapor['erisilemeyen'])} "
        f"dry={_dry()}"
    )


if __name__ == "__main__":
    main()
