"""Kış Keşfet kayıt doğrulama. Sahte/eksik kayıt yazılmaz."""
from __future__ import annotations

from common import http_url, resmi_alan_adi
from iller import fold, il_bul, slug

KAMU_KURUM = {
    "Belediye",
    "Üniversite",
    "Sağlık Bakanlığı",
    "Devlet hastanesi",
    "Köy",
    "Emniyet",
    "Vakıf",
}

OZEL_KELIME = ("özel tesis", "ozel tesis", "özel otel", "private")

ID_ON_EK = {
    "kayak": "kayak",
    "termal": "termal",
    "kisGezisi": "gezi",
}


def kayit_id(kategori: str, il: str, isim: str, verilen: str = "") -> str:
    if verilen.strip():
        return verilen.strip()
    return f"{ID_ON_EK[kategori]}-{slug(il)}-{slug(isim)}"[:80]


def ayni_yer(a: dict, b: dict) -> bool:
    if a.get("id") and a.get("id") == b.get("id"):
        return True
    return fold(a.get("il", "")) == fold(b.get("il", "")) and fold(a.get("isim", "")) == fold(
        b.get("isim", "")
    )


def kamu_termal(rec: dict) -> bool:
    if rec.get("tesisSinifi") == "ozel":
        return False
    kurum = (rec.get("kurumTuru") or "").strip()
    if kurum == "Özel tesis":
        return False
    blob = fold(" ".join([kurum, rec.get("isim", ""), rec.get("kisaAciklama", "")]))
    if any(fold(x) in blob for x in OZEL_KELIME):
        return False
    if rec.get("tesisSinifi") == "kamu":
        return True
    return kurum in KAMU_KURUM


def dogrula(rec: dict, yeni: bool) -> str | None:
    kategori = rec.get("kategori")
    if kategori not in ID_ON_EK:
        return "kategori"
    isim = (rec.get("isim") or "").strip()
    il = il_bul(rec.get("il") or "")
    kaynak = http_url(rec.get("resmiKaynak") or "")
    if not isim or il is None or kaynak is None:
        return "zorunlu"
    rec["isim"] = isim
    rec["il"] = il
    rec["resmiKaynak"] = kaynak
    if yeni and not resmi_alan_adi(kaynak):
        return "resmi_kaynak"
    if kategori == "termal" and not kamu_termal(rec):
        return "ozel_termal"
    return None


def yeni_kayit(
    *,
    kategori: str,
    il: str,
    isim: str,
    resmi_kaynak: str,
    today: str,
    kurum_turu: str,
    kisa: str,
    tesis_sinifi: str = "",
    verilen_id: str = "",
) -> dict | None:
    rec = {
        "id": kayit_id(kategori, il, isim, verilen_id),
        "kategori": kategori,
        "il": il,
        "ilce": "",
        "isim": isim,
        "kurumTuru": kurum_turu,
        "kisaAciklama": kisa,
        "adres": "",
        "telefon": "",
        "kullanimTuru": "Günübirlik",
        "resmiKaynak": resmi_kaynak,
        "sonDogrulama": today,
    }
    if tesis_sinifi:
        rec["tesisSinifi"] = tesis_sinifi
    if dogrula(rec, yeni=True):
        return None
    return rec
