"""Mevcut uygulama JSON'unu kategori dosyalarına böler. Tarama değildir."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, KATEGORI_DOSYA, save_json  # noqa: E402
from merge import birlestir  # noqa: E402
from model import dogrula  # noqa: E402

APP_JSON = (
    Path(__file__).resolve().parents[2]
    / "rotalink_flutter"
    / "assets"
    / "data"
    / "kis_kesfet.json"
)


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else APP_JSON
    blob = json.loads(src.read_text(encoding="utf-8"))
    rows = blob.get("kayitlar") or []
    buckets = {k: [] for k in KATEGORI_DOSYA}
    for rec in rows:
        if not isinstance(rec, dict):
            continue
        kat = rec.get("kategori")
        if kat not in buckets:
            continue
        if dogrula(rec, yeni=False):
            continue
        buckets[kat].append(rec)
    today = date.today().isoformat()
    for kat, dosya in KATEGORI_DOSYA.items():
        save_json(
            DATA / dosya,
            {"kategori": kat, "sonTarama": today, "kayitlar": buckets[kat]},
        )
        print(kat, len(buckets[kat]))
    save_json(DATA / "kis_kesfet.json", birlestir(today))


if __name__ == "__main__":
    main()
