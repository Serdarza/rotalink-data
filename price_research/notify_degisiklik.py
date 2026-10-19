#!/usr/bin/env python3
"""Aylık fiyat tarama raporunda değişen misafirhane varsa e-posta gönderir.

Ortam: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, GONDEREN (isteğe bağlı),
PRICE_NOTIFY_TO (varsayılan: rotalinkinfo@gmail.com).
Değişiklik yoksa veya SMTP yoksa sessizce çıkar (exit 0).
"""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

PR = Path(__file__).resolve().parent
REPORTS = PR / "reports"
DEFAULT_TO = "rotalinkinfo@gmail.com"
ALERT_SONUCLAR = {"degisti", "suresi_doldu", "olasi_yeni_tarife", "celiski"}


def load_report() -> dict | None:
    for name in ("latest.json", "latest_dry_run.json"):
        p = REPORTS / name
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


def build_body(rep: dict) -> tuple[str, str] | None:
    degisen = [r for r in (rep.get("sonuclar") or []) if r.get("sonuc") in ALERT_SONUCLAR]
    degisiklikler = list(rep.get("degisiklikler") or [])
    if not degisen and not degisiklikler:
        return None

    canli = "CANLI" if rep.get("canli") else "DRY RUN"
    tarih = rep.get("tarih") or "?"
    subject = f"[Rotalink] Fiyat değişikliği uyarısı — {tarih} ({canli})"

    lines = [
        f"Aylık resmî fiyat taraması ({tarih}, {canli})",
        "",
        f"Fiyatı değişmiş / tarife süresi dolmuş / çelişkili / olası yeni tarife: {len(degisen)} tesis",
        f"İşlem günlüğü kaydı: {len(degisiklikler)}",
        "",
    ]
    if degisen:
        lines.append("=== Değişen / dikkat gereken tesisler ===")
        for r in degisen:
            lines.append(
                f"- [{r.get('sonuc')}] {r.get('il')} / {r.get('isim')}\n"
                f"  bulunmayan mevcut: {r.get('kaynakta_bulunmayan_mevcut_fiyatlar')}\n"
                f"  yeni aday: {(r.get('kaynaktaki_yeni_aday_rakamlar') or [])[:12]}\n"
                f"  kaynak: {r.get('kaynak')}"
            )
        lines.append("")
    if degisiklikler:
        lines.append("=== İşlem günlüğü ===")
        for x in degisiklikler:
            lines.append(
                f"- {x.get('tesis')} — {x.get('islem')}\n"
                f"  eski: {x.get('eski_fiyat')} | yeni: {x.get('yeni_fiyat')}\n"
                f"  kaynak: {x.get('resmi_kaynak')}"
            )
        lines.append("")
    lines.append("Detaylı rapor: GitHub Actions artefaktı (fiyat-raporu-*).")
    lines.append("Kaynak: price_research/reports/latest.json")
    return subject, "\n".join(lines) + "\n"


def send_mail(subject: str, body: str) -> int:
    smtp = {k: os.environ.get(k, "").strip() for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS")}
    gonderen = os.environ.get("GONDEREN", "").strip() or smtp["SMTP_USER"]
    alici = os.environ.get("PRICE_NOTIFY_TO", "").strip() or DEFAULT_TO
    eksik = [k for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS") if not smtp[k]]
    if eksik:
        print("Mail atılmadı; eksik secrets: " + ", ".join(eksik))
        return 0

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = gonderen
    msg["To"] = alici
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=gonderen.split("@")[-1] if "@" in gonderen else "localhost")
    msg.set_content(body)

    port = int(smtp["SMTP_PORT"] or "587")
    ctx = ssl.create_default_context()
    with smtplib.SMTP(smtp["SMTP_HOST"], port, timeout=60) as s:
        s.ehlo()
        if port != 465:
            s.starttls(context=ctx)
            s.ehlo()
        s.login(smtp["SMTP_USER"], smtp["SMTP_PASS"])
        s.send_message(msg)
    print(f"Bildirim maili gönderildi → {alici}")
    return 0


def main() -> int:
    rep = load_report()
    if not rep:
        print("Rapor yok; mail atılmadı.")
        return 0
    built = build_body(rep)
    if not built:
        print("Değişen fiyat yok; mail atılmadı.")
        return 0
    subject, body = built
    print(f"Uyarı hazır: {subject}")
    return send_mail(subject, body)


if __name__ == "__main__":
    raise SystemExit(main())
