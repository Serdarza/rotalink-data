"""Rotalink hediye Pro kodları.

GitHub'daki `pro_kodlar.json` yalnızca kodların SHA-256 özetini tutar; kodların
kendisi depoya yazılmaz, `pro_kod/uretilen/` altına (git dışı) kaydedilir.

Örnekler:
  python pro_kod/kod_uret.py uret --plan aylik --adet 3
  python pro_kod/kod_uret.py uret --plan yillik --adet 1 --son 2027-01-31
  python pro_kod/kod_uret.py uret --plan aylik --kod YAZ2026 --kullanim 100
  python pro_kod/kod_uret.py iptal --kod RL-ABCD-EFGH-JKMN
  python pro_kod/kod_uret.py liste
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "pro_kodlar.json"
OUT_DIR = Path(__file__).resolve().parent / "uretilen"

ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
PLANS = ("aylik", "yillik")
SALT = "rotalink-pro-kod-v1:"
NOTE = (
    "Hediye Pro kodlarının SHA-256 özetleri. Kodların kendisi burada tutulmaz. "
    "Kod üretmek/iptal etmek için: python pro_kod/kod_uret.py --help"
)


def normalize(raw: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


def code_hash(raw: str) -> str:
    return hashlib.sha256((SALT + normalize(raw)).encode("utf-8")).hexdigest()


def new_code() -> str:
    body = "".join(secrets.choice(ALPHABET) for _ in range(12))
    return f"RL-{body[0:4]}-{body[4:8]}-{body[8:12]}"


def load() -> dict:
    if not DATA.exists():
        return {"surum": 1, "not": NOTE, "kodlar": []}
    data = json.loads(DATA.read_text(encoding="utf-8"))
    data.setdefault("kodlar", [])
    return data


def save(data: dict) -> None:
    data["not"] = NOTE
    data["kodlar"].sort(key=lambda k: (k.get("eklenme", ""), k["ozet"]))
    DATA.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def uret(
    plan: str,
    adet: int = 1,
    son: str | None = None,
    kullanim: int = 1,
    kod: str | None = None,
) -> tuple[list[str], str]:
    """Kodları üretip özetlerini `pro_kodlar.json`a ekler; (kodlar, son) döner."""
    if plan not in PLANS:
        raise ValueError("plan aylik veya yillik olmalı")
    if not 1 <= kullanim <= 1000:
        raise ValueError("kullanim 1-1000 arasında olmalı")
    today = dt.date.today()
    son = son or (today + dt.timedelta(days=365)).isoformat()
    try:
        son_date = dt.date.fromisoformat(son)
    except ValueError:
        raise ValueError("son tarihi YYYY-AA-GG biçiminde olmalı") from None
    if son_date < today:
        raise ValueError("son kullanma tarihi geçmiş olamaz")

    if kod:
        if len(normalize(kod)) < 6:
            raise ValueError("özel kod en az 6 harf/rakam olmalı")
        codes = [kod.strip().upper()]
    else:
        if not 1 <= adet <= 500:
            raise ValueError("adet 1-500 arasında olmalı")
        codes = [new_code() for _ in range(adet)]

    data = load()
    existing = {k["ozet"] for k in data["kodlar"]}
    added = []
    for code in codes:
        h = code_hash(code)
        if h in existing:
            print(f"zaten var, atlandı: {code}", file=sys.stderr)
            continue
        entry = {
            "ozet": h,
            "plan": plan,
            "son_kullanma": son,
            "eklenme": today.isoformat(),
        }
        if kullanim > 1:
            entry["kullanim"] = kullanim
        data["kodlar"].append(entry)
        existing.add(h)
        added.append(code)

    if not added:
        return [], son
    save(data)

    OUT_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = OUT_DIR / f"{stamp}-{plan}.txt"
    lines = [
        f"{plan_label(plan)} hediye Pro kodu — son kullanma {son}"
        + (f" — {kullanim} kullanım" if kullanim > 1 else ""),
        *added,
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return added, son


def plan_label(plan: str) -> str:
    return "Aylık" if plan == "aylik" else "Yıllık"


def cmd_uret(args: argparse.Namespace) -> int:
    try:
        added, son = uret(args.plan, args.adet, args.son, args.kullanim, args.kod)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if not added:
        return 1
    print(f"{plan_label(args.plan)} hediye Pro kodu — son kullanma {son}")
    print("\n".join(added))
    print(f"\nKodlar kaydedildi: {OUT_DIR.relative_to(ROOT)} (GitHub'a gönderilmez)")
    return 0


def cmd_iptal(args: argparse.Namespace) -> int:
    data = load()
    h = code_hash(args.kod)
    before = len(data["kodlar"])
    data["kodlar"] = [k for k in data["kodlar"] if k["ozet"] != h]
    if len(data["kodlar"]) == before:
        print("kod bulunamadı", file=sys.stderr)
        return 1
    save(data)
    print("kod iptal edildi (yeni kullanım kabul edilmez)")
    return 0


def cmd_liste(_: argparse.Namespace) -> int:
    data = load()
    today = dt.date.today().isoformat()
    for plan in PLANS:
        items = [k for k in data["kodlar"] if k["plan"] == plan]
        live = [k for k in items if k.get("son_kullanma", "9999") >= today]
        print(f"{plan}: {len(items)} kod ({len(live)} geçerli)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Rotalink hediye Pro kodları")
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("uret", help="yeni kod üret")
    u.add_argument("--plan", required=True, choices=PLANS)
    u.add_argument("--adet", type=int, default=1)
    u.add_argument("--son", help="son kullanma tarihi YYYY-AA-GG (varsayılan 1 yıl)")
    u.add_argument("--kod", help="rastgele yerine özel kod (ör. YAZ2026)")
    u.add_argument("--kullanim", type=int, default=1, help="kaç cihazda kullanılabilir")
    i = sub.add_parser("iptal", help="kodu iptal et")
    i.add_argument("--kod", required=True)
    sub.add_parser("liste", help="özet sayıları")
    args = ap.parse_args(argv)
    return {"uret": cmd_uret, "iptal": cmd_iptal, "liste": cmd_liste}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
