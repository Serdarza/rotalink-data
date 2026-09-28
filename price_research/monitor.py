#!/usr/bin/env python3
"""RotaLink aylık resmî fiyat kontrolü.

Akış: kaynak kaydını oku → resmî kaynakları nazikçe indir (koşullu GET, hız sınırı, yeniden deneme)
→ HTML/PDF/Word/Excel/görsel (OCR) metnini çıkar → her tesisin mevcut tarifesindeki rakamlar resmî
kaynakta hâlâ geçiyor mu, dönem bitti mi kontrol et → yeni 2026 tarife/kaynak adaylarını ve yeni
tesisleri keşfet → (canlı modda) yalnızca durum işaretlerini güncelle, doğrula, atomik yaz → rapor üret.

Fiyat rakamları otomatik olarak YAZILMAZ ve SİLİNMEZ. Değişen/süresi dolan tarife
`tarife.dogrulama = "teyit_gerekli"` olarak işaretlenir ve raporlanır; yeni fiyat, rapordaki resmî
kaynaktan onaylanarak girilir. Erişim hatasında veriye dokunulmaz (kayıtta source_check_failed).

Kullanım:
  python price_research/monitor.py [--dry-run] [--limit N] [--il İL] [--no-ocr] [--no-discovery]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import (FILE_EXT_RE, PRICE_WORD_RE, Fetcher, digits, extract, mentions_year, norm,  # noqa: E402
                    resmi_alan_adi, source_numbers, tarife_expired, tarife_prices)
from validate import master_keys, new_errors, validate_data  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PR = ROOT / "price_research"
REPORTS = PR / "reports"
AUTO_NOTE = "Otomatik aylık resmî kaynak kontrolü"
KEYWORDS_RE = re.compile(r"misafirhane|konuk ?evi|sosyal tesis|konaklama|uygulama otel|kamp|orduevi|polis ?evi|"
                         r"[oö][gğ]retmen ?evi|e[gğ]itim (ve dinlenme )?tesis|dinlenme tesis|fiyat|[uü]cret|tarife", re.I)
PRICE_RANGE = (100.0, 100000.0)
NON_LODGING_RE = re.compile(r"organizasyon|restoran|restorant|yemek|men[uü]|spor|salon|d[uü][gğ][uü]n|toplant[iı]|"
                            r"kantin|kafeterya|otopark|ihale|taahh[uü]t|kira", re.I)


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, data, validate_fn=None) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2 if path.name == "fiyatlar.json" else 1) + "\n",
                   encoding="utf-8")
    json.loads(tmp.read_text(encoding="utf-8"))
    if validate_fn:
        errs = validate_fn(load(tmp))
        if errs:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"{path.name} doğrulamadan geçmedi, yazılmadı: {errs[:5]}")
    os.replace(tmp, path)


# ------------------------------------------------------------------ URL işleme

IMG_SKIP_RE = re.compile(r"logo|icon|ikon|banner|sprite|avatar|flag|bayrak|\.gif|\.svg|/assets/|/tema/|/theme", re.I)
IMG_RE = re.compile(r"\.(jpe?g|png|webp)(\?|#|$)", re.I)


def embedded_images(page_url: str, links: list, limit: int = 6) -> list[str]:
    host = urlparse(page_url).hostname or ""
    out = []
    for u, _t in links:
        if IMG_RE.search(u) and not IMG_SKIP_RE.search(u) and (urlparse(u).hostname or "") == host and u not in out:
            out.append(u)
    return out[:limit]


def process_url(fetcher: Fetcher, url: str, prev: dict, use_ocr: bool, year: int, embed: bool = False) -> dict:
    fr = fetcher.get(url, etag=prev.get("etag"), last_modified=prev.get("last_modified"))
    out = {"url": url, "ok": fr.ok, "http": fr.status, "hata": fr.error, "degisti": None, "sayilar": set(),
           "yil_var": False, "tur": None, "ocr": False, "cikarim_hatasi": None, "linkler": [], "sha": prev.get("sha")}
    if not fr.ok:
        return out
    if fr.not_modified:
        out.update(degisti=False, sayilar=set(prev.get("sayilar") or []), yil_var=bool(prev.get("yil_var")),
                   yil_fiyat=bool(prev.get("yil_fiyat")), tur=prev.get("tur"), linkler=prev.get("linkler") or [])
        return out
    kind = common.detect_kind(url, fr.ctype)
    if kind == "gorsel" and not use_ocr:
        ex = common.Extracted("", "gorsel", error="OCR kapalı")
    else:
        ex = extract(url, fr.content, fr.ctype)
    out.update(tur=ex.kind, ocr=ex.ocr_used, cikarim_hatasi=ex.error, sha=fr.sha256, etag=fr.etag,
               last_modified=fr.last_modified, degisti=(prev.get("sha") is not None and prev.get("sha") != fr.sha256))
    text = ex.text
    if embed and use_ocr and ex.kind == "web" and not ex.error:
        for iu in embedded_images(url, ex.links):
            ir = fetcher.get(iu)
            if ir.ok and ir.content:
                try:
                    text += "\n[OCR]\n" + common.ocr_image_bytes(ir.content)
                    out["ocr"] = True
                except Exception:  # noqa: BLE001
                    pass
    out["sayilar"] = {n for n in source_numbers(text) if PRICE_RANGE[0] <= n <= PRICE_RANGE[1]}
    out["yil_var"] = mentions_year(ex.text, year)
    out["yil_fiyat"] = common.year_price_phrase(ex.text, year)
    out["linkler"] = [(u, t) for u, t in ex.links if u.startswith("http") and
                      (FILE_EXT_RE.search(u) or PRICE_WORD_RE.search(f"{u} {t}"))][:120]
    return out


def candidate_links(res: dict, known: set[str], year: int) -> list[str]:
    """Sayfadaki, kayıtta olmayan, fiyat/2026 işaretli resmî dosya ve sayfa bağlantıları."""
    out = []
    for u, txt in res.get("linkler") or []:
        if u in known or not resmi_alan_adi(u):
            continue
        blob = f"{u} {txt}"
        if NON_LODGING_RE.search(blob):
            continue
        if re.search(rf"20(1\d|2[0-{(year - 1) % 10}])", blob) and not mentions_year(blob, year) and f"/{year}_" not in u:
            continue
        m = FILE_EXT_RE.search(u)
        is_doc = bool(m) and m.group(1).lower() in ("pdf", "doc", "docx", "xls", "xlsx")
        has_year = f"/{year}_" in u or mentions_year(blob, year)
        priced = bool(PRICE_WORD_RE.search(blob))
        if (m and priced) or (is_doc and has_year) or (not m and has_year and priced):
            out.append(u)
    return sorted(set(out))


# ------------------------------------------------------------- tesis kontrolü

def evaluate(t: dict, entry: dict | None, url_res: dict, url_state: dict, known: set[str], today: date) -> dict:
    year = today.year
    srcs = t.get("kaynaklar") or []
    res = [url_res[s["url"]] for s in srcs if s["url"] in url_res]
    ok = [r for r in res if r["ok"]]
    adaylar = sorted({c for s, r in zip(srcs, res) if r["ok"] and s["rol"] in ("sayfa", "ana_sayfa")
                      for c in candidate_links(r, known, year)})
    base = {"il": t["il"], "isim": t["isim"], "kurum": t.get("kurum"),
            "kaynak": next((s["url"] for s in srcs if s["rol"] == "fiyat"), srcs[0]["url"] if srcs else None),
            "yeni_kaynak_adaylari": adaylar[:20],
            "erisilemeyen": [{"url": r["url"], "http": r["http"], "hata": r["hata"]} for r in res if not r["ok"]]}
    if not res:
        return {**base, "sonuc": "kontrol_edilmedi"}
    if not ok:
        return {**base, "sonuc": "source_check_failed"}

    tarife = (entry or {}).get("tarife") or {}
    prices = set(tarife_prices(tarife))
    if t.get("kontrol_yontemi") == "rakam_dogrulama" and prices:
        price_srcs = [(s, url_res.get(s["url"])) for s in srcs if s["rol"] in ("fiyat", "fiyat_ek", "sayfa")]
        main_src = next(((s, r) for s, r in price_srcs if s["rol"] == "fiyat"), None)
        if main_src and (main_src[1] is None or not main_src[1]["ok"]):
            return {**base, "sonuc": "source_check_failed"}
        reach = [(s, r) for s, r in price_srcs if r and r["ok"] and not (r.get("cikarim_hatasi") and not r["sayilar"])]
        if not any(s["rol"] in ("fiyat", "fiyat_ek") for s, _ in reach):
            if tarife_expired(tarife, today):
                return {**base, "sonuc": "suresi_doldu", "donem": tarife.get("donem")}
            hata = next((r.get("cikarim_hatasi") for _, r in price_srcs if r and r.get("cikarim_hatasi")), None)
            return {**base, "sonuc": "islenemedi", "hata": hata}
        nums = set().union(*[r["sayilar"] for _, r in reach]) if reach else set()
        missing = sorted(prices - nums - {float(x) for x in t.get("ocr_eksik") or []})
        same_bytes = bool(reach) and all(
            r["sha"] and url_state.get(s["url"], {}).get("dogrulanan_sha") == r["sha"] for s, r in reach)
        if tarife_expired(tarife, today):
            return {**base, "sonuc": "suresi_doldu", "donem": tarife.get("donem")}
        # Çelişki: tarife dosyalarından biri mevcut rakamları tam içerirken başka bir güncel dosya çok farklıysa
        full = [s for s, r in reach if prices <= (r["sayilar"] | {float(x) for x in t.get("ocr_eksik") or []})]
        odd = [s for s, r in reach if s["rol"] in ("fiyat", "fiyat_ek") and r["degisti"] and r["yil_var"]
               and len(prices & r["sayilar"]) < 0.5 * len(prices) and len(r["sayilar"] - prices) >= 5]
        if full and odd:
            return {**base, "sonuc": "celiski", "celisen_kaynaklar": [s["url"] for s in odd]}
        if not missing or same_bytes:
            return {**base, "sonuc": "dogrulandi"}
        new_nums = sorted(set().union(*[r["sayilar"] for s, r in reach if s["rol"] in ("fiyat", "fiyat_ek")]) - prices)
        return {**base, "sonuc": "degisti", "kaynakta_bulunmayan_mevcut_fiyatlar": missing,
                "kaynaktaki_yeni_aday_rakamlar": new_nums[:60]}

    # Güncel resmî tarifesi olmayan tesis: yeni tarife yayımlanmış mı?
    signal = any(r.get("yil_fiyat") and r["degisti"] is not False for r in ok) or bool(adaylar)
    return {**base, "sonuc": "olasi_yeni_tarife" if signal else "guncel_fiyat_bulunamadi"}


# ------------------------------------------------------------------ keşif

def discover_kurumlar(fetcher: Fetcher, kurumlar: list[dict], known: set[str], year: int, deadline: float) -> list[dict]:
    out = []
    for k in kurumlar:
        if time.monotonic() > deadline:
            break
        root = fetcher.get(k["url"])
        if not root.ok or not root.content:
            out.append({"kurum": k["ad"], "url": k["url"], "durum": "erisilemedi", "hata": root.error or root.status})
            continue
        ex = extract(k["url"], root.content, root.ctype)
        host = (urlparse(k["url"]).hostname or "").removeprefix("www.")
        pages = [u for u, txt in ex.links if host in (urlparse(u).hostname or "") and KEYWORDS_RE.search(f"{u} {txt}")]
        cands = set()
        for u in sorted(set(pages))[:8]:
            if u in known:
                continue
            fr = fetcher.get(u)
            if not fr.ok or not fr.content:
                continue
            sub = extract(u, fr.content, fr.ctype)
            if KEYWORDS_RE.search(sub.text[:20000]) and (PRICE_WORD_RE.search(sub.text) or mentions_year(sub.text, year)):
                cands.add(u)
            for lu, lt in sub.links:
                if lu not in known and FILE_EXT_RE.search(lu) and KEYWORDS_RE.search(f"{lu} {lt}"):
                    cands.add(lu)
        out.append({"kurum": k["ad"], "url": k["url"], "durum": "tarandi", "aday_sayfalar": sorted(cands)[:25]})
    return out


def discover_meb(fetcher: Fetcher, url: str, master: list[dict]) -> dict:
    fr = fetcher.get(url)
    if not fr.ok or not fr.content:
        return {"durum": "erisilemedi", "hata": fr.error or fr.status, "yeni": []}
    import html as htmlmod
    raw = fr.content.decode("utf-8", "replace")
    rows = re.findall(r"lbl_il[^>]*>([^<]*)</span>.*?lbl_ilce[^>]*>([^<]*)</span>.*?"
                      r"lbl_kurum[^>]*>([^<]*)</span>.*?lbl_telefon[^>]*>([^<]*)</span>", raw, re.S)
    by_il: dict[str, list[dict]] = {}
    for t in master:
        by_il.setdefault(norm(t.get("il")), []).append(t)
    generic = {"ogretmenevi", "ogretmen", "evi", "ve", "aso", "aksam", "sanat", "okulu", "mudurlugu", "sehit"}
    yeni = []
    for il, ilce, kurum, tel in rows:
        il, ilce, kurum, tel = (htmlmod.unescape(x).strip() for x in (il, ilce, kurum, tel))
        cands = by_il.get(norm(il), [])
        toks = set(norm(kurum).split()) - generic
        d = digits(tel)
        hit = False
        for t in cands:
            if d and d == digits(str(t.get("telefon") or "")):
                hit = True
                break
            mt = set(norm(t.get("isim")).split())
            if ("retmen" in norm(t.get("isim")) or "aso" in mt) and (toks & mt or norm(ilce) in norm(t.get("isim"))):
                hit = True
                break
        if not hit:
            yeni.append({"il": il, "ilce": ilce, "kurum": kurum, "telefon": tel, "durum": "DISCOVERED"})
    return {"durum": "tarandi", "liste_satiri": len(rows), "yeni": yeni}


def discover_polis(fetcher: Fetcher, hosts: list[str], known: set[str], deadline: float) -> list[dict]:
    out = []
    kw = re.compile(r"polis ?evi|sosyal tesis|misafirhane|konaklama|fiyat|kamp", re.I)
    for h in hosts:
        if time.monotonic() > deadline:
            break
        url = f"https://{h}/"
        fr = fetcher.get(url)
        if not fr.ok or not fr.content:
            out.append({"site": h, "durum": "erisilemedi"})
            continue
        ex = extract(url, fr.content, fr.ctype)
        c = sorted({u for u, t in ex.links if h in u and kw.search(f"{u} {t}") and u not in known})
        out.append({"site": h, "durum": "tarandi", "aday_sayfalar": c[:15]})
    return out


# ------------------------------------------------------------------- ana akış

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--il")
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--no-discovery", action="store_true")
    ap.add_argument("--today")
    a = ap.parse_args()

    cfg = load(PR / "config.json")
    env_dry = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    live = bool(cfg.get("canli")) and not a.dry_run and not env_dry
    today = date.fromisoformat(a.today) if a.today else datetime.now(timezone.utc).date()
    t0 = time.monotonic()
    deadline = t0 + 60 * float(cfg.get("azami_dakika", 300))
    print(f"mod: {'CANLI' if live else 'DRY RUN'} | tarih {today}")

    reg = load(PR / "sources.json")
    fiyat_path = ROOT / "fiyatlar.json"
    fiyat = load(fiyat_path)
    mkeys = master_keys(ROOT)
    before_errs = validate_data(fiyat, mkeys)
    master = load(ROOT / "master_database_updated.json")["tesisler"]
    idx = {(e["il"], e["isim"]): i for i, e in enumerate(fiyat["tesisler"])}
    url_state: dict = reg.setdefault("url_durumu", {})
    common.RESMI_EK = set(reg.get("onayli_alan_adlari") or [])

    tesisler = reg["tesisler"]
    if a.il:
        tesisler = [t for t in tesisler if t["il"] == a.il]
    active = [t for t in tesisler if t.get("aktif")]
    if a.limit:
        active = active[: a.limit]
    known = {s["url"] for t in reg["tesisler"] for s in t.get("kaynaklar") or []}
    urls = sorted({s["url"] for t in active for s in t.get("kaynaklar") or []})
    embed_urls = {s["url"] for t in active if t.get("kontrol_yontemi") == "rakam_dogrulama"
                  for s in t.get("kaynaklar") or [] if s["rol"] in ("fiyat", "fiyat_ek")}
    print(f"aktif tesis {len(active)} | benzersiz kaynak {len(urls)}")

    fetcher = Fetcher(per_host_delay=float(cfg.get("host_bekleme_sn", 1.5)), timeout=float(cfg.get("zaman_asimi_sn", 40)),
                      retries=int(cfg.get("yeniden_deneme", 3)))
    url_res: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=int(cfg.get("paralel", 8))) as ex:
        futs = {}
        for u in urls:
            futs[ex.submit(process_url, fetcher, u, url_state.get(u, {}), not a.no_ocr, today.year,
                             u in embed_urls)] = u
        for n, f in enumerate(as_completed(futs), 1):
            u = futs[f]
            try:
                url_res[u] = f.result()
            except Exception as e:  # noqa: BLE001
                url_res[u] = {"url": u, "ok": False, "http": None, "hata": f"{type(e).__name__}: {e}"[:300],
                              "sayilar": set(), "linkler": [], "degisti": None, "sha": None, "yil_var": False}
            if n % 100 == 0:
                print(f"  kaynak {n}/{len(urls)}  ({int(time.monotonic() - t0)} sn)", flush=True)
            if time.monotonic() > deadline:
                print("  süre sınırı: kalan kaynaklar bu ay kontrol edilmedi")
                for ff in futs:
                    ff.cancel()
                break

    # Tesis değerlendirme + (canlı) işaret güncellemesi
    results, changes = [], []
    today_s = today.isoformat()
    today_tr = today.strftime("%d.%m.%Y")
    new_list = list(fiyat["tesisler"])
    for t in active:
        key = (t["il"], t["isim"])
        entry = new_list[idx[key]] if key in idx else None
        r = evaluate(t, entry, url_res, url_state, known, today)
        results.append(r)
        t["son_kontrol"] = today_s
        t["son_sonuc"] = r["sonuc"]
        if r["sonuc"] not in ("source_check_failed", "kontrol_edilmedi"):
            t["son_basarili_kontrol"] = today_s
        if r["sonuc"] == "dogrulandi":
            for s in t.get("kaynaklar") or []:
                rr = url_res.get(s["url"])
                if rr and rr["ok"] and rr["sha"]:
                    url_state.setdefault(s["url"], {})["dogrulanan_sha"] = rr["sha"]
        if entry is None or not isinstance(entry.get("tarife"), dict):
            continue
        tar = dict(entry["tarife"])
        notlar = [n for n in tar.get("notlar") or [] if not n.startswith(AUTO_NOTE)]
        if r["sonuc"] in ("degisti", "suresi_doldu") and tar.get("dogrulama") == "resmi_kaynak":
            why = ("tarife döneminin sona erdiği" if r["sonuc"] == "suresi_doldu"
                   else "resmî kaynaktaki tarifenin değiştiği")
            notlar.append(f"{AUTO_NOTE} ({today_tr}): {why} tespit edildi; bu fiyatlar güncel olmayabilir, "
                          f"rezervasyon öncesi tesisle teyit ediniz.")
            tar.update(dogrulama="teyit_gerekli", notlar=notlar)
            changes.append({"tesis": f"{t['il']} / {t['isim']}", "islem": "teyit_gerekli olarak işaretlendi",
                            "neden": r["sonuc"], "eski_fiyat": {k: entry.get(k) for k in
                            ("fiyat_kurum_personeli", "fiyat_kamu_personeli", "fiyat_sivil")},
                            "yeni_fiyat": "resmî kaynaktan onayla girilecek",
                            "kaynakta_bulunmayan_mevcut_fiyatlar": r.get("kaynakta_bulunmayan_mevcut_fiyatlar"),
                            "kaynaktaki_yeni_aday_rakamlar": r.get("kaynaktaki_yeni_aday_rakamlar"),
                            "resmi_kaynak": r["kaynak"], "kontrol_tarihi": today_s})
            t["otomatik_isaret"] = today_s
        elif r["sonuc"] == "dogrulandi" and t.get("otomatik_isaret") and tar.get("dogrulama") == "teyit_gerekli":
            tar.update(dogrulama="resmi_kaynak", notlar=notlar)
            t.pop("otomatik_isaret", None)
            changes.append({"tesis": f"{t['il']} / {t['isim']}", "islem": "yeniden resmi_kaynak (tarife resmî kaynakta tekrar doğrulandı)",
                            "resmi_kaynak": r["kaynak"], "kontrol_tarihi": today_s})
        else:
            continue
        if not tar.get("notlar"):
            tar.pop("notlar", None)
        new_list[idx[key]] = {**entry, "tarife": tar}

    for u, rr in url_res.items():
        st = url_state.setdefault(u, {})
        st.update(son_kontrol=today_s, son_http=rr.get("http"), son_hata=rr.get("hata"))
        if rr["ok"]:
            st["son_basarili"] = today_s
            if rr.get("sha"):
                st.update(sha=rr["sha"], etag=rr.get("etag") or st.get("etag"),
                          last_modified=rr.get("last_modified") or st.get("last_modified"),
                          sayilar=sorted(rr["sayilar"])[:300], yil_var=rr["yil_var"], yil_fiyat=rr.get("yil_fiyat"),
                          tur=rr.get("tur"), linkler=[list(x) for x in rr.get("linkler", [])[:60]])

    # Keşif
    kesif = {}
    if not a.no_discovery and not a.limit and not a.il:
        kur = load(PR / "kurumlar.json")
        kesif["meb"] = discover_meb(fetcher, kur["ozel_kaynaklar"]["meb_ogretmenevi_listesi"], master)
        kesif["polis"] = discover_polis(fetcher, kur.get("emniyet_siteleri") or [], known, deadline)
        kesif["kurumlar"] = discover_kurumlar(fetcher, kur["kurumlar"], known, today.year, deadline)

    # Yazma (canlı)
    wrote = False
    if live:
        cand = {**fiyat, "tesisler": new_list}
        if changes:
            atomic_write_json(fiyat_path, cand, lambda d: new_errors(before_errs, validate_data(d, mkeys)))
            wrote = True
        atomic_write_json(PR / "sources.json", reg)

    report = build_report(results, url_res, changes, kesif, live, wrote, today, before_errs, time.monotonic() - t0,
                          [t for t in tesisler if not t.get("aktif")])
    REPORTS.mkdir(parents=True, exist_ok=True)
    suffix = "" if live else "_dry_run"
    (REPORTS / f"latest{suffix}.json").write_text(json.dumps(report["json"], ensure_ascii=False, indent=1), encoding="utf-8")
    (REPORTS / f"latest{suffix}.md").write_text(report["md"], encoding="utf-8")
    if live:
        (REPORTS / f"{today:%Y-%m}.md").write_text(report["md"], encoding="utf-8")
        if changes:
            with open(REPORTS / "degisiklikler.log", "a", encoding="utf-8") as fh:
                for c in changes:
                    fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(report["md"][:60000])
    print(report["md"].split("\n## ")[0])
    return 0


def build_report(results, url_res, changes, kesif, live, wrote, today, legacy_errs, secs, pasif) -> dict:
    c = Counter(r["sonuc"] for r in results)
    ok_urls = [r for r in url_res.values() if r["ok"]]
    bad_urls = [r for r in url_res.values() if not r["ok"]]
    kinds = Counter(r.get("tur") for r in url_res.values() if r.get("cikarim_hatasi"))
    ocr = sum(1 for r in url_res.values() if r.get("ocr"))
    yeni_tesis = (kesif.get("meb") or {}).get("yeni") or []
    aday_kaynak = sum(1 for r in results if r.get("yeni_kaynak_adaylari"))
    stats = {
        "Toplam kaynak": len(url_res), "Başarılı kaynak": len(ok_urls), "Başarısız kaynak": len(bad_urls),
        "Kontrol edilen tesis": len(results),
        "Güncel resmî fiyatı doğrulanan tesis": c["dogrulandi"],
        "Fiyatı değişmiş görünen tesis": c["degisti"],
        "Fiyatı değişmeyen tesis": c["dogrulandi"],
        "Tarife dönemi sona eren tesis": c["suresi_doldu"],
        "Olası yeni 2026 tarifesi olan tesis": c["olasi_yeni_tarife"],
        "Güncel fiyat bulunamayan tesis": c["guncel_fiyat_bulunamadi"] + len(pasif),
        "Kaynağı erişilemeyen tesis (source_check_failed)": c["source_check_failed"],
        "Çelişkili kaynak (CONFLICT)": c["celiski"],
        "Kaynağı okunamayan tesis (işlenemedi)": c["islenemedi"],
        "Yeni kaynak adayı bulunan tesis": aday_kaynak,
        "Yeni keşfedilen tesis (DISCOVERED)": len(yeni_tesis),
        "İşlenemeyen PDF": kinds.get("pdf", 0), "İşlenemeyen Excel": kinds.get("excel", 0),
        "İşlenemeyen Word": kinds.get("word", 0), "OCR uygulanan dosya": ocr,
        ("fiyatlar.json'da işaret değişikliği" if live else
         "fiyatlar.json'da yapılacak işaret değişikliği (DRY RUN — uygulanmadı)"): len(changes),
        "Mevcut veride bilinen eski sorun": len(legacy_errs),
    }
    L = [f"# Aylık resmî fiyat kontrolü — {today:%d.%m.%Y} ({'CANLI' if live else 'DRY RUN'})", "",
         f"Süre: {int(secs // 60)} dk. fiyatlar.json {'güncellendi' if wrote else 'değiştirilmedi'}.", ""]
    L += [f"- {k}: **{v}**" for k, v in stats.items()]

    def sec(title, rows):
        L.extend(["", f"## {title} ({len(rows)})", ""])
        L.extend(rows or ["- yok"])

    sec("Değişiklik günlüğü", [f"- {x['tesis']} — {x['islem']} ({x.get('neden', '')}); eski: {x.get('eski_fiyat')}; "
                              f"kaynakta bulunmayan: {x.get('kaynakta_bulunmayan_mevcut_fiyatlar')}; yeni aday rakamlar: "
                              f"{x.get('kaynaktaki_yeni_aday_rakamlar')}; kaynak: {x['resmi_kaynak']}" for x in changes])
    sec("Fiyatı değişmiş görünen", [f"- {r['il']} / {r['isim']} — bulunmayan {r['kaynakta_bulunmayan_mevcut_fiyatlar']} — "
                                    f"yeni aday {r['kaynaktaki_yeni_aday_rakamlar'][:15]} — {r['kaynak']}"
                                    for r in results if r["sonuc"] == "degisti"])
    sec("Tarife dönemi sona eren", [f"- {r['il']} / {r['isim']} — {r.get('donem')} — {r['kaynak']}"
                                    for r in results if r["sonuc"] == "suresi_doldu"])
    sec("Çelişkili kaynak (CONFLICT)", [f"- {r['il']} / {r['isim']} — {r.get('celisen_kaynaklar')}"
                                        for r in results if r["sonuc"] == "celiski"])
    sec("Kaynağı okunamayan (işlenemedi — veri korunur)", [f"- {r['il']} / {r['isim']} — {r.get('hata')} — {r['kaynak']}"
                                                           for r in results if r["sonuc"] == "islenemedi"])
    sec("Olası yeni 2026 tarifesi", [f"- {r['il']} / {r['isim']} — {r['kaynak']} — adaylar: {r['yeni_kaynak_adaylari'][:5]}"
                                     for r in results if r["sonuc"] == "olasi_yeni_tarife"])
    sec("Yeni kaynak adayları (doğrulanmış tesisler)", [f"- {r['il']} / {r['isim']} — {r['yeni_kaynak_adaylari'][:5]}"
                                                        for r in results if r["sonuc"] == "dogrulandi" and r["yeni_kaynak_adaylari"]])
    sec("Kaynağı erişilemeyen (source_check_failed — veri korunur)",
        [f"- {r['il']} / {r['isim']} — {r['erisilemeyen'][:2]}" for r in results if r["sonuc"] == "source_check_failed"])
    sec("Yeni keşfedilen tesisler (DISCOVERED — otomatik eklenmez)",
        [f"- {x['il']} / {x['ilce']} — {x['kurum']} — {x['telefon']}" for x in yeni_tesis])
    kur = kesif.get("kurumlar") or []
    sec("Kurum sitelerinde aday konaklama/fiyat sayfaları",
        [f"- {k['kurum']}: {k.get('aday_sayfalar')}" for k in kur if k.get("aday_sayfalar")] +
        [f"- {k['kurum']}: erişilemedi ({k.get('hata')})" for k in kur if k.get("durum") == "erisilemedi"])
    pol = kesif.get("polis") or []
    sec("Emniyet sitelerinde aday polisevi sayfaları", [f"- {p['site']}: {p['aday_sayfalar']}" for p in pol if p.get("aday_sayfalar")])
    sec("Güncel fiyat bulunamayan (aktif kontrol)", [f"- {r['il']} / {r['isim']} — {r['kaynak']}"
                                                     for r in results if r["sonuc"] == "guncel_fiyat_bulunamadi"])
    sec("Resmî kaynağı olmayan / pasif", [f"- {t['il']} / {t['isim']} — {t.get('neden') or ''}"[:300] for t in pasif])
    sec("Mevcut veride bilinen eski sorunlar (bu iş değiştirmez)", [f"- {e}" for e in legacy_errs])
    js = {"tarih": today.isoformat(), "canli": live, "fiyatlar_guncellendi": wrote, "istatistik": stats,
          "degisiklikler": changes, "sonuclar": results, "kesif": kesif}
    return {"md": "\n".join(L) + "\n", "json": js}


if __name__ == "__main__":
    sys.exit(main())
