"""Resmî kamp kaynakları.

OGM (benimormanim.ogm.gov.tr): çadırlı kamp veya kampçılık sunan orman parkları;
konum, adres ve telefon parkın resmî sayfasından alınır.
KTB (ktb.gov.tr): Bakanlık belgeli kampingler; konum vermediği için yalnız mevcut
kayıtla eşleşirse "Bakanlık belgeli" işaretlenir, eşleşmeyen incelemeye düşer.
Bilinmeyen alan null kalır; fiyat yazılmaz.
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import date

from iller import ILLER, fold

OGM = "https://benimormanim.ogm.gov.tr"
OGM_ATIF = "Kaynak: T.C. Orman Genel Müdürlüğü (benimormanim.ogm.gov.tr)"
KTB_URL = "https://www.ktb.gov.tr/genel/searchhotelgenel.aspx"
UA = "RotalinkCampBot/1.0 (https://rotalink.tr)"
_DETAY_RE = re.compile(r'href="(/orman-parklari/[a-z0-9-]+-(\d+))"')
_KAMP_OZELLIK = "çadırlı kamp"
_KAMP_AKTIVITE = "kampçılık"
_GENEL = {"camping", "kamping", "camp", "kamp", "restaurant", "restoran", "alani",
          "tesisi", "tesisleri", "karavan", "park", "parki"}


def _tr_fold(s: str) -> str:
    return fold((s or "").replace("İ", "i").replace("I", "ı"))


_IL_BY_FOLD = {_tr_fold(ad): ad for ad, _ in ILLER}


def il_bul(raw: str) -> str | None:
    return _IL_BY_FOLD.get(_tr_fold(raw))


def fetch(url: str, timeout: int = 45) -> str:
    last = "bağlantı kurulamadı"
    for attempt in range(3):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                return res.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code not in (429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError) as e:
            last = type(e).__name__
        time.sleep((3, 10, 20)[attempt])
    raise RuntimeError(last)


def _temiz(s: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


def _bolum(doc: str, start_id: str) -> str:
    i = doc.find(f'id="{start_id}"')
    if i < 0:
        return ""
    j = doc.find('<h3 class="subtitle', i + 10)
    return doc[i:j if j > 0 else len(doc)]


def _maddeler(doc: str, start_id: str) -> list[str]:
    return [_temiz(x) for x in re.findall(r"<span>(.*?)</span>", _bolum(doc, start_id), flags=re.S)]


def _iletisim(doc: str, baslik: str) -> str | None:
    m = re.search(rf"<strong>\s*{baslik}\s*</strong>\s*<span>(.*?)</span>", doc, flags=re.S)
    s = _temiz(m.group(1)) if m else ""
    return s or None


def _telefon(raw: str | None) -> str | None:
    """Yalnız geçerli 10 haneli Türkiye numarası (sabit 2-4xx, mobil 5xx); hatalı girişler atılır."""
    if not raw or "_" in raw:
        return None
    d = re.sub(r"\D", "", raw).lstrip("0")
    if len(d) != 10 or d[0] not in "2345":
        return None
    return f"0{d[:3]} {d[3:6]} {d[6:8]} {d[8:]}"


def ogm_kayit(doc: str, url: str, park_id: str, today: date) -> dict | None:
    """OGM park sayfası → kamp kaydı. Kamp imkânı yoksa veya konum/il belirsizse None."""
    ozellik = [fold(x) for x in _maddeler(doc, "ozellikler")]
    aktivite = [fold(x) for x in _maddeler(doc, "aktiviteler")]
    cadirli = fold(_KAMP_OZELLIK) in ozellik
    if not cadirli and fold(_KAMP_AKTIVITE) not in aktivite:
        return None
    m = re.search(r"<h1>(.*?)</h1>", doc, flags=re.S)
    ad = _temiz(m.group(1)) if m else ""
    m = re.search(r"maps\.google\.com/maps\?q=(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", doc)
    if not ad or not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    if not (35.0 <= lat <= 43.0 and 25.0 <= lon <= 45.5):
        return None
    adres = _iletisim(doc, "Adres")
    if not adres or "/" not in adres:
        return None
    once, il_raw = adres.rsplit("/", 1)
    il = il_bul(il_raw)
    if not il:
        return None
    parca = once.replace("/", " ").split()
    son = parca[-1] if parca else ""
    ilce = son if son.isalpha() else None
    return {
        "id": f"ogm-{park_id}",
        "ad": ad,
        "il": il,
        "ilce": ilce,
        "adres": adres,
        "enlem": round(lat, 6),
        "boylam": round(lon, 6),
        "telefon": _telefon(_iletisim(doc, "Telefon")),
        "web": None,
        "kaynak_url": url,
        "kaynak_turu": "resmi",
        "atif": OGM_ATIF,
        "kamp_turu": "orman_parki",
        "cadir": True if cadirli else None,
        "karavan": None,
        "motokaravan": None,
        "elektrik": None,
        "tuvalet": None,
        "dus": None,
        "icme_suyu": None,
        "atik": None,
        "wifi": None,
        "otopark": True if "otopark" in ozellik else None,
        "denize_yakin": True if "sahil" in ozellik else None,
        "fiyat": None,
        "fiyat_birim": None,
        "ucret": "bilinmiyor",
        "rezervasyon": None,
        "son_kontrol": today.isoformat(),
        "dogrulama": "resmi",
        "durum": "aktif",
    }


def ogm_kamplari(today: date, deadline: float, get=fetch, bekle: float = 1.5) -> tuple[list[dict], bool]:
    """Dönen: kamp kayıtları ve taramanın eksiksiz bitip bitmediği."""
    sayfalar: dict[str, str] = {}
    for page in range(1, 60):
        if time.monotonic() > deadline:
            return [], False
        try:
            doc = get(f"{OGM}/orman-parklari?page={page}")
        except RuntimeError as e:
            print(f"hata: OGM liste {page}: {e}", flush=True)
            return [], False
        yeni = {path: pid for path, pid in _DETAY_RE.findall(doc) if path not in sayfalar}
        if not yeni:
            break
        sayfalar.update(yeni)
        time.sleep(bekle)
    out, eksik = [], False
    for path, pid in sayfalar.items():
        if time.monotonic() > deadline:
            eksik = True
            break
        try:
            doc = get(OGM + path)
        except RuntimeError as e:
            print(f"hata: OGM {path}: {e}", flush=True)
            eksik = True
            continue
        rec = ogm_kayit(doc, OGM + path, pid, today)
        if rec:
            out.append(rec)
        time.sleep(bekle)
    print(f"OGM: {len(sayfalar)} orman parkı, {len(out)} kamp", flush=True)
    return out, bool(sayfalar) and not eksik


def ktb_kampingler(doc: str) -> list[dict]:
    """KTB sayfasındaki gömülü tesis listesinden belgeli kampingler."""
    out = []
    for m in re.finditer(r"\{[^{}]*\"tesisTuru\":\"Kamping\"[^{}]*\}", doc):
        try:
            row = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if row.get("belgeDurumu") != "Belgeli Tesisler":
            continue
        il = il_bul(row.get("sehir") or "")
        ad = " ".join(str(row.get("tesisAdi") or "").split())
        if il and ad:
            out.append({"ad": ad, "il": il, "ilce": row.get("ilce"), "belge_no": str(row.get("belgeNo") or "")})
    return out


def _cekirdek(ad: str) -> set[str]:
    return {w for w in re.findall(r"\w+", _tr_fold(ad)) if len(w) > 2 and w not in _GENEL}


def ktb_esle(items: list[dict], belgeli: list[dict], today: date) -> tuple[int, list[dict]]:
    """Aynı ilde ayırt edici ad sözcüğü ortak olan aktif kayda belge no yazar."""
    eslesen, reviews = 0, []
    for b in belgeli:
        hedef = _cekirdek(b["ad"])
        if not hedef:
            continue
        aday = [r for r in items if r.get("durum") == "aktif" and r.get("il") == b["il"]
                and hedef & _cekirdek(r.get("ad") or "")]
        if len(aday) == 1:
            aday[0]["bakanlik_belge_no"] = b["belge_no"]
            eslesen += 1
        else:
            reviews.append({
                "tur": "ktb_konum_yok" if not aday else "ktb_belirsiz", "il": b["il"], "ad": b["ad"],
                "ilce": b.get("ilce"), "belge_no": b["belge_no"], "tarih": today.isoformat(),
                "detay": "Bakanlık belgeli kamping; konum kaynağı yok, eklenmedi.",
            })
    return eslesen, reviews
