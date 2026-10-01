"""bildirimler.json doğrulayıcı. Hata varsa 1 ile çıkar."""

import datetime as dt
import json
import re
import sys
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "bildirimler.json"
EKRANLAR = {"", "kampanyalar", "tatiller", "pro"}
MAX_BASLIK = 50
MAX_METIN = 150
SAAT_RE = re.compile(r"^(\d{1,2})[:.](\d{2})$")


def saat_gecerli(v):
    m = SAAT_RE.match(v) if isinstance(v, str) else None
    return bool(m) and int(m[1]) <= 23 and int(m[2]) <= 59


def main():
    hatalar, uyarilar = [], []
    try:
        root = json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"HATA: bildirimler.json okunamadı: {e}")
        return 1

    if not isinstance(root, dict) or not isinstance(root.get("mesajlar"), list):
        print('HATA: kökte "mesajlar" listesi olmalı')
        return 1
    if "saat" in root and not saat_gecerli(root["saat"]):
        hatalar.append(f'genel saat geçersiz: {root["saat"]!r} (örnek "21:00")')

    haftalar = {}
    for i, m in enumerate(root["mesajlar"], start=1):
        etiket = f"mesaj {i}"
        if not isinstance(m, dict):
            hatalar.append(f"{etiket}: nesne olmalı")
            continue
        tarih = m.get("tarih")
        try:
            gun = dt.date.fromisoformat(tarih) if isinstance(tarih, str) and len(tarih) == 10 else None
        except ValueError:
            gun = None
        if gun is None:
            hatalar.append(f"{etiket}: tarih YYYY-AA-GG olmalı, gelen {tarih!r}")
        else:
            etiket = f"mesaj {i} ({tarih})"
        for alan, sinir in (("baslik", MAX_BASLIK), ("metin", MAX_METIN)):
            v = m.get(alan)
            if not isinstance(v, str) or not v.strip():
                hatalar.append(f"{etiket}: {alan} boş olamaz")
            elif len(v.strip()) > sinir:
                hatalar.append(f"{etiket}: {alan} {len(v.strip())} karakter, en fazla {sinir}")
        if "saat" in m and not saat_gecerli(m["saat"]):
            hatalar.append(f"{etiket}: saat geçersiz: {m['saat']!r}")
        ekran = m.get("ekran", "")
        if not isinstance(ekran, str) or ekran.strip().lower() not in EKRANLAR:
            hatalar.append(f"{etiket}: ekran {ekran!r} geçersiz; kampanyalar, tatiller, pro veya boş")
        if "aktif" in m and not isinstance(m["aktif"], bool):
            hatalar.append(f"{etiket}: aktif true/false olmalı")
        if gun is not None and m.get("aktif", True) is not False:
            if gun.weekday() != 3:
                uyarilar.append(f"{etiket}: Perşembe değil")
            hafta = gun - dt.timedelta(days=gun.weekday())
            if hafta in haftalar:
                uyarilar.append(f"{etiket}: {haftalar[hafta]} ile aynı hafta, gönderilmeyecek")
            else:
                haftalar[hafta] = etiket

    for u in uyarilar:
        print(f"UYARI: {u}")
    for h in hatalar:
        print(f"HATA: {h}")
    if hatalar:
        return 1
    print(f"bildirimler.json geçerli: {len(root['mesajlar'])} mesaj")
    return 0


if __name__ == "__main__":
    sys.exit(main())
