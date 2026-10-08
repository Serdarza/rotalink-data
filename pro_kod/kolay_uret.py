"""Soru sorarak hediye Pro kodu üretir, GitHub'a gönderir ve not dosyasına yazar.

Masaüstündeki `Rotalink_Kod_Uret.bat` bu dosyayı çalıştırır.
"""

from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kod_uret  # noqa: E402

REPO = kod_uret.ROOT
NOTES = REPO.parent / "Rotalink_Hediye_Kodlari.txt"


def git(*args: str) -> bool:
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        print((r.stderr or r.stdout).strip())
    return r.returncode == 0


def ask_plan() -> str:
    while True:
        a = input("Hangi kod?  1 = Aylık (30 gün)   2 = Yıllık (365 gün)  : ").strip()
        if a == "1":
            return "aylik"
        if a == "2":
            return "yillik"
        print("Lütfen 1 veya 2 yazın.")


def ask_count() -> int:
    while True:
        a = input("Kaç tane? (1-100)  : ").strip()
        if a.isdigit() and 1 <= int(a) <= 100:
            return int(a)
        print("Lütfen 1 ile 100 arasında bir sayı yazın.")


def append_notes(plan: str, codes: list[str], son: str, note: str) -> None:
    today = dt.date.today().strftime("%d.%m.%Y")
    days = "365 gün" if plan == "yillik" else "30 gün"
    header = f"{kod_uret.plan_label(plan).upper()} ({days} Pro) — {len(codes)} adet — üretim {today} — son giriş {son}"
    if note:
        header += f" — {note}"
    lines = ["", header, *[f"{c}   Verildi: " for c in codes]]
    if not NOTES.exists():
        lines = ["ROTALINK HEDİYE PRO KODLARI", "===========================", *lines]
    with NOTES.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def push(plan: str, count: int) -> bool:
    msg = f"feat: {count} {kod_uret.plan_label(plan).lower()} hediye Pro kodu (özet)"
    if not git("commit", "-q", "-m", msg, "--", "pro_kodlar.json"):
        return False
    for _ in range(2):
        if git("push", "-q"):
            return True
        git("pull", "--rebase", "-q", "--autostash")
    return False


def main() -> int:
    print("ROTALINK HEDİYE PRO KODU ÜRET\n")
    print("GitHub'dan son durum alınıyor…")
    if not git("pull", "--rebase", "-q", "--autostash"):
        print("\nGitHub'a bağlanılamadı. İnterneti kontrol edip tekrar deneyin.")
        return 1

    plan = ask_plan()
    count = ask_count()
    note = input("Not (kampanya adı vb., boş bırakabilirsiniz)  : ").strip()

    try:
        codes, son = kod_uret.uret(plan, count)
    except ValueError as e:
        print(f"\nKod üretilemedi: {e}")
        return 1
    append_notes(plan, codes, son, note)

    print(f"\n{kod_uret.plan_label(plan)} kodlar (son giriş {son}):")
    print("\n".join(codes))
    print(f"\nKodlar not dosyasına eklendi: {NOTES}")

    print("\nGitHub'a gönderiliyor…")
    if push(plan, count):
        print("Tamam. Kodlar yaklaşık 5 dakika içinde uygulamada çalışır.")
        return 0
    print(
        "\nUYARI: Kodlar GitHub'a gönderilemedi, şu an uygulamada ÇALIŞMAZ.\n"
        "İnterneti kontrol edip bu aracı tekrar açın; kodlar dosyada duruyor,\n"
        "yeniden açınca otomatik gönderilir."
    )
    return 1


def resend_pending() -> None:
    """Önceki çalıştırmada gönderilemeyen kodları gönderir."""
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", "pro_kodlar.json"],
        cwd=REPO, capture_output=True, text=True,
    ).stdout.strip()
    ahead = subprocess.run(
        ["git", "rev-list", "--count", "@{u}..HEAD"],
        cwd=REPO, capture_output=True, text=True,
    ).stdout.strip()
    if status:
        git("commit", "-q", "-m", "feat: hediye Pro kodu (özet)", "--", "pro_kodlar.json")
    if status or (ahead.isdigit() and int(ahead) > 0):
        print("Önceden gönderilemeyen kodlar gönderiliyor…")
        if git("push", "-q") or (git("pull", "--rebase", "-q", "--autostash") and git("push", "-q")):
            print("Gönderildi.\n")


if __name__ == "__main__":
    resend_pending()
    code = main()
    input("\nKapatmak için Enter'a basın…")
    sys.exit(code)
