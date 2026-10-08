"""Kamp alanı keşfi ve kayıtlı OSM kaynaklarının kontrolü.

Kaynak sırası: resmî bakanlık/belediye sayfaları bu sürümde fiyat yazmaz;
konum keşfi lisanslı açık veri (OpenStreetMap, ODbL) ile yapılır.
Resmî fiyat uydurulmaz. Google Maps ve sosyal medya kullanılmaz.

Ortam: CAMP_MODE=discover|update, CAMP_ONLY_IL, DRY_RUN, CAMP_TIME_BUDGET_MIN.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import iller as iller_mod  # noqa: E402
from model import birlestir, from_osm  # noqa: E402

DATA = ROOT / "data"
SITES = DATA / "camp_sites.json"
SOURCES = DATA / "camp_sources.json"
HISTORY = DATA / "camp_price_history.json"
REVIEW = DATA / "camp_review_queue.json"
REPORTS = HERE / "reports"
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
RETRY_CODES = (429, 500, 502, 503, 504)
UA = "RotalinkCampBot/1.0 (https://rotalink.tr)"
MODE = os.environ.get("CAMP_MODE", "discover")
DRY = os.environ.get("DRY_RUN", "").lower() in {"1", "true", "yes"}


def load(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def overpass(query: str) -> dict:
    body = urllib.parse.urlencode({"data": query}).encode()
    last = "bağlantı kurulamadı"
    for url in OVERPASS_URLS:
        for attempt in range(3):
            req = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=90) as res:
                    return json.loads(res.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code}"
                if e.code not in RETRY_CODES:
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last = type(e).__name__
            time.sleep((5, 15, 30)[attempt])
    raise RuntimeError(last)


def query_il(iso: str) -> str:
    return (
        f'[out:json][timeout:80];'
        f'area["ISO3166-2"="{iso}"]["admin_level"="4"]->.a;'
        f'(nwr["tourism"="camp_site"](area.a);nwr["tourism"="caravan_site"](area.a););'
        f'out tags center;'
    )


def query_ids(ids: list[tuple[str, str]]) -> str:
    parts = []
    for tip, num in ids:
        if tip in {"node", "way", "relation"} and num.isdigit():
            parts.append(f"{tip}({num});")
    return "[out:json][timeout:80];(" + "".join(parts) + ");out tags center;"


def discover(provinces: list[tuple[str, str]], today: date, deadline: float):
    found, errors = [], {}
    pending = list(provinces)
    for round_no in range(2):
        if round_no and pending:
            print(f"{len(pending)} il yeniden deneniyor…", flush=True)
            time.sleep(60)
        retry = []
        for il, iso in pending:
            if time.monotonic() > deadline:
                errors[il] = "zaman sınırı"
                continue
            try:
                payload = overpass(query_il(iso))
            except RuntimeError as e:
                errors[il] = str(e)
                retry.append((il, iso))
                continue
            errors.pop(il, None)
            for el in payload.get("elements") or []:
                rec = from_osm(il, el, today)
                if rec:
                    found.append(rec)
            time.sleep(2)
        pending = retry
    for il, err in errors.items():
        print(f"hata: {il}: {err}", flush=True)
    return found, errors


def update(prev: list[dict], today: date, deadline: float):
    wanted = []
    for rec in prev:
        rid = str(rec.get("id") or "")
        if not rid.startswith("osm-"):
            continue
        parts = rid.split("-", 2)
        if len(parts) == 3 and parts[1] in {"node", "way", "relation"} and parts[2].isdigit():
            wanted.append((parts[1], parts[2], rec))
    found, errors = [], {}
    for i in range(0, len(wanted), 40):
        if time.monotonic() > deadline:
            errors["toplu"] = "zaman sınırı"
            break
        chunk = wanted[i:i + 40]
        try:
            payload = overpass(query_ids([(t, n) for t, n, _ in chunk]))
        except RuntimeError as e:
            for _, _, rec in chunk:
                errors[rec["id"]] = str(e)
            continue
        by_id = {f"osm-{el.get('type')}-{el.get('id')}": el for el in payload.get("elements") or []}
        for _, _, rec in chunk:
            el = by_id.get(rec["id"])
            if not el:
                continue
            fresh = from_osm(rec.get("il") or "", el, today)
            if fresh:
                found.append(fresh)
        time.sleep(2)
    return found, errors


def il_raporu(items: list[dict], provinces: list[tuple[str, str]], errors: dict, today: date) -> list[dict]:
    rows = []
    for il, _iso in provinces:
        own = [r for r in items if r.get("il") == il and r.get("durum") == "aktif"]
        rows.append({
            "il": il,
            "kesfedilen": len(own),
            "cadir": sum(1 for r in own if r.get("cadir") is True),
            "karavan": sum(1 for r in own if r.get("karavan") is True or r.get("kamp_turu") == "karavan"),
            "fiyat_dogrulanmis": sum(1 for r in own if r.get("fiyat") is not None and r.get("dogrulama") == "resmi"),
            "dogrulanamayan": sum(1 for r in items if r.get("il") == il and r.get("durum") == "inceleme"),
            "hata": errors.get(il),
            "son_tarama": None if errors.get(il) else today.isoformat(),
        })
    return rows


def main() -> int:
    today = date.today()
    only = {x.strip() for x in os.environ.get("CAMP_ONLY_IL", "").split(",") if x.strip()}
    provinces = iller_mod.sec(only or None)
    budget = float(os.environ.get("CAMP_TIME_BUDGET_MIN", "80")) * 60
    deadline = time.monotonic() + budget
    prev_doc = load(SITES, {"items": []})
    prev = prev_doc.get("items") or []
    history = load(HISTORY, {})
    if MODE == "update":
        found, errors = update(prev, today, deadline)
        scanned = {r.get("il") for r in prev if r.get("il")}
        failed = set()
        for rid, _err in errors.items():
            old = next((r for r in prev if r["id"] == rid), None)
            if old and old.get("il"):
                failed.add(old["il"])
    else:
        found, errors = discover(provinces, today, deadline)
        scanned = {il for il, _ in provinces}
        failed = set(errors)
    items, reviews, stats = birlestir(prev, found, scanned, failed, today, history)
    report_rows = il_raporu(items, provinces if MODE == "discover" else [(il, "") for il in sorted(scanned)], errors, today)
    summary = {
        "tarih": today.isoformat(),
        "mod": MODE,
        "dry_run": DRY,
        "taranan_il": len(provinces) if MODE == "discover" else len(scanned),
        "hatali_il": len(errors),
        **stats,
        "inceleme_kuyrugu_yeni": len(reviews),
        "iller": report_rows,
    }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / f"{today.isoformat()}-{MODE}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not DRY:
        save(SITES, {
            "not": "Çadır, karavan ve kamping alanları. Konumlar OpenStreetMap açık verisinden "
                   "(ODbL) gelir; resmî fiyat değildir. Bilinmeyen alanlar null'dır. "
                   "durum=inceleme olan kayıt uygulamada gösterilmez, silinmez.",
            "atif": "© OpenStreetMap katkıları (ODbL)",
            "guncelleme": today.isoformat(),
            "items": items,
        })
        sources = load(SOURCES, {})
        for rec in items:
            if str(rec.get("id", "")).startswith("osm-"):
                sources[rec["id"]] = {
                    "url": rec.get("kaynak_url"), "il": rec.get("il"),
                    "gorulme": rec.get("son_kontrol"), "durum": rec.get("durum"),
                }
        save(SOURCES, sources)
        save(HISTORY, history)
        old_reviews = load(REVIEW, [])
        seen = {json.dumps(r, sort_keys=True, ensure_ascii=False) for r in old_reviews}
        merged_reviews = old_reviews + [r for r in reviews if json.dumps(r, sort_keys=True, ensure_ascii=False) not in seen]
        save(REVIEW, merged_reviews)
    print(json.dumps({k: v for k, v in summary.items() if k != "iller"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
