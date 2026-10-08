"""İsteğe bağlı: sosyal_menuler.json'u bir Rotalink API'sine gönderir.

Uygulama veriyi doğrudan GitHub'daki JSON'dan okur; bu adım yalnız ROTALINK_API_URL ve
ROTALINK_API_KEY GitHub Secrets olarak tanımlıysa çalışır. Anahtar koda yazılmaz.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    url = os.environ.get("ROTALINK_API_URL", "").strip()
    key = os.environ.get("ROTALINK_API_KEY", "").strip()
    if not url or not key:
        print("ROTALINK_API_URL / ROTALINK_API_KEY tanımlı değil; API'ye gönderim atlandı.")
        return 0
    p = urlparse(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        print("ROTALINK_API_URL geçersiz (yalnız kimlik bilgisi içermeyen https adresi kabul edilir).")
        return 1
    body = (ROOT / "sosyal_menuler.json").read_bytes()
    r = requests.post(url, data=body, timeout=60,
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json; charset=utf-8"})
    print(f"API yanıtı: HTTP {r.status_code}")
    return 0 if r.ok else 1


if __name__ == "__main__":
    sys.exit(main())
