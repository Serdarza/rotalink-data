"""Resmî katalog metninden aday çıkarımı. Sayfada olmayan yer uydurulmaz."""
from __future__ import annotations

import html
import re

from common import temiz_html
from iller import fold, il_bul

KAYAK_IMZA = (
    ("kartepe", "Kocaeli", "Kartepe Kayak Merkezi"),
    ("zigana", "Gümüşhane", "Zigana Kayak Merkezi"),
    ("ergan", "Erzincan", "Ergan Kayak Merkezi"),
    ("yedikuyular", "Kahramanmaraş", "Yedikuyular Kayak Merkezi"),
    ("bozdag", "İzmir", "Bozdağ Kayak Merkezi"),
    ("cambasi", "Ordu", "Çambaşı Kayak Merkezi"),
    ("elmadag", "Ankara", "Elmadağ Kayak Merkezi"),
    ("keltepe", "Kocaeli", "Keltepe Kayak Merkezi"),
    ("ladik", "Samsun", "Ladik Akdağ Kayak Merkezi"),
)

KIS_IMZA = (
    "uludag",
    "ilgaz",
    "allahuekber",
    "agri dagi",
    "kackar",
    "nene hatun",
    "yedigoller",
    "abant",
    "aladaglar",
    "munzur",
    "kop dagi",
    "karagol",
    "altindere",
    "cilo",
    "honaz",
    "kizildag",
    "spil dagi",
    "kazdagi",
)

KAMU_ISLETME = (
    "belediye",
    "universite",
    "valiligi",
    "il ozel",
    "saglik bakanligi",
    "koy tuze",
    "emniyet",
)


def anahtarlar_var(metin: str, anahtarlar: list[str]) -> bool:
    blob = fold(metin)
    return all(fold(k) in blob for k in anahtarlar if k.strip())


def kayak_pdf(metin: str) -> list[tuple[str, str]]:
    """PDF'te geçen imza merkezleri (il, isim). Metinde yoksa eklenmez."""
    blob = fold(metin)
    out = []
    for imza, il, isim in KAYAK_IMZA:
        if imza in blob and fold(il) in blob:
            out.append((il, isim))
    return out


def hsgm_kamu(metin: str) -> list[tuple[str, str]]:
    """Lisans listesinden kamu/belediye kaplıcası. Özel satır atılır."""
    out = []
    seen: set[tuple[str, str]] = set()
    for raw in metin.splitlines():
        line = " ".join(raw.split())
        if len(line) < 8:
            continue
        blob = fold(line)
        if "ozel" in blob and "belediye" not in blob and "universite" not in blob:
            continue
        if not any(k in blob for k in KAMU_ISLETME):
            continue
        if not any(k in blob for k in ("kaplica", "ilica", "termal", "icmece")):
            continue
        il = il_bul(line)
        if not il:
            continue
        isim = _hsgm_ad(line, il)
        if not isim:
            continue
        key = (fold(il), fold(isim))
        if key in seen:
            continue
        seen.add(key)
        out.append((il, isim))
    return out


def _hsgm_ad(line: str, il: str) -> str | None:
    cleaned = re.sub(rf"\b{re.escape(il)}\b", " ", line, flags=re.I)
    cleaned = " ".join(cleaned.split())
    m = re.search(
        r"([A-ZÇĞİÖŞÜa-zçğıöşüİıâîû0-9'’.\- ]{4,60}(?:Kaplıcası|Kaplıca|Ilıcası|Ilıca|Termal|İçmecesi|İçmece))",
        cleaned,
    )
    if not m:
        return None
    ad = " ".join(m.group(1).split())
    ad = re.sub(
        r"^.+?(?:Belediyesi|Üniversitesi|Valiliği|Hastanesi)\s+",
        "",
        ad,
        flags=re.I,
    )
    if len(ad) < 6:
        return None
    return ad


def dkmp_kis(html_doc: str) -> list[tuple[str, str]]:
    """DKMP milli park tablosundan kış rotasına uygun dağ/göl parkları."""
    doc = html.unescape(html_doc or "").replace("&#58;", ":")
    rows = re.findall(
        r"<tr[^>]*>.*?</tr>",
        doc,
        flags=re.I | re.S,
    )
    out = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)
        if len(cells) < 3:
            continue
        il_raw = " ".join(re.sub(r"<[^>]+>", " ", cells[1]).split())
        ad = " ".join(re.sub(r"<[^>]+>", " ", cells[2]).split())
        il = il_bul(il_raw.split("-")[0] if il_raw else "")
        if not il or not ad:
            continue
        if not _kis_park(ad):
            continue
        key = (fold(il), fold(ad))
        if key in seen:
            continue
        seen.add(key)
        out.append((il, ad if "milli park" in fold(ad) else f"{ad} Milli Parkı"))
    return out


def _kis_park(ad: str) -> bool:
    blob = fold(ad)
    if any(x in blob for x in ("sahil", "deniz", "longoz", "kuscenneti", "magara", "kanyon")):
        return False
    return any(imza in blob for imza in KIS_IMZA)


def html_kayak_adi(html_doc: str) -> bool:
    return "kayak" in fold(temiz_html(html_doc))
