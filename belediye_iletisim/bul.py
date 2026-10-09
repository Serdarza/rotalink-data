"""Sosyal tesislerin bağlı olduğu belediyelerin resmî e-posta adreslerini bulur.

Belediye adı tesis adından veya açıklamasından alınır ("X Belediyesi").
Alan adı yalnız resmî biçimlerden (*.bel.tr, ibb.istanbul) üretilir ve sayfa
başlığında belediye adı geçmesiyle doğrulanır. Yalnız kurumsal genel adresler
(bilgiedinme@, bilgi@, info@ …) alınır; kişisel ve KEP adresleri alınmaz.
Bulunamayan adres uydurulmaz; önceki kayıt korunur.

Ortam: DRY_RUN, ILETISIM_ONLY_IL, ILETISIM_TIME_BUDGET_MIN.
"""
from __future__ import annotations

import html
import json
import os
import re
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MASTER = ROOT / "master_database_updated.json"
OUT = HERE / "belediyeler.json"
UA = "Mozilla/5.0 (RotalinkBot/1.0; +https://rotalink.tr)"
DRY = os.environ.get("DRY_RUN", "").lower() in {"1", "true", "yes"}

_TR = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"})
_BEL_RE = re.compile(r"([A-ZÇĞİÖŞÜ][\wçğıöşüâîû]+(?:\s+Büyükşehir)?)\s+Belediyesi", re.U)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_GENEL = ("bilgiedinme", "bilgi.edinme", "bilgi_edinme", "bilgi", "info", "iletisim", "belediye",
          "halklailiskiler", "halkla.iliskiler", "beyazmasa", "beyaz.masa", "yazisleri", "yazi.isleri",
          "ozelkalem", "ozel.kalem", "destek", "basin")
_ILETISIM_YOLLARI = ("/iletisim", "/tr/iletisim", "/iletisim-bilgileri", "/bize-ulasin", "/iletisim.aspx")
_YASAK_ADLAR = {"Büyükşehir", "Büyüksehir", "Buyuksehir", "Bu", "Ilçe", "İlçe", "Il", "İl"}


def lower_tr(s: str) -> str:
    return (s or "").replace("İ", "i").replace("I", "ı").lower()


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", lower_tr(s).translate(_TR))


def belediye_adi(t: dict) -> str | None:
    """'Seyhan' veya 'Adana Büyükşehir'; bulunamazsa None (tahmin edilmez)."""
    isim = str(t.get("isim") or "")
    if re.match(r"(?i)^ibb\b|^İBB\b", isim.strip()):
        return "İstanbul Büyükşehir"
    for metin in (isim, str(t.get("aciklama") or "")):
        for m in _BEL_RE.finditer(metin):
            ad = " ".join(m.group(1).split())
            if ad.split()[0] not in _YASAK_ADLAR:
                return ad
    return None


def aday_alanlar(ad: str, il: str) -> list[str]:
    if ad == "İstanbul Büyükşehir":
        return ["ibb.istanbul"]
    kok = slug(ad.replace("Büyükşehir", ""))
    il_s = slug(il)
    if not kok:
        return []
    out = [f"{kok}.bel.tr"]
    if "Büyükşehir" not in ad and kok != il_s:
        out += [f"{kok}{il_s}.bel.tr", f"{kok}-{il_s}.bel.tr"]
    return out


def resmi_host(host: str) -> bool:
    h = (host or "").lower()
    return h.endswith(".bel.tr") or h == "ibb.istanbul" or h.endswith(".ibb.istanbul")


def fetch(url: str, timeout: int = 15) -> tuple[str, str] | None:
    """(son url, metin). Yalnız resmî alan adlarına gidilir."""
    p = urllib.parse.urlparse(url)
    if p.scheme not in {"http", "https"} or not resmi_host(p.hostname or ""):
        return None
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "tr"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            final = res.geturl()
            if not resmi_host(urllib.parse.urlparse(final).hostname or ""):
                return None
            raw = res.read(3_000_000)
            charset = res.headers.get_content_charset() or "utf-8"
            return final, raw.decode(charset, "replace")
    except (urllib.error.URLError, TimeoutError, ValueError, ConnectionError, OSError):
        return None


def _cf_decode(hexstr: str) -> str:
    try:
        key = int(hexstr[:2], 16)
        return "".join(chr(int(hexstr[i:i + 2], 16) ^ key) for i in range(2, len(hexstr), 2))
    except ValueError:
        return ""


def epostalar(doc: str) -> set[str]:
    metin = html.unescape(doc)
    found = set(_EMAIL_RE.findall(metin))
    for m in re.finditer(r'data-cfemail="([0-9a-fA-F]+)"', doc):
        found.add(_cf_decode(m.group(1)))
    metin2 = re.sub(r"\s*(\[at\]|\(at\)|\[et\])\s*", "@", metin, flags=re.I)
    found |= set(_EMAIL_RE.findall(metin2))
    return {e.strip(".").lower() for e in found if e}


