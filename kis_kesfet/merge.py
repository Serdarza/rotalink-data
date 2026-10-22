"""Üç kategori dosyasını yayınlanan kis_kesfet.json dosyasında birleştirir."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, KATEGORI_DOSYA, load_json, save_json
from model import dogrula

SIRALAMA = ("kayak", "kisGezisi", "termal")


def birlestir(today: str | None = None) -> dict:
    kayitlar = []
    seen: set[str] = set()
    for kategori in SIRALAMA:
        path = DATA / KATEGORI_DOSYA[kategori]
        blob = load_json(path, {"kayitlar": []})
        rows = blob.get("kayitlar") if isinstance(blob, dict) else blob
        if not isinstance(rows, list):
            continue
        for rec in rows:
            if not isinstance(rec, dict):
                continue
            if rec.get("kategori") != kategori:
                continue
            if dogrula(rec, yeni=False):
                continue
            kid = rec.get("id") or ""
            if kid in seen:
                continue
            seen.add(kid)
            kayitlar.append(rec)
    return {
        "aciklama": (
            "Kış Keşfet yayın dosyası. Kayak, termal ve kış rotası taramaları "
            "ayrı GitHub Actions ile aylık güncellenir. Ana misafirhane ve fiyat "
            "verisine dokunulmaz."
        ),
        "sonBirlestirme": today or date.today().isoformat(),
        "kayitlar": kayitlar,
    }


def main() -> None:
    out = birlestir()
    save_json(DATA / "kis_kesfet.json", out)
    print(f"birlesti {len(out['kayitlar'])} kayit")


if __name__ == "__main__":
    main()
