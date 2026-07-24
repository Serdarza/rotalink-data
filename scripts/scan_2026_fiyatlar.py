#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotalink 2026 konaklama fiyat tarayıcı.

Yalnızca resmi sayfalarda (özellikle *.pol.tr) bulunan 2026 fiyat tablolarını
çıkarır. Tahmin / ortalama / uydurma fiyat YAZMAZ.
Kaynak bulunamayan tesisler fiyatlar.json'a eklenmez.
"""

from __future__ import annotations

import json
import re
import sys
import time
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
MASTER_CANDIDATES = [
    Path(r"C:\Users\Kartal\Desktop\Rotalink_Merkez\Rotalink_Web\rotalink-app\data\master_database.json"),
    ROOT.parent / "Rotalink_Web" / "rotalink-app" / "data" / "master_database.json",
    ROOT / "master_database.json",
]
FIYATLAR_PATH = ROOT / "fiyatlar.json"
REPORT_PATH = ROOT / "scripts" / "scan_2026_report.json"
PROGRESS_PATH = ROOT / "scripts" / "scan_2026_progress.json"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 RotalinkPriceScanner/1.0"
)
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    }
)
TIMEOUT = 18
MAX_WORKERS = 8

# İl adı -> pol.tr slug (özel durumlar)
IL_SLUG_OVERRIDE = {
    "Afyonkarahisar": "afyon",
    "Kahramanmaraş": "kahramanmaras",
    "Şanlıurfa": "sanliurfa",
    "Şırnak": "sirnak",
    "İstanbul": "istanbul",
    "İzmir": "izmir",
    "Çanakkale": "canakkale",
    "Çankırı": "cankiri",
    "Çorum": "corum",
    "Iğdır": "igdir",
    "Kilis": "kilis",
    "Osmaniye": "osmaniye",
    "Düzce": "duzce",
    "Gümüşhane": "gumushane",
    "Ağrı": "agri",
    "Muş": "mus",
    "Uşak": "usak",
    "Elazığ": "elazig",
    "Muğla": "mugla",
    "Nevşehir": "nevsehir",
    "Niğde": "nigde",
    "Tekirdağ": "tekirdag",
    "Kırklareli": "kirklareli",
    "Kırıkkale": "kirikkale",
    "Kırşehir": "kirsehir",
    "Balıkesir": "balikesir",
    "Eskişehir": "eskisehir",
    "Kütahya": "kutahya",
    "Kocaeli": "kocaeli",
    "Sakarya": "sakarya",
    "Hatay": "hatay",
    "Adıyaman": "adiyaman",
    "Diyarbakır": "diyarbakir",
}

TR_MAP = str.maketrans(
    {
        "ç": "c",
        "Ç": "c",
        "ğ": "g",
        "Ğ": "g",
        "ı": "i",
        "İ": "i",
        "I": "i",
        "ö": "o",
        "Ö": "o",
        "ş": "s",
        "Ş": "s",
        "ü": "u",
        "Ü": "u",
    }
)

MONEY_RE = re.compile(
    r"(?:₺|TL)?\s*(\d{1,3}(?:[.\s]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s*(?:₺|TL)?",
    re.I,
)
YEAR_2026_RE = re.compile(r"2026")
POLISEVI_HINT = re.compile(r"polis\s*evi|polisevi|konaklama\s*fiyat|oda\s*(ve\s*)?yatak", re.I)
ROLE_HINTS = {
    "kurum": re.compile(
        r"te[şs]kilat|emniyet\s*mensub|%?\s*30\s*indirim",
        re.I,
    ),
    "kamu": re.compile(
        r"kamu\s*(personel|mensub)|konaklama\s*[üu]cret[iı]?",
        re.I,
    ),
    "sivil": re.compile(
        r"onayl[ıi]\s*misafir|yabanc[ıi]\s*(misafir|konuk)|onayl[ıi]\s*veya",
        re.I,
    ),
}
# 2026 gecelik oda için makul alt sınır (çamaşır/ütü vb. elensin)
MIN_ROOM_PRICE = 400.0
MAX_ROOM_PRICE = 25000.0


def slug_il(il: str) -> str:
    if il in IL_SLUG_OVERRIDE:
        return IL_SLUG_OVERRIDE[il]
    return il.translate(TR_MAP).lower().replace(" ", "")


def normalize_name(s: str) -> str:
    s = (s or "").casefold().translate(TR_MAP)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def parse_money_tr(token: str) -> float | None:
    raw = token.strip()
    if not raw:
        return None
    raw = raw.replace("₺", "").replace("TL", "").replace("tl", "").strip()
    raw = raw.replace("\xa0", "").replace(" ", "")
    # 1.234,56 or 1,234.56 or 1234,56 or 1234.00
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", raw):
        raw = raw.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", raw):
        raw = raw.replace(",", "")
    elif "," in raw and "." in raw:
        # last separator is decimal
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        parts = raw.split(",")
        if len(parts[-1]) <= 2:
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    try:
        val = float(raw)
    except ValueError:
        return None
    if val < 1 or val > 100_000:
        return None
    return val


def format_tl(v: float) -> str:
    n = int(round(v))
    return f"{n:,}".replace(",", ".")


def format_range(vals: list[float]) -> str | None:
    if not vals:
        return None
    lo, hi = min(vals), max(vals)
    if abs(lo - hi) < 0.5:
        return f"{format_tl(lo)} TL"
    return f"{format_tl(lo)} – {format_tl(hi)} TL"


def fetch(url: str) -> tuple[str | None, str | None]:
    try:
        r = SESSION.get(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}"
        ctype = (r.headers.get("content-type") or "").lower()
        if "html" not in ctype and "text" not in ctype and "xml" not in ctype:
            return None, f"skip content-type {ctype}"
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text, None
    except Exception as e:
        return None, str(e)


def candidate_pol_urls(il: str) -> list[str]:
    slug = slug_il(il)
    bases = [f"https://www.{slug}.pol.tr", f"https://{slug}.pol.tr"]
    paths = [
        "/polisevi",
        "/polis-evi",
        "/polisevi-sube-mudurlugu",
        "/polis-evi-sube-mudurlugu",
        "/polisevi-sube-mudurlugu-fiyat-listesi",
        f"/{slug}-polisevi-2026-yili-fiyat-listesi",
        f"/{slug}-polisevi",
        f"/{slug}-polis-evi",
        "/gaziantep-pol-evi",
        "/konaklama-fiyat-listesi",
        "/fiyat-listesi",
    ]
    urls: list[str] = []
    for b in bases:
        for p in paths:
            urls.append(b + p)
    # dedupe preserve order
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def extract_links(html: str, base: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = " ".join(a.stripped_strings)
        full = urljoin(base, href)
        blob = f"{href} {text}".lower()
        if any(
            k in blob
            for k in (
                "polisevi",
                "polis-evi",
                "polis evi",
                "fiyat",
                "konaklama",
                "2026",
            )
        ):
            if urlparse(full).netloc.endswith("pol.tr"):
                links.append(full.split("#")[0])
    # unique
    seen = set()
    out = []
    for u in links:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:40]


def detect_columns(header_cells: list[str]) -> dict[str, int] | None:
    mapping: dict[str, int] = {}
    for i, h in enumerate(header_cells):
        hnorm = h.strip()
        if not hnorm:
            continue
        # sivil önce (daha spesifik); sonra kurum; kamu "konaklama ücreti"
        for role in ("sivil", "kurum", "kamu"):
            if ROLE_HINTS[role].search(hnorm) and role not in mapping:
                mapping[role] = i
    # teşkilat + onaylı misafir zorunlu (yanlış tablo riskini düşürür)
    if "kurum" in mapping and "sivil" in mapping:
        return mapping
    return None


def moneys_in_cell(text: str) -> list[float]:
    vals = []
    for m in MONEY_RE.finditer(text.replace("\xa0", " ")):
        v = parse_money_tr(m.group(1))
        if v is not None:
            vals.append(v)
    return vals


def parse_stacked_room_prices(text_all: str, url: str) -> dict[str, Any] | None:
    """
    Tablo olmayan sayfalar: oda tipi satırı + 3 fiyat (teşkilat / kamu / onaylı).
    Yalnızca 2026 + rol anahtarları varsa ve tutarlar makulse kabul edilir.
    """
    if not YEAR_2026_RE.search(text_all):
        return None
    if not ROLE_HINTS["kurum"].search(text_all):
        return None
    if not ROLE_HINTS["sivil"].search(text_all) and not re.search(
        r"onayl[ıi]|misafir", text_all, re.I
    ):
        return None

    # satırlara böl (get_text tek satır olabilir) — para birimlerinden de ayır
    rough = re.sub(r"(?<=\d)\s*TL\b", " TL\n", text_all, flags=re.I)
    rough = re.sub(r"(?<=\d)\s*₺", " ₺\n", rough)
    lines = [ln.strip() for ln in re.split(r"[\n\r]+", rough) if ln.strip()]
    # eğer çok az satır varsa kelime bloklarını dene
    if len(lines) < 8:
        lines = [ln.strip() for ln in re.split(r"\s{2,}|\n", text_all) if ln.strip()]

    buckets: dict[str, list[float]] = {"kurum": [], "kamu": [], "sivil": []}
    room_rx = re.compile(r"oda|yatak|suit|süit|su[iı]t|vip|aile|double|m[uü]stakil", re.I)
    skip_rx = re.compile(r"ek yatak|çamaşır|camasir|[uü]t[uü]|oda kart|kahvalt", re.I)

    i = 0
    while i < len(lines):
        line = lines[i]
        if skip_rx.search(line):
            i += 1
            continue
        if room_rx.search(line) and not moneys_in_cell(line):
            # sonraki 3 satırda fiyat ara
            vals = []
            j = i + 1
            while j < len(lines) and len(vals) < 3:
                ms = moneys_in_cell(lines[j])
                if ms:
                    pick = ms[-1] if len(ms) >= 3 else ms[0]
                    if MIN_ROOM_PRICE <= pick <= MAX_ROOM_PRICE:
                        vals.append(pick)
                        j += 1
                        continue
                # ara satır (boş/etiket) atla ama oda satırına gelince dur
                if room_rx.search(lines[j]) and not moneys_in_cell(lines[j]):
                    break
                if not ms:
                    j += 1
                    if j - i > 6:
                        break
                    continue
                break
            if len(vals) == 3 and vals[0] <= vals[1] <= vals[2] and vals[2] / max(vals[0], 1) <= 5:
                buckets["kurum"].append(vals[0])
                buckets["kamu"].append(vals[1])
                buckets["sivil"].append(vals[2])
                i = j
                continue
        i += 1

    if len(buckets["sivil"]) < 2 or len(buckets["kurum"]) < 2:
        return None
    if max(buckets["sivil"]) < 900:
        return None
    if min(buckets["kurum"]) >= max(buckets["sivil"]):
        return None

    gecerlilik = "2026 yılı (sayfada yayımlanan liste)"
    if re.search(r"19[./.]01[./.]2026", text_all):
        gecerlilik = "19.01.2026 itibarıyla"
    elif re.search(r"01[./.]05[./.]2026", text_all):
        gecerlilik = "01.05.2026 itibarıyla"

    return {
        "fiyat_sivil": format_range(buckets["sivil"]),
        "fiyat_kamu_personeli": format_range(buckets["kamu"]),
        "fiyat_kurum_personeli": format_range(buckets["kurum"]),
        "kaynak": url,
        "gecerlilik": gecerlilik,
    }


def parse_price_table(html: str, url: str) -> dict[str, Any] | None:
    if not YEAR_2026_RE.search(html):
        # bazı sayfalar görsel PDF; yıl yoksa yine de polisevi fiyat tablosu olabilir
        # ama kullanıcı 2026 istedi — yıl yoksa reddet
        if "2025" in html and "2026" not in html:
            return None

    soup = BeautifulSoup(html, "lxml")
    text_all = soup.get_text(" ", strip=True)
    if not YEAR_2026_RE.search(text_all) and not YEAR_2026_RE.search(html):
        return None
    if not POLISEVI_HINT.search(text_all) and "TEŞKİLAT" not in text_all.upper() and "teskilat" not in text_all.casefold():
        # yine de tablo header'larına bak
        pass

    buckets: dict[str, list[float]] = {"kurum": [], "kamu": [], "sivil": []}
    found_any = False

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        # find header row
        colmap = None
        data_start = 0
        for ri, tr in enumerate(rows[:5]):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if not cells:
                continue
            joined = " | ".join(cells)
            cm = detect_columns(cells)
            if cm:
                colmap = cm
                data_start = ri + 1
                break
            # sometimes header is single cell spanning — skip
            if ROLE_HINTS["kurum"].search(joined) and ROLE_HINTS["sivil"].search(joined):
                # try next row as real header
                continue
        if not colmap:
            continue

        for tr in rows[data_start:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            row_label = cells[0].casefold()
            # ek yatak / kart / çamaşır / kuaför / yemek hariç
            if any(
                x in row_label
                for x in (
                    "ek yatak",
                    "oda kart",
                    "kayıp kart",
                    "kayip kart",
                    "manyetik",
                    "çamaşır",
                    "camasir",
                    "ütü",
                    "utu",
                    "kahvaltı",
                    "kahvalti",
                    "saç",
                    "sac ",
                    "fön",
                    "fon ",
                    "ağda",
                    "agda",
                    "makyaj",
                    "perma",
                    "röfle",
                    "rofle",
                    "tabldot",
                    "çorba",
                    "corba",
                )
            ):
                continue
            # tablo başlığı konaklama değilse (kuaför/yemek) tüm tabloyu atla
            table_head = " ".join(
                c.get_text(" ", strip=True) for c in table.find_all(["th", "caption"])[:8]
            ).casefold()
            if any(
                x in table_head
                for x in ("kuaför", "kuafor", "çamaşır", "camasir", "yemek list", "tabldot", "salon fiyat")
            ):
                break
            if "konaklama" not in table_head and "oda" not in table_head and "yatak" not in table_head:
                # header hücrelerinde oda/konaklama yoksa yine de rol header varsa devam
                pass
            for role, idx in colmap.items():
                if idx >= len(cells):
                    continue
                vals = moneys_in_cell(cells[idx])
                # genelde hücrede tek tutar; vergi ayrımı varsa son = toplam tercih
                if vals:
                    # eğer 3 sayı varsa (ücret, vergi, toplam) toplamı al
                    pick = vals[-1] if len(vals) >= 3 else (max(vals) if vals else None)
                    if pick is not None and MIN_ROOM_PRICE <= pick <= MAX_ROOM_PRICE:
                        buckets[role].append(pick)
                        found_any = True

    # Yapısız metin tahmini YOK — yanlış fiyat riski yüksek.

    if not found_any:
        return parse_stacked_room_prices(text_all, url)
    if not buckets["kurum"] or not buckets["sivil"]:
        stacked = parse_stacked_room_prices(text_all, url)
        if stacked:
            return stacked
        return None
    # en az 2 oda tipi
    if len(buckets["sivil"]) < 2 or len(buckets["kurum"]) < 2:
        stacked = parse_stacked_room_prices(text_all, url)
        if stacked:
            return stacked
        return None
    # makul aralık: sivil genelde kurumdan yüksek
    if min(buckets["sivil"]) < MIN_ROOM_PRICE:
        return None
    if max(buckets["sivil"]) < 900:
        return None
    if min(buckets["kurum"]) >= max(buckets["sivil"]):
        return None

    # vergi notu
    gecerlilik = "2026 yılı (sayfada yayımlanan liste)"
    if re.search(r"01[./.]05[./.]2026|01\.05\.2026", text_all):
        gecerlilik = "01.05.2026 itibarıyla"
    elif re.search(r"19[./.]01[./.]2026", text_all):
        gecerlilik = "19.01.2026 itibarıyla"
    if re.search(r"%\s*2\s*konaklama\s*vergisi\s*(dahil|DAHİL)", text_all, re.I):
        gecerlilik += " (%2 konaklama vergisi dahil)"
    elif re.search(r"%\s*1\s*konaklama\s*vergisi\s*(dahil|DAHİL)", text_all, re.I):
        gecerlilik += " (%1 konaklama vergisi dahil)"
    elif re.search(r"vergisi\s*HAR[İI][ÇC]|vergisi\s*hari[çc]", text_all, re.I):
        gecerlilik += " (sayfada vergi HARİÇ belirtilmiş olabilir)"

    entry = {
        "fiyat_sivil": format_range(buckets["sivil"]),
        "fiyat_kamu_personeli": format_range(buckets["kamu"]),
        "fiyat_kurum_personeli": format_range(buckets["kurum"]),
        "kaynak": url,
        "gecerlilik": gecerlilik,
        "_counts": {k: len(v) for k, v in buckets.items()},
        "_mins": {k: (min(v) if v else None) for k, v in buckets.items()},
        "_maxs": {k: (max(v) if v else None) for k, v in buckets.items()},
    }
    # en az bir fiyat alanı dolu olmalı
    if not any(entry[k] for k in ("fiyat_sivil", "fiyat_kamu_personeli", "fiyat_kurum_personeli")):
        return None
    return entry


def pick_best_facility(il: str, facilities: list[dict], page_title_hint: str = "") -> dict | None:
    """Aynı ildeki polisevi adaylarından en uygununu seç. Belirsizse None."""
    cands = [
        f
        for f in facilities
        if f.get("il") == il
        and re.search(r"polis", f.get("isim", ""), re.I)
        and not re.search(
            r"d[uü][gğ][uü]n|salon|spor|yemek|kayak|kongre|pekom|moral",
            f.get("isim", ""),
            re.I,
        )
    ]
    if not cands:
        return None
    slug = normalize_name(il)
    target = f"{slug}polisevi"  # "Polis Evi" / "Polisevi" normalize sonrası aynı
    matches = [f for f in cands if normalize_name(f["isim"]) == target]
    if matches:
        return sorted(matches, key=lambda f: len(f["isim"]))[0]
    if len(cands) == 1:
        return cands[0]
    return None


def ddg_search_urls(query: str) -> list[str]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    html, err = fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.select("a.result__a"):
        href = a.get("href") or ""
        if "pol.tr" in href or "gov.tr" in href or "meb.gov.tr" in href:
            out.append(href)
    # duckduckgo sometimes wraps
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "uddg=" in href:
            m = re.search(r"uddg=([^&]+)", href)
            if m:
                from urllib.parse import unquote

                real = unquote(m.group(1))
                if any(x in real for x in (".pol.tr", ".gov.tr", "meb.gov.tr")):
                    out.append(real)
    seen = set()
    uniq = []
    for u in out:
        if u not in seen and u.startswith("http"):
            seen.add(u)
            uniq.append(u)
    return uniq[:12]


def scan_il_polisevi(il: str, facilities: list[dict]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "il": il,
        "status": "not_found",
        "tried": [],
        "facility": None,
        "entry": None,
        "error": None,
    }
    facility = pick_best_facility(il, facilities)
    if not facility:
        result["status"] = "ambiguous_or_no_facility"
        result["error"] = "DB'de tekil polisevi eşleşmesi yok"
        return result

    result["facility"] = {"il": facility["il"], "isim": facility["isim"]}

    urls = candidate_pol_urls(il)
    # homepage crawl for more links
    for home in [f"https://www.{slug_il(il)}.pol.tr", f"https://{slug_il(il)}.pol.tr"]:
        html, err = fetch(home)
        result["tried"].append({"url": home, "err": err, "ok": bool(html)})
        if html:
            for link in extract_links(html, home):
                if link not in urls:
                    urls.append(link)

    # DDG supplement
    for q in (
        f"site:{slug_il(il)}.pol.tr 2026 polisevi fiyat",
        f"{il} polisevi 2026 fiyat listesi site:pol.tr",
    ):
        for u in ddg_search_urls(q):
            if u not in urls:
                urls.append(u)
        time.sleep(0.4)

    seen_pages = set()
    for url in urls[:35]:
        if url in seen_pages:
            continue
        seen_pages.add(url)
        html, err = fetch(url)
        result["tried"].append({"url": url, "err": err, "ok": bool(html)})
        if not html:
            continue
        parsed = parse_price_table(html, url)
        if parsed:
            # strip debug fields for public json later
            result["entry"] = parsed
            result["status"] = "found"
            return result
        # follow deeper price links once
        for link in extract_links(html, url)[:10]:
            if link in seen_pages:
                continue
            seen_pages.add(link)
            html2, err2 = fetch(link)
            result["tried"].append({"url": link, "err": err2, "ok": bool(html2)})
            if not html2:
                continue
            parsed2 = parse_price_table(html2, link)
            if parsed2:
                result["entry"] = parsed2
                result["status"] = "found"
                return result
        time.sleep(0.15)

    return result


def load_master() -> list[dict]:
    for p in MASTER_CANDIDATES:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            return data.get("tesisler", [])
    raise FileNotFoundError("master_database.json bulunamadı")


def load_existing() -> dict:
    if FIYATLAR_PATH.exists():
        return json.loads(FIYATLAR_PATH.read_text(encoding="utf-8"))
    return {
        "not": "Yalnızca resmi kaynaklardan doğrulanmış 2026 konaklama tarifeleri.",
        "tesisler": [],
    }


def public_entry(il: str, isim: str, parsed: dict) -> dict:
    out = {
        "il": il,
        "isim": isim,
        "fiyat_sivil": parsed.get("fiyat_sivil"),
        "fiyat_kamu_personeli": parsed.get("fiyat_kamu_personeli"),
        "fiyat_kurum_personeli": parsed.get("fiyat_kurum_personeli"),
        "kaynak": parsed.get("kaynak"),
        "gecerlilik": parsed.get("gecerlilik"),
    }
    return {k: v for k, v in out.items() if v is not None}


def merge_and_save(found_entries: list[dict], report: dict) -> None:
    data = load_existing()
    by_key = {}
    for t in data.get("tesisler", []):
        by_key[(t["il"], t["isim"])] = t
    for e in found_entries:
        by_key[(e["il"], e["isim"])] = e

    data["not"] = (
        "Yalnızca resmi kaynaklardan (il Emniyet Müdürlüğü / pol.tr ve benzeri kamu siteleri) "
        "2026 yılı yayımlanmış konaklama tarifeleri eklenmiştir. Kaynak bulunamayan tesisler "
        "bilerek yazılmamıştır. Aralıklar oda tiplerine göre min–max gecelik ücrettir "
        "(ek yatak satırları hariç). fiyat_kurum_personeli = teşkilat mensubu; "
        "fiyat_kamu_personeli = kamu personeli / konaklama ücreti; fiyat_sivil = onaylı misafir. "
        "Kesin ücret oda tipine göre değişir; rezervasyonda tesisle teyit edilmelidir."
    )
    data["tesisler"] = sorted(by_key.values(), key=lambda x: (x["il"], x["isim"]))
    FIYATLAR_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    # flutter mirror if present
    flutter = ROOT.parent / "rotalink_flutter" / "fiyatlar.json"
    if flutter.parent.exists():
        flutter.write_text(FIYATLAR_PATH.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    print("Loading master DB…", flush=True)
    facilities = load_master()
    print(f"Tesis sayısı: {len(facilities)}", flush=True)

    # unique iller that have a polisevi-like facility
    iller = sorted(
        {
            f["il"]
            for f in facilities
            if re.search(r"polis", f.get("isim", ""), re.I)
            or (f.get("tip") or "").casefold() == "polisevi"
        }
    )
    print(f"Polisevi taranacak il: {len(iller)}", flush=True)

    results = []
    found_entries = []

    # sequential is safer for pol.tr rate limits; mild parallelism
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(scan_il_polisevi, il, facilities): il for il in iller}
        done = 0
        for fut in as_completed(futs):
            il = futs[fut]
            done += 1
            try:
                r = fut.result()
            except Exception as e:
                r = {
                    "il": il,
                    "status": "error",
                    "error": str(e),
                    "trace": traceback.format_exc(),
                }
            results.append(r)
            if r.get("status") == "found" and r.get("entry") and r.get("facility"):
                pe = public_entry(r["facility"]["il"], r["facility"]["isim"], r["entry"])
                found_entries.append(pe)
                print(
                    f"[{done}/{len(iller)}] FOUND {pe['il']} / {pe['isim']} -> {pe.get('fiyat_sivil')}",
                    flush=True,
                )
            else:
                print(
                    f"[{done}/{len(iller)}] {r.get('status')} {il}",
                    flush=True,
                )
            # incremental progress
            PROGRESS_PATH.write_text(
                json.dumps(
                    {
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "done": done,
                        "total": len(iller),
                        "found": len(found_entries),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    report = {
        "started_note": "Sadece resmi sayfada 2026 fiyat tablosu bulunan tesisler",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "iller_scanned": len(iller),
        "found_count": len(found_entries),
        "found": found_entries,
        "results": results,
    }
    merge_and_save(found_entries, report)
    print(
        f"DONE. Found={len(found_entries)} → {FIYATLAR_PATH}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
