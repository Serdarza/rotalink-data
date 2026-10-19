#!/usr/bin/env python3
"""fiyatlar.json içindeki HTTP kaynak URL'lerini sources.json'a işler.

Yeni tesis kaydı yoksa master'dan oluşturur; varsa URL'yi kaynaklar listesine ekler.
Resmî uzantı dışı alan adlarını onayli_alan_adlari listesine ekler.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PR = ROOT / "price_research"
sys.path.insert(0, str(PR))
from common import RESMI_UZANTILAR, resmi_alan_adi  # noqa: E402

URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
FOLD = {
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
}


def fold(s: str) -> str:
    out = []
    for ch in unicodedata.normalize("NFD", s or ""):
        o = ord(ch)
        if 0x0300 <= o <= 0x036F:
            continue
        if ch in FOLD:
            out.append(FOLD[ch])
        elif ch != " ":
            out.append(ch.lower())
    return "".join(out)


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write_sources(path: Path, data: dict) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    path.write_text(text, encoding="utf-8")


def extract_urls(text: str) -> list[str]:
    found = []
    for m in URL_RE.finditer(text or ""):
        u = m.group(0).rstrip(".,;:)")
        if u not in found:
            found.append(u)
    return found


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def main() -> int:
    fiyat = load(ROOT / "fiyatlar.json")
    master = {fold(t["il"]) + "\0" + fold(t["isim"]): t for t in load(ROOT / "master_database_updated.json")["tesisler"]}
    reg = load(PR / "sources.json")
    by_key = {
        fold(t["il"]) + "\0" + fold(t["isim"]): t for t in reg["tesisler"]
    }
    onayli = set(reg.get("onayli_alan_adlari") or [])
    common_ek = set(onayli)

    added_tesis = 0
    added_url = 0
    activated = 0

    for entry in fiyat["tesisler"]:
        urls = extract_urls(str(entry.get("kaynak") or ""))
        if not urls:
            continue
        key = fold(entry["il"]) + "\0" + fold(entry["isim"])
        m = master.get(key)
        rec = by_key.get(key)
        if rec is None:
            rec = {
                "il": entry["il"],
                "isim": entry["isim"],
                "kurum": (m or {}).get("tip") or "",
                "telefon": (m or {}).get("telefon") or "",
                "durum": "B",
                "aktif": True,
                "kontrol_yontemi": "rakam_dogrulama",
                "kaynaklar": [],
                "ocr_eksik": [],
                "neden": None,
                "son_kontrol": None,
                "son_basarili_kontrol": None,
                "son_sonuc": None,
            }
            reg["tesisler"].append(rec)
            by_key[key] = rec
            added_tesis += 1
        else:
            if not rec.get("aktif"):
                rec["aktif"] = True
                activated += 1
            if rec.get("kontrol_yontemi") == "pasif":
                rec["kontrol_yontemi"] = "rakam_dogrulama"

        existing_urls = {s.get("url") for s in (rec.get("kaynaklar") or []) if s.get("url")}
        for url in urls:
            host = host_of(url)
            if host and not resmi_alan_adi(url, common_ek | onayli):
                if host.startswith("www."):
                    host = host[4:]
                if host and host not in onayli:
                    onayli.add(host)
                    common_ek.add(host)
            if url in existing_urls:
                continue
            rol = "fiyat"
            if any(ext in url.lower() for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
                rol = "fiyat_ek"
            elif url.rstrip("/").endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx")):
                rol = "fiyat"
            src = {
                "url": url,
                "tur": "gorsel" if rol == "fiyat_ek" else "web",
                "rol": rol,
                "alan_adi": host_of(url),
                "baslik": f"fiyatlar.json kaynağı — {entry['isim']}",
            }
            rec.setdefault("kaynaklar", []).append(src)
            existing_urls.add(url)
            added_url += 1

        # En az bir fiyat URL'si varsa neden alanını temizle
        if any(s.get("rol") in ("fiyat", "fiyat_ek") for s in rec.get("kaynaklar") or []):
            if rec.get("neden") and "bulunamadı" in str(rec.get("neden")).lower():
                rec["neden"] = None

    reg["onayli_alan_adlari"] = sorted(onayli)
    # İl + isim sıralı tut
    reg["tesisler"].sort(key=lambda t: (fold(t.get("il", "")), fold(t.get("isim", ""))))
    write_sources(PR / "sources.json", reg)
    print(
        f"sources güncellendi: yeni_tesis={added_tesis} yeni_url={added_url} "
        f"aktif_edilen={activated} onayli_alan={len(onayli)} toplam_tesis={len(reg['tesisler'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
