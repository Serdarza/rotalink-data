#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe *.ogretmenevi.com.tr/fiyatlistesi.php (+ variants) for 2026 tariffs."""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
MASTER = Path(
    r"C:\Users\Kartal\Desktop\Rotalink_Merkez\Rotalink_Web\rotalink-app\data\master_database.json"
)
FIYATLAR = ROOT / "fiyatlar.json"
LOG = ROOT / "scripts" / "probe_fiyatlistesi.log"
REPORT = ROOT / "scripts" / "probe_fiyatlistesi_report.json"

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}
S = requests.Session()
S.headers.update(UA)

TR = str.maketrans(
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
MONEY = re.compile(
    r"(?:₺|TL)?\s*(\d{1,3}(?:[.\s]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s*(?:₺|TL)?",
    re.I,
)

# Known working / candidate hosts (seed + common city slugs)
EXTRA_URLS = [
    "https://corumogretmenevi.com.tr/fiyatlistesi.php",
    "https://www.corumogretmenevi.com.tr/fiyatlistesi.php",
    "https://www.iskilipogretmenevi.com.tr/fiyatlistesi.php",
    "https://iskilipogretmenevi.com.tr/fiyatlistesi.php",
    "https://www.denizliogretmenevi.com.tr/",
    "https://denizliogretmenevi.com.tr/fiyatlistesi.php",
    "https://www.denizliogretmenevi.com.tr/fiyatlistesi.php",
    "https://bodrumogretmenevi.com.tr/fiyatlistesi.php",
    "https://www.bodrumogretmenevi.com.tr/fiyatlistesi.php",
    "https://fethiyeogretmenevi.com.tr/fiyatlistesi.php",
    "https://www.fethiyeogretmenevi.com.tr/fiyatlistesi.php",
    "https://milasogretmenevi.com.tr/fiyatlistesi.php",
    "https://koycegizogretmenevi.com.tr/fiyatlistesi.php",
    "https://ulaogretmenevi.com.tr/fiyatlistesi.php",
    "https://ankaraogretmenevi.com.tr/fiyatlistesi.php",
    "https://www.ankaraogretmenevi.com.tr/fiyatlistesi.php",
    "https://izmirogretmenevi.com.tr/fiyatlistesi.php",
    "https://bursaoogretmenevi.com.tr/fiyatlistesi.php",
    "https://antalyogretmenevi.com.tr/fiyatlistesi.php",
    "https://www.antalyogretmenevi.com.tr/fiyatlistesi.php",
    "https://adanaogretmenevi.com.tr/fiyatlistesi.php",
    "https://konyaogretmenevi.com.tr/fiyatlistesi.php",
    "https://samsunogretmenevi.com.tr/fiyatlistesi.php",
    "https://trabzonogretmenevi.com.tr/fiyatlistesi.php",
    "https://eskisehirogretmenevi.com.tr/fiyatlistesi.php",
    "https://gaziantepogretmenevi.com.tr/fiyatlistesi.php",
    "https://malatyogretmenevi.com.tr/fiyatlistesi.php",
    "https://vanogretmenevi.com.tr/fiyatlistesi.php",
    "https://erzurumogretmenevi.com.tr/fiyatlistesi.php",
    "https://diyarbakirogretmenevi.com.tr/fiyatlistesi.php",
    "https://mardinogretmenevi.com.tr/fiyatlistesi.php",
    "https://hatayogretmenevi.com.tr/fiyatlistesi.php",
    "https://manisaogretmenevi.com.tr/fiyatlistesi.php",
    "https://aydinogretmenevi.com.tr/fiyatlistesi.php",
    "https://muglaogretmenevi.com.tr/fiyatlistesi.php",
    "https://www.muglaogretmenevi.com.tr/fiyatlistesi.php",
    "https://balikesirogretmenevi.com.tr/fiyatlistesi.php",
    "https://tekirdagogretmenevi.com.tr/fiyatlistesi.php",
    "https://edirneogretmenevi.com.tr/fiyatlistesi.php",
    "https://kirklareliogretmenevi.com.tr/fiyatlistesi.php",
    "https://canakkaleogretmenevi.com.tr/fiyatlistesi.php",
    "https://afyonogretmenevi.com.tr/fiyatlistesi.php",
    "https://usakogretmenevi.com.tr/fiyatlistesi.php",
    "https://kutahyaogretmenevi.com.tr/fiyatlistesi.php",
    "https://boluogretmenevi.com.tr/fiyatlistesi.php",
    "https://duzceogretmenevi.com.tr/fiyatlistesi.php",
    "https://zonguldakogretmenevi.com.tr/fiyatlistesi.php",
    "https://karabukogretmenevi.com.tr/fiyatlistesi.php",
    "https://kastamonuogretmenevi.com.tr/fiyatlistesi.php",
    "https://sinopogretmenevi.com.tr/fiyatlistesi.php",
    "https://amasyaogretmenevi.com.tr/fiyatlistesi.php",
    "https://tokatogretmenevi.com.tr/fiyatlistesi.php",
    "https://sivasogretmenevi.com.tr/fiyatlistesi.php",
    "https://yozgatogretmenevi.com.tr/fiyatlistesi.php",
    "https://nevsehirogretmenevi.com.tr/fiyatlistesi.php",
    "https://kirsehirogretmenevi.com.tr/fiyatlistesi.php",
    "https://kayseriogretmenevi.com.tr/fiyatlistesi.php",
    "https://nigdeogretmenevi.com.tr/fiyatlistesi.php",
    "https://aksarayogretmenevi.com.tr/fiyatlistesi.php",
    "https://karamanogretmenevi.com.tr/fiyatlistesi.php",
    "https://mersinogretmenevi.com.tr/fiyatlistesi.php",
    "https://osmaniyeogretmenevi.com.tr/fiyatlistesi.php",
    "https://kahramanmarasogretmenevi.com.tr/fiyatlistesi.php",
    "https://adiyamanogretmenevi.com.tr/fiyatlistesi.php",
    "https://sanliurfaogretmenevi.com.tr/fiyatlistesi.php",
    "https://batmanogretmenevi.com.tr/fiyatlistesi.php",
    "https://siirtogretmenevi.com.tr/fiyatlistesi.php",
    "https://sirnakogretmenevi.com.tr/fiyatlistesi.php",
    "https://hakkariogretmenevi.com.tr/fiyatlistesi.php",
    "https://bitlisogretmenevi.com.tr/fiyatlistesi.php",
    "https://musogretmenevi.com.tr/fiyatlistesi.php",
    "https://bingologretmenevi.com.tr/fiyatlistesi.php",
    "https://elazigogretmenevi.com.tr/fiyatlistesi.php",
    "https://tunceliogretmenevi.com.tr/fiyatlistesi.php",
    "https://gumushaneogretmenevi.com.tr/fiyatlistesi.php",
    "https://bayburtogretmenevi.com.tr/fiyatlistesi.php",
    "https://artvinogretmenevi.com.tr/fiyatlistesi.php",
    "https://rizeogretmenevi.com.tr/fiyatlistesi.php",
    "https://giresunogretmenevi.com.tr/fiyatlistesi.php",
    "https://orduogretmenevi.com.tr/fiyatlistesi.php",
    "https://ispartaogretmenevi.com.tr/fiyatlistesi.php",
    "https://burdurogretmenevi.com.tr/fiyatlistesi.php",
    "https://yalovaogretmenevi.com.tr/fiyatlistesi.php",
    "https://sakaryaogretmenevi.com.tr/fiyatlistesi.php",
    "https://kocaeliogretmenevi.com.tr/fiyatlistesi.php",
    "https://www.cubukogretmenevi.com.tr/fiyatlistesi.php",
    "https://cubukogretmenevi.com.tr/fiyatlistesi.php",
]


def log(msg: str) -> None:
    print(msg, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").casefold().translate(TR))


def parse_money(tok: str) -> float | None:
    raw = (
        tok.strip()
        .replace("₺", "")
        .replace("TL", "")
        .replace("tl", "")
        .replace("\xa0", "")
        .replace(" ", "")
    )
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", raw):
        raw = raw.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", raw):
        raw = raw.replace(",", "")
    elif "," in raw and "." in raw:
        raw = (
            raw.replace(".", "").replace(",", ".")
            if raw.rfind(",") > raw.rfind(".")
            else raw.replace(",", "")
        )
    elif "," in raw:
        raw = (
            raw.replace(".", "").replace(",", ".")
            if len(raw.split(",")[-1]) <= 2
            else raw.replace(",", "")
        )
    try:
        v = float(raw)
    except ValueError:
        return None
    return v if 1 <= v <= 100000 else None


def moneys(text: str) -> list[float]:
    out = []
    for m in MONEY.finditer(text.replace("\xa0", " ")):
        v = parse_money(m.group(1))
        if v is not None:
            out.append(v)
    return out


def fmt_range(vals: list[float]) -> str | None:
    if not vals:
        return None
    lo, hi = min(vals), max(vals)

    def f(x: float) -> str:
        return f"{int(round(x)):,}".replace(",", ".")

    return f"{f(lo)} TL" if abs(lo - hi) < 0.5 else f"{f(lo)} – {f(hi)} TL"


def fetch(url: str) -> tuple[str | None, int | None]:
    try:
        r = S.get(url, timeout=12, allow_redirects=True)
        if r.status_code >= 400:
            return None, r.status_code
        ctype = (r.headers.get("content-type") or "").lower()
        if "pdf" in ctype or url.lower().endswith(".pdf"):
            return None, r.status_code
        if "html" not in ctype and "text" not in ctype:
            return None, r.status_code
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text, r.status_code
    except Exception:
        return None, None


def detect_cols(headers: list[str]) -> dict[str, int] | None:
    m: dict[str, int] = {}
    for i, h in enumerate(headers):
        h = h.strip()
        if not h:
            continue
        if re.search(r"[üu]ye\s*/\s*(kamu|öğretmen|ogretmen)|uye\s*/\s*", h, re.I):
            m["kurum"] = i
            if re.search(r"kamu", h, re.I):
                m["kamu"] = i
            continue
        if re.search(r"meb|öğretmen|ogretmen|[üu]ye", h, re.I) and "kurum" not in m:
            m["kurum"] = i
        if re.search(r"kamu", h, re.I) and "kamu" not in m and not re.search(
            r"meb|öğretmen|[üu]ye", h, re.I
        ):
            m["kamu"] = i
        if re.search(r"sivil|diğer|diger|öğrenci|ogrenci", h, re.I) and "sivil" not in m:
            m["sivil"] = i
    if "kurum" in m and ("sivil" in m or "kamu" in m):
        return m
    if "kamu" in m and "sivil" in m:
        return m
    return None


def parse_prices(html: str, url: str) -> dict | None:
    if "2026" not in html:
        return None
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    if "2026" not in text:
        return None
    if not re.search(r"konaklama|oda|fiyat|ücret|ucret", text, re.I):
        return None
    if re.search(r"ortalama\s*(öğretmenevi|ogretmenevi)|tahmini\s*aral", text, re.I):
        return None

    buckets: dict[str, list[float]] = {"kurum": [], "kamu": [], "sivil": []}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        colmap = None
        start = 0
        for ri, tr in enumerate(rows[:5]):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            cm = detect_cols(cells)
            if cm:
                colmap = cm
                start = ri + 1
                break
        if not colmap:
            continue
        for tr in rows[start:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            lab = cells[0].casefold()
            if any(x in lab for x in ("ek yatak", "toplantı", "toplanti", "kart", "kahvaltı ayrı")):
                continue
            for role, idx in colmap.items():
                if idx >= len(cells):
                    continue
                vals = moneys(cells[idx])
                if vals:
                    pick = vals[0]
                    if 300 <= pick <= 25000:
                        buckets[role].append(pick)

    if not any(buckets.values()):
        return None
    if max((max(v) for v in buckets.values() if v), default=0) < 600:
        return None

    gecerlilik = "2026 yılı (sayfada yayımlanan liste)"
    if re.search(r"01[./.]01[./.]2026|1\s*ocak\s*2026", text, re.I):
        gecerlilik = "01.01.2026 itibarıyla"
    elif re.search(r"02\s*[şs]ubat\s*2026|02[./.]02[./.]2026", text, re.I):
        gecerlilik = "02 Şubat 2026 – 30 Haziran 2026"
    elif re.search(r"1\s*temmuz\s*2026|01[./.]07[./.]2026", text, re.I):
        gecerlilik = "1 Temmuz 2026 itibarıyla"

    return {
        "fiyat_sivil": fmt_range(buckets["sivil"]),
        "fiyat_kamu_personeli": fmt_range(buckets["kamu"]),
        "fiyat_kurum_personeli": fmt_range(buckets["kurum"]),
        "kaynak": url,
        "gecerlilik": gecerlilik,
    }


def slug_candidates(isim: str, il: str) -> list[str]:
    n = norm(isim)
    for s in (
        "veaksamsanatokulu",
        "veaso",
        "aso",
        "mudurlugu",
        "ogretmenevi",
        "ogretmen evi",
    ):
        n = n.replace(norm(s), "")
    n = n.replace("ogretmenevi", "")
    cores = set()
    if n and len(n) >= 3:
        cores.add(n)
    iln = norm(il)
    if iln:
        cores.add(iln)
        if n.startswith(iln) and len(n) > len(iln):
            cores.add(n[len(iln) :])
            cores.add(n)
    # strip short junk
    return [c for c in cores if len(c) >= 3]


def urls_for_facility(f: dict) -> list[str]:
    urls = []
    for core in slug_candidates(f["isim"], f["il"]):
        for host in (
            f"{core}ogretmenevi.com.tr",
            f"www.{core}ogretmenevi.com.tr",
        ):
            urls.append(f"https://{host}/fiyatlistesi.php")
            urls.append(f"https://{host}/fiyat-listesi")
            urls.append(f"https://{host}/fiyatlar")
    # dedupe
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:8]


def match_facility(facilities: list[dict], html: str, url: str) -> dict | None:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    host = urlparse(url).netloc.lower().replace("www.", "")
    host_core = host.replace("ogretmenevi.com.tr", "").replace(".com.tr", "")
    blob = norm(title + " " + host + " " + soup.get_text(" ", strip=True)[:4000])
    best = None
    best_score = 0
    for f in facilities:
        fn = norm(f["isim"])
        score = 0
        if fn and fn in blob:
            score = 120 + len(fn)
        else:
            m = re.match(r"(.+?)ogretmen", fn)
            core = m.group(1) if m else ""
            if len(core) >= 4 and core in blob:
                score = 60 + len(core)
            if host_core and len(host_core) >= 4 and host_core in fn:
                score = max(score, 80 + len(host_core))
        if score > best_score:
            best_score = score
            best = f
    if best and best_score >= 60:
        return best
    return None


def merge(found: list[dict]) -> None:
    data = json.loads(FIYATLAR.read_text(encoding="utf-8"))
    by = {(t["il"], t["isim"]): t for t in data.get("tesisler", [])}
    for e in found:
        pub = {
            "il": e["il"],
            "isim": e["isim"],
            "fiyat_sivil": e["entry"].get("fiyat_sivil"),
            "fiyat_kamu_personeli": e["entry"].get("fiyat_kamu_personeli"),
            "fiyat_kurum_personeli": e["entry"].get("fiyat_kurum_personeli"),
            "kaynak": e["entry"].get("kaynak"),
            "gecerlilik": e["entry"].get("gecerlilik"),
        }
        by[(pub["il"], pub["isim"])] = {k: v for k, v in pub.items() if v is not None}
    data["tesisler"] = sorted(by.values(), key=lambda x: (x["il"], x["isim"]))
    FIYATLAR.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    flutter = ROOT.parent / "rotalink_flutter" / "fiyatlar.json"
    if flutter.parent.exists():
        flutter.write_text(FIYATLAR.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    LOG.write_text("", encoding="utf-8")
    log("START fiyatlistesi probe")
    facilities = [
        t
        for t in json.loads(MASTER.read_text(encoding="utf-8"))["tesisler"]
        if t.get("tip") == "Öğretmenevi"
    ]
    log(f"facilities={len(facilities)}")

    # Build URL set: EXTRA + per-facility guesses (limit for speed)
    urls: list[str] = []
    seen_u = set()
    for u in EXTRA_URLS:
        if u not in seen_u:
            seen_u.add(u)
            urls.append(u)

    # Prioritize unique district/city cores from DB names
    for f in facilities:
        for u in urls_for_facility(f)[:2]:
            if u not in seen_u:
                seen_u.add(u)
                urls.append(u)

    log(f"urls_to_probe={len(urls)}")

    found: list[dict] = []
    seen_fac = set()
    live = 0
    for i, url in enumerate(urls, 1):
        html, code = fetch(url)
        if not html:
            if i % 50 == 0:
                log(f"[{i}/{len(urls)}] probed… found={len(found)} live={live}")
            continue
        live += 1
        parsed = parse_prices(html, url)
        if not parsed:
            # page exists but no 2026 table
            if "2026" in html and re.search(r"fiyat|konaklama", html, re.I):
                log(f"LIVE no-parse {url}")
            continue
        fac = match_facility(facilities, html, url)
        if not fac:
            log(f"PARSE no-match {url} -> {parsed.get('fiyat_sivil')}")
            continue
        key = (fac["il"], fac["isim"])
        if key in seen_fac:
            continue
        seen_fac.add(key)
        found.append({"il": fac["il"], "isim": fac["isim"], "entry": parsed})
        log(
            f"FOUND {fac['il']} / {fac['isim']} -> sivil={parsed.get('fiyat_sivil')} kurum={parsed.get('fiyat_kurum_personeli')} | {url}"
        )
        if len(found) % 3 == 0:
            merge(found)
        time.sleep(0.05)

    merge(found)
    REPORT.write_text(
        json.dumps(
            {
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "probed": len(urls),
                "live_pages": live,
                "found_count": len(found),
                "found": [{"il": x["il"], "isim": x["isim"], **x["entry"]} for x in found],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    log(f"DONE found={len(found)} live_pages={live}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
