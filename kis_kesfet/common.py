"""Nazik HTTP, resmî alan adı, metin temizliği. Fiyat/misafirhane yazılmaz."""
from __future__ import annotations

import html
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"
SOURCES = HERE / "sources"
REPORTS = HERE / "reports"
UA = "RotalinkWinterBot/1.0 (+https://github.com/Serdarza/rotalink-data)"

RESMI_UZANTILAR = (
    ".gov.tr", ".edu.tr", ".k12.tr", ".bel.tr", ".pol.tr",
    ".tsk.tr", ".mil.tr", ".gov.ct.tr", ".edu.ct.tr",
)
RESMI_EK = {
    "kamutesisleri.com",
}

KATEGORI_DOSYA = {
    "kayak": "kayak.json",
    "termal": "termal.json",
    "kisGezisi": "kis_gezisi.json",
}


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def resmi_alan_adi(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    if host.endswith(RESMI_UZANTILAR):
        return True
    return any(host == h or host.endswith("." + h) for h in RESMI_EK)


def http_url(raw: str) -> str | None:
    url = (raw or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    return url


def temiz_html(doc: str) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", doc or "")
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(html.unescape(text).split())


def fetch(url: str, timeout: int = 40) -> tuple[bool, str, int | None]:
    """(ok, text, status). PDF baytları da metne çevrilir."""
    last = "bağlantı kurulamadı"
    status = None
    for attempt in range(3):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        for ctx in (ssl.create_default_context(), ssl._create_unverified_context()):
            try:
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as res:
                    status = res.status
                    data = res.read()
                    ctype = (res.headers.get("Content-Type") or "").lower()
                    if "pdf" in ctype or url.lower().split("?")[0].endswith(".pdf"):
                        return True, _pdf_text(data), status
                    return True, data.decode("utf-8", "replace"), status
            except urllib.error.HTTPError as e:
                status = e.code
                last = f"HTTP {e.code}"
                if e.code not in {429, 500, 502, 503, 504}:
                    return False, last, status
                break
            except ssl.SSLError:
                continue
            except (urllib.error.URLError, TimeoutError) as e:
                last = type(e).__name__
                break
        time.sleep((3, 10, 20)[attempt])
    return False, last, status


def _pdf_text(content: bytes) -> str:
    try:
        import pymupdf
    except ImportError:
        return ""
    doc = pymupdf.open(stream=content, filetype="pdf")
    try:
        return "\n".join(page.get_text() or "" for page in doc)
    finally:
        doc.close()
