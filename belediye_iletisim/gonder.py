"""Belediyelere 4982 sayılı Kanun kapsamında sosyal tesis fiyat tarifesi başvurusu gönderir.

Her belediyeye 6 ayda en fazla bir başvuru; günlük gönderim sınırı vardır.
Kimlik ve SMTP bilgileri yalnız ortam değişkenlerinden (GitHub Secrets) okunur,
dosyaya yazılmaz. Alıcı yalnız resmî alan adındaki (*.bel.tr, ibb.istanbul) adrestir.

Ortam: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, GONDEREN,
BASVURU_AD, BASVURU_TC, BASVURU_ADRES, BASVURU_EPOSTA, BASVURU_TELEFON,
GUNLUK_LIMIT, DRY_RUN.
"""
from __future__ import annotations

import json
import os
import re
import smtplib
import ssl
import sys
import time
from datetime import date, timedelta
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

HERE = Path(__file__).resolve().parent
BELEDIYELER = HERE / "belediyeler.json"
KAYIT = HERE / "gonderim.json"
ARALIK = timedelta(days=175)
DRY = os.environ.get("DRY_RUN", "").lower() in {"1", "true", "yes"}
_ADRES_RE = re.compile(r"[a-z0-9._%+-]+@([a-z0-9-]+\.)*(bel\.tr|ibb\.istanbul)")


def gecerli_adres(e: str | None) -> bool:
    return bool(e) and _ADRES_RE.fullmatch(e) is not None


def temiz_satir(s: str) -> str:
    return " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", s or "").split())


def zamani_geldi(kayit: dict | None, bugun: date) -> bool:
    if not kayit or not kayit.get("son"):
        return True
    try:
        return bugun - date.fromisoformat(kayit["son"]) >= ARALIK
    except ValueError:
        return True


def metin(rec: dict, kimlik: dict) -> str:
    tesisler = "\n".join(f"  - {temiz_satir(t)}" for t in rec.get("tesisler") or [])
    satirlar = [
        f"Sayın {temiz_satir(rec['belediye'])} Başkanlığı,",
        "",
        "4982 sayılı Bilgi Edinme Hakkı Kanunu kapsamında, belediyenize ait aşağıdaki sosyal "
        "tesislerin güncel yiyecek-içecek ücret tarifesinin (meclis/encümen kararı veya fiyat "
        "listesi) tarafıma elektronik ortamda (PDF veya bağlantı) iletilmesini arz ederim.",
        "",
        tesisler,
        "",
        "Bilgiler, vatandaşların erişebilmesi amacıyla Rotalink uygulamasında belediyeniz kaynak "
        "gösterilerek yayımlanacaktır. Tarife resmî sitenizde yayımlanıyorsa bağlantısını "
        "iletmeniz yeterlidir.",
        "",
        "Gereğini bilgilerinize arz ederim.",
        "",
        f"Ad Soyad: {temiz_satir(kimlik['ad'])}",
    ]
    if kimlik.get("tc"):
        satirlar.append(f"T.C. Kimlik No: {temiz_satir(kimlik['tc'])}")
    satirlar.append(f"Adres: {temiz_satir(kimlik['adres'])}")
    if kimlik.get("telefon"):
        satirlar.append(f"Telefon: {temiz_satir(kimlik['telefon'])}")
    satirlar.append(f"E-posta: {temiz_satir(kimlik['eposta'])}")
    return "\n".join(satirlar) + "\n"


def mesaj(rec: dict, kimlik: dict, gonderen: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "Bilgi Edinme Başvurusu - Sosyal Tesis Ücret Tarifesi"
    msg["From"] = temiz_satir(gonderen)
    msg["To"] = rec["eposta"]
    msg["Reply-To"] = temiz_satir(kimlik["eposta"])
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=gonderen.split("@")[-1])
    msg.set_content(metin(rec, kimlik))
    return msg


def main() -> int:
    bugun = date.today()
    limit = int(os.environ.get("GUNLUK_LIMIT", "30"))
    smtp = {k: os.environ.get(k, "").strip() for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS")}
    kimlik = {
        "ad": os.environ.get("BASVURU_AD", "").strip(),
        "tc": os.environ.get("BASVURU_TC", "").strip(),
        "adres": os.environ.get("BASVURU_ADRES", "").strip(),
        "telefon": os.environ.get("BASVURU_TELEFON", "").strip(),
        "eposta": os.environ.get("BASVURU_EPOSTA", "").strip() or smtp["SMTP_USER"],
    }
    gonderen = os.environ.get("GONDEREN", "").strip() or smtp["SMTP_USER"]
    eksik = [k for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS") if not smtp[k]]
    eksik += [f"BASVURU_{k.upper()}" for k in ("ad", "adres") if not kimlik[k]]
    if eksik and not DRY:
        print("Gönderim yapılmadı; eksik GitHub Secrets: " + ", ".join(eksik))
        return 0
    if DRY and eksik:
        kimlik = {"ad": "Ad Soyad", "tc": "", "adres": "Adres", "telefon": "", "eposta": "ornek@ornek.com"}
        gonderen = "ornek@ornek.com"

    items = json.loads(BELEDIYELER.read_text(encoding="utf-8")).get("items") or {}
    kayit = json.loads(KAYIT.read_text(encoding="utf-8")) if KAYIT.exists() else {}
    sira = [(k, r) for k, r in sorted(items.items())
            if gecerli_adres(r.get("eposta")) and r.get("tesisler") and zamani_geldi(kayit.get(k), bugun)]
    print(f"Sırada {len(sira)} belediye; bugün en fazla {limit}.")
    gonderilen = 0
    sunucu = None
    try:
        for key, rec in sira[:limit]:
            msg = mesaj(rec, kimlik, gonderen)
            if DRY:
                if gonderilen == 0:
                    print(msg.as_string()[:1500])
                print(f"[DRY] {rec['belediye']} <{rec['eposta']}>")
            else:
                if sunucu is None:
                    port = int(smtp["SMTP_PORT"] or 587)
                    ctx = ssl.create_default_context()
                    if port == 465:
                        sunucu = smtplib.SMTP_SSL(smtp["SMTP_HOST"], port, context=ctx, timeout=60)
                    else:
                        sunucu = smtplib.SMTP(smtp["SMTP_HOST"], port, timeout=60)
                        sunucu.starttls(context=ctx)
                    sunucu.login(smtp["SMTP_USER"], smtp["SMTP_PASS"])
                try:
                    sunucu.send_message(msg)
                except smtplib.SMTPRecipientsRefused:
                    kayit[key] = {"son": bugun.isoformat(), "eposta": rec["eposta"], "durum": "adres_reddedildi"}
                    print(f"Adres reddedildi: {rec['belediye']} <{rec['eposta']}>")
                    continue
                kayit[key] = {"son": bugun.isoformat(), "eposta": rec["eposta"], "durum": "gonderildi",
                              "message_id": msg["Message-ID"]}
                print(f"Gönderildi: {rec['belediye']} <{rec['eposta']}>")
                time.sleep(20)
            gonderilen += 1
    finally:
        if sunucu is not None:
            try:
                sunucu.quit()
            except smtplib.SMTPException:
                pass
        if not DRY:
            KAYIT.write_text(json.dumps(dict(sorted(kayit.items())), ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    print(f"Bu çalışmada {gonderilen} başvuru {'(DRY)' if DRY else 'gönderildi'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