def uygun_eposta(e: str, alan: str) -> bool:
    if not re.fullmatch(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", e):
        return False
    yerel, dom = e.split("@", 1)
    if "kep" in dom.split("."):
        return False
    kok = alan.split(".")[0]
    if not (dom == alan or dom.endswith("." + alan) or (dom.endswith(".bel.tr") and dom.split(".")[0] == kok)):
        return False
    if yerel in _GENEL or yerel in {kok, f"{kok}belediyesi", f"{kok}.belediyesi"}:
        return True
    # halkmasasi@, hilalmasa@, beyazmasa@, cozummasasi@ gibi başvuru masaları
    return "." not in yerel and "masa" in yerel


def en_iyi(adresler: set[str]) -> str | None:
    sira = {g: i for i, g in enumerate(_GENEL)}

    def puan(e: str) -> tuple[int, str]:
        yerel = e.split("@")[0]
        if yerel in sira:
            return (sira[yerel], e)
        return (50 if "masa" in yerel else 60, e)

    uygun = sorted(adresler, key=puan)
    return uygun[0] if uygun else None


def dogrula(doc: str, ad: str) -> bool:
    m = re.search(r"<title[^>]*>(.*?)</title>", doc, flags=re.S | re.I)
    baslik = slug(html.unescape(m.group(1))) if m else ""
    govde = slug(html.unescape(doc[:200_000]))
    kok = slug(ad.replace("Büyükşehir", ""))
    return bool(kok) and (kok in baslik or f"{kok}belediye" in govde)


def _cozulur(host: str) -> bool:
    try:
        socket.getaddrinfo(host, 443)
        return True
    except (socket.gaierror, UnicodeError, OSError):
        return False


def belediye_tara(ad: str, il: str, bekle: float = 1.0) -> dict | None:
    for alan in aday_alanlar(ad, il):
        ana = None
        hostlar = [h for h in (alan, f"www.{alan}") if _cozulur(h)]
        for url in [f"{s}://{h}/" for h in hostlar for s in ("https", "http")]:
            ana = fetch(url)
            if ana:
                break
        time.sleep(bekle)
        if not ana or not dogrula(ana[1], ad):
            continue
        final, doc = ana
        bulunan = {e for e in epostalar(doc) if uygun_eposta(e, alan)}
        kaynak = final
        if not bulunan:
            linkler = re.findall(r'href="([^"#]*iletisim[^"#]*)"', doc, flags=re.I)
            yollar = list(dict.fromkeys([*linkler[:3], *_ILETISIM_YOLLARI]))
            for yol in yollar:
                url = urllib.parse.urljoin(final, yol)
                if urllib.parse.urlparse(url).hostname != urllib.parse.urlparse(final).hostname:
                    continue
                sayfa = fetch(url)
                time.sleep(bekle)
                if not sayfa:
                    continue
                bulunan = {e for e in epostalar(sayfa[1]) if uygun_eposta(e, alan)}
                if bulunan:
                    kaynak = sayfa[0]
                    break
        return {"alan_adi": alan, "eposta": en_iyi(bulunan), "kaynak_url": kaynak}
    return None


def grupla(sosyal: list[dict], only: set[str] | None = None) -> dict[str, dict]:
    gruplar: dict[str, dict] = {}
    for t in sosyal:
        il = str(t.get("il") or "").strip()
        if only and slug(il) not in only:
            continue
        ad = belediye_adi(t)
        if not il or not ad:
            continue
        key = f"{slug(il)}:{slug(ad)}"
        g = gruplar.setdefault(key, {"belediye": f"{ad} Belediyesi", "ad": ad, "il": il, "tesisler": []})
        isim = " ".join(str(t.get("isim") or "").split())
        if isim and isim not in g["tesisler"]:
            g["tesisler"].append(isim)
    return gruplar


def main() -> int:
    today = date.today().isoformat()
    only = {slug(x) for x in os.environ.get("ILETISIM_ONLY_IL", "").split(",") if x.strip()} or None
    deadline = time.monotonic() + float(os.environ.get("ILETISIM_TIME_BUDGET_MIN", "100")) * 60
    sosyal = json.loads(MASTER.read_text(encoding="utf-8")).get("sosyal") or []
    onceki = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"items": {}}
    eski = onceki.get("items") or {}
    gruplar = grupla(sosyal, only)
    bulunan = bulunamayan = 0
    sonuc = {k: v for k, v in eski.items() if k in gruplar or (only and slug(v.get("il", "")) not in only)}

    def tara(item):
        key, g = item
        if time.monotonic() > deadline:
            return key, g, "zaman"
        return key, g, belediye_tara(g["ad"], g["il"])

    with ThreadPoolExecutor(max_workers=16) as pool:
        sonuclar = list(pool.map(tara, sorted(gruplar.items())))
    for key, g, bilgi in sonuclar:
        if bilgi == "zaman":
            continue
        rec = dict(eski.get(key) or {})
        rec.update({"belediye": g["belediye"], "il": g["il"], "tesisler": g["tesisler"]})
        if bilgi and bilgi["eposta"]:
            rec.update(bilgi)
            rec["son_kontrol"] = today
            bulunan += 1
        else:
            if bilgi:
                rec.setdefault("alan_adi", bilgi["alan_adi"])
            rec.setdefault("eposta", None)
            rec["son_deneme"] = today
            bulunamayan += 1
        sonuc[key] = rec
        print(f"{g['il']} / {g['belediye']}: {rec.get('eposta') or '-'}", flush=True)
    print(json.dumps({"belediye": len(gruplar), "eposta_bulunan": bulunan, "bulunamayan": bulunamayan},
                     ensure_ascii=False))
    if not DRY:
        OUT.write_text(json.dumps({
            "not": "Sosyal tesislerin bağlı olduğu belediyelerin resmî sitelerinde yayımlanan kurumsal "
                   "e-posta adresleri. Kişisel adres tutulmaz.",
            "guncelleme": today,
            "items": dict(sorted(sonuc.items())),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
