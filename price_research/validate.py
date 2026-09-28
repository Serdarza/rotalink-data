"""fiyatlar.json doğrulayıcı.

Kullanım: python price_research/validate.py [fiyatlar.json yolu]
Çıkış kodu 0 = geçerli, 1 = hata var.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARIFE_KEYS = {"baslik", "donem", "birim", "guncelleme", "dogrulama", "kategoriler", "tablolar", "kurallar",
               "giris_saati", "cikis_saati", "dahil", "indirimler", "ek_ucretler", "notlar"}
DOGRULAMA = {"resmi_kaynak", "tesis_dogruladi", "kullanici_bildirimi", "teyit_gerekli"}
OZET = ("fiyat_sivil", "fiyat_kamu_personeli", "fiyat_kurum_personeli")
URL_RE = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.I)


def validate_data(data: object, master_keys: set[tuple[str, str]] | None = None) -> list[str]:
    errs: list[str] = []
    if not isinstance(data, dict) or not isinstance(data.get("tesisler"), list):
        return ["kök nesne {'tesisler': [...]} biçiminde değil"]
    seen: set[tuple[str, str]] = set()
    for i, e in enumerate(data["tesisler"]):
        tag = f"#{i} {e.get('il')} / {e.get('isim')}" if isinstance(e, dict) else f"#{i}"
        if not isinstance(e, dict):
            errs.append(f"{tag}: kayıt nesne değil")
            continue
        il, isim = e.get("il"), e.get("isim")
        if not isinstance(il, str) or not il.strip() or not isinstance(isim, str) or not isim.strip():
            errs.append(f"{tag}: il/isim zorunlu")
            continue
        key = (il, isim)
        if key in seen:
            errs.append(f"{tag}: tekrar eden kayıt")
        seen.add(key)
        if master_keys is not None and key not in master_keys:
            errs.append(f"{tag}: master veritabanında yok (yanlış il/tesis)")
        for f in OZET:
            if f in e and e[f] is not None and not isinstance(e[f], str):
                errs.append(f"{tag}: {f} metin ya da null olmalı")
            if isinstance(e.get(f), str) and re.match(r"^-\s*\d", e[f].strip()):
                errs.append(f"{tag}: {f} negatif fiyat içeriyor")
        k = e.get("kaynak")
        if k not in (None, "") and (not isinstance(k, str) or not URL_RE.match(k)):
            errs.append(f"{tag}: kaynak URL bozuk: {k!r}")
        t = e.get("tarife")
        if t is None:
            continue
        if not isinstance(t, dict):
            errs.append(f"{tag}: tarife nesne değil")
            continue
        for kk in t:
            if kk not in TARIFE_KEYS:
                errs.append(f"{tag}: tarife içinde bilinmeyen alan: {kk}")
        if t.get("dogrulama") is not None and t["dogrulama"] not in DOGRULAMA:
            errs.append(f"{tag}: dogrulama değeri geçersiz: {t['dogrulama']}")
        cats = {c.get("id") for c in t.get("kategoriler") or [] if isinstance(c, dict)}
        tables = t.get("tablolar") or []
        if not isinstance(tables, list):
            errs.append(f"{tag}: tablolar liste değil")
            continue
        for tb in tables:
            tcats = cats | {c.get("id") for c in tb.get("kategoriler") or [] if isinstance(c, dict)}
            rows = tb.get("satirlar") or []
            dup_rows: set[str] = set()
            for r in rows:
                if not r.get("ad"):
                    errs.append(f"{tag}: satırda ad yok")
                sig = json.dumps([r.get("ad"), r.get("kisi"), r.get("fiyatlar")], ensure_ascii=False, sort_keys=True)
                if sig in dup_rows:
                    errs.append(f"{tag}: aynı tabloda tekrar eden fiyat satırı: {r.get('ad')}")
                dup_rows.add(sig)
                for cid, v in (r.get("fiyatlar") or {}).items():
                    if cid not in tcats:
                        errs.append(f"{tag}: kategori tanımsız: {cid}")
                    if isinstance(v, bool) or v is None:
                        errs.append(f"{tag}: boş/geçersiz fiyat ({r.get('ad')} / {cid})")
                    elif isinstance(v, (int, float)) and v <= 0:
                        errs.append(f"{tag}: sıfır/negatif fiyat ({r.get('ad')} / {cid}: {v})")
                    elif isinstance(v, str) and not v.strip():
                        errs.append(f"{tag}: boş fiyat metni ({r.get('ad')} / {cid})")
    return errs


def master_keys(root: Path = ROOT) -> set[tuple[str, str]]:
    m = json.loads((root / "master_database_updated.json").read_text(encoding="utf-8"))
    return {(t.get("il"), t.get("isim")) for t in m.get("tesisler", [])}


def validate_file(path: Path, root: Path = ROOT) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"JSON sözdizimi hatası: {e}"]
    return validate_data(data, master_keys(root))


def new_errors(before: list[str], after: list[str]) -> list[str]:
    """Güncellemenin eklediği hatalar (önceden var olan eski sorunlar hariç; kayıt sırası değişse de)."""
    strip = lambda s: re.sub(r"^#\d+ ", "", s)  # noqa: E731
    old = {strip(e) for e in before}
    return [e for e in after if strip(e) not in old]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=str(ROOT / "fiyatlar.json"))
    ap.add_argument("--write-baseline", help="mevcut hataları bu dosyaya yaz (güncelleme öncesi)")
    ap.add_argument("--baseline", help="yalnızca bu dosyada olmayan (yeni) hatalarda başarısız ol")
    a = ap.parse_args()
    path = Path(a.path)
    errs = validate_file(path)
    if a.write_baseline:
        Path(a.write_baseline).write_text(json.dumps(errs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{path.name}: {len(errs)} mevcut sorun temel olarak kaydedildi")
        return 0 if not any(e.startswith("JSON sözdizimi") for e in errs) else 1
    if a.baseline:
        base = json.loads(Path(a.baseline).read_text(encoding="utf-8"))
        known = len(errs)
        errs = new_errors(base, errs)
        print(f"bilinen eski sorun: {known - len(errs)}")
    for e in errs:
        print("HATA:", e)
    print(f"{path.name}: {'GEÇERLİ' if not errs else f'{len(errs)} hata'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
