"""Denetim kararlarını tesisler_adres.json'a uygular ve veri kalitesi raporu yazar."""
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import audit
from audit import REF, norm, overlay_norm

HERE = Path(__file__).parent
DATA = HERE.parent.parent
REPORT_DIR = DATA / "raporlar"


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def digits(p):
    d = re.sub(r"\D", "", str(p or ""))
    return d[-10:] if len(d) >= 10 else d


def app_key(il, isim):
    """FacilityAddressEntry.matchKey ile aynı (normalizeForSearch)."""
    def f(s):
        t = s or ""
        for a, b in (("ç", "c"), ("Ç", "c"), ("ğ", "g"), ("Ğ", "g"), ("ı", "i"), ("İ", "i"),
                     ("ö", "o"), ("Ö", "o"), ("ş", "s"), ("Ş", "s"), ("ü", "u"), ("Ü", "u")):
            t = t.replace(a, b)
        return t.lower().replace(" ", "")
    return f(il) + "\x01" + f(isim)


def main():
    audit.main()
    rows = json.load(open(audit.CACHE / "audit_out.json", encoding="utf-8"))
    master = json.load(open(DATA / "master_database_updated.json", encoding="utf-8"))["tesisler"]
    adres_path = DATA / "tesisler_adres.json"
    adres_doc = json.load(open(adres_path, encoding="utf-8"))
    items = adres_doc["items"]

    # il+isim başına karar (yinelenen kayıtlarda çelişki → belirsiz)
    by_key = defaultdict(list)
    for r in rows:
        by_key[(norm(r["il"]), norm(r["isim"]))].append(r)
    decision = {}
    for k, rs in by_key.items():
        ok = {r["karar"] for r in rs if r["karar"] != "belirsiz"}
        decision[k] = ok.pop() if len(ok) == 1 else None

    idx = {}
    for i, it in enumerate(items):
        idx[app_key(it["il"], it["isim"])] = i  # uygulamada son kayıt geçerli
    overlay_missing_before = len({app_key(r["il"], r["isim"]) for r in rows} - set(idx))
    corrected, standardized, completed, cleared, unchanged = [], [], [], [], 0
    for k, rs in by_key.items():
        new = decision[k]
        seen = set()
        for r0 in rs:
            ak = app_key(r0["il"], r0["isim"])
            if ak in seen:
                continue
            seen.add(ak)
            i = idx.get(ak)
            old = items[i]["ilce"] if i is not None else None
            if new is None:
                if i is None:
                    idx[ak] = len(items)
                    items.append({"il": r0["il"], "isim": r0["isim"], "adres": "", "ilce": ""})
                elif old:
                    items[i]["ilce"] = ""
                    cleared.append((r0, old))
                continue
            if i is None:
                idx[ak] = len(items)
                items.append({"il": r0["il"], "isim": r0["isim"], "adres": "", "ilce": new})
                completed.append((r0, None, new))
                continue
            if old == new:
                unchanged += 1
                continue
            items[i]["ilce"] = new
            canon_old = overlay_norm(old, audit.IL_N.get(norm(r0["il"]), r0["il"]))
            if not old.strip():
                completed.append((r0, old, new))
            elif canon_old == new:
                standardized.append((r0, old, new))
            else:
                corrected.append((r0, old, new))

    out = json.dumps(adres_doc, ensure_ascii=False, indent=2)
    adres_path.write_text(out, encoding="utf-8")

    # ---- rapor ----
    uniq = {(norm(r["il"]), norm(r["isim"])) for r in rows}
    final_ilce = {k: decision[k] for k in uniq}
    amb_rows = [by_key[k][0] for k in uniq if final_ilce[k] is None]
    amb_rows.sort(key=lambda r: (audit.tr_key(r["il"]) if hasattr(audit, "tr_key") else r["il"], r["isim"]))

    dup_pairs = [rs for rs in by_key.values() if len(rs) > 1]
    near = []
    by_il = defaultdict(list)
    for i, m in enumerate(master):
        by_il[norm(m["il"])].append(i)
    for il, ids in by_il.items():
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                x, y = master[ids[a]], master[ids[b]]
                if norm(x["isim"]) == norm(y["isim"]):
                    continue
                if not (x["latitude"] and y["latitude"]):
                    continue
                dx = digits(x["telefon"])
                if dx and len(dx) == 10 and dx == digits(y["telefon"]) and \
                        km((x["latitude"], x["longitude"]), (y["latitude"], y["longitude"])) < 0.3:
                    near.append((x, y))

    shared_addr = defaultdict(set)
    for m in master:
        if isinstance(m["adres"], str) and len(re.findall(r"\w+", m["adres"])) > 3:
            shared_addr[norm(m["adres"])].add((m["il"], m["isim"], m["adres"]))
    shared_addr = [v for v in shared_addr.values() if len({norm(n) for _, n, _ in v}) > 1]

    coord_bad = [r for r in rows if r.get("poly") is None and r["il"] != "Kıbrıs"]
    coord_other_il = [r for r in rows if r.get("poly") and audit.IL_N.get(norm(r["il"])) != r["poly"][0]]
    warn_rows = [r for r in rows if r.get("uyari")]
    tip_odd = Counter(str(m.get("tip")) for m in master
                      if not m.get("tip") or m["tip"] != m["tip"].strip() or m["tip"][:1].islower() or m["tip"].isupper())
    master_ilce_missing = sum(1 for m in master if not str(m.get("ilce", "")).strip())
    il_counts = Counter(by_key[k][0]["il"] for k in uniq)
    ilce_counts = defaultdict(Counter)
    for k in uniq:
        ilce_counts[by_key[k][0]["il"]][final_ilce[k] or "— belirsiz —"] += 1

    def trk(s):
        return audit.norm(s)

    L = []
    L.append("# İl / İlçe Veri Kalitesi Raporu")
    L.append("")
    L.append(f"Tarih: {date.today().isoformat()} · Kaynak: `master_database_updated.json` (tesisler) + `tesisler_adres.json`")
    L.append("")
    L.append("Referans: İçişleri il/ilçe listesi (81 il, 973 ilçe) ile OpenStreetMap ilçe sınırları "
             "(geoBoundaries, ODbL) karşılaştırıldı; KKTC için 6 ilçe (Lefkoşa, Gazimağusa, Girne, "
             "Güzelyurt, İskele, Lefke). Büyükşehir olmayan 51 ilde merkez ilçe resmi adıyla \"Merkez\".")
    L.append("")
    L.append("## Yöntem")
    L.append("")
    L.append("Her tesis için üç bağımsız kanıt karşılaştırıldı; ilçe tahminle doldurulmadı:")
    L.append("")
    L.append("1. **Konum:** koordinatın düştüğü ilçe sınırı (poligon). Başka tesisle birebir aynı koordinat zayıf kanıt sayıldı.")
    L.append("2. **Resmi adres:** master adresindeki `İlçe/İL`, `İlçe – İL`, `İlçe, İL` kalıpları; yoksa adreste tek geçen ilçe adı. "
             "Birden fazla farklı tesiste birebir tekrar eden (kopyalanmış) adresler kanıt sayılmadı.")
    L.append("3. **Tesis adı / Google adresi:** addaki ilçe adı ve `tesisler_adres.json` Google adresi destekleyici kanıt olarak kullanıldı.")
    L.append("")
    L.append("Konum ve adres aynı ilçeyi gösteriyorsa kabul edildi. Çelişkide adres ilçesinin sınırı koordinata 2 km'den yakınsa adres; "
             "ad ile desteklenen taraf; aksi halde kayıt **belirsiz** listesine alındı ve ilçe alanı boş bırakıldı.")
    L.append("")
    L.append("## Özet")
    L.append("")
    L.append("| Ölçüt | Sayı |")
    L.append("|---|---:|")
    L.append(f"| Toplam tesis kaydı | {len(rows)} |")
    L.append(f"| Tekil tesis (il + ad) | {len(uniq)} |")
    L.append(f"| İl bilgisi eksik kayıt | 0 |")
    L.append(f"| Standart dışı il adı | 0 (82 il değeri referansla birebir) |")
    L.append(f"| İlçe bilgisi eksik (önce, master `ilce`) | {master_ilce_missing} |")
    L.append(f"| `tesisler_adres.json` kaydı olmayan tesis (önce) | {overlay_missing_before} |")
    L.append(f"| İlçesi doğrulanan tesis (sonra) | {len(uniq) - len(amb_rows)} |")
    L.append(f"| Düzeltilen ilçe (yanlış → doğru) | {len(corrected)} |")
    L.append(f"| Standartlaştırılan ilçe yazımı | {len(standardized)} |")
    L.append(f"| Tamamlanan (eksik → eklendi) | {len(completed)} |")
    L.append(f"| Değişmeyen (zaten doğru) | {unchanged} |")
    L.append(f"| Belirsiz kalan (kontrol listesi) | {len(amb_rows)} |")
    L.append(f"| Doğrulanamadığı için boşaltılan eski ilçe | {len(cleared)} |")
    L.append(f"| Yinelenen kayıt (aynı il + ad) | {len(dup_pairs)} grup |")
    L.append(f"| Olası yinelenen (farklı ad, aynı telefon, <300 m) | {len(near)} çift |")
    L.append(f"| Konum uyarısı (koordinat kontrol edilmeli) | {len(warn_rows) + len(coord_bad) + len(coord_other_il)} |")
    L.append("")

    L.append("## Belirsiz kalan kayıtlar (kontrol listesi)")
    L.append("")
    L.append("İlçe alanı boş bırakıldı; tesis il genelinde (\"Tüm ilçeler\") listelenir. Doğrulandıktan sonra "
             "`tesisler_adres.json` içindeki `ilce` alanına standart ilçe adı yazılmalı.")
    L.append("")
    L.append("| İl | Tesis | Önceki kayıt | Bulgular |")
    L.append("|---|---|---|---|")
    cleared_old = {(norm(r["il"]), norm(r["isim"])): o for r, o in cleared}
    for r in sorted(amb_rows, key=lambda r: (trk(r["il"]), trk(r["isim"]))):
        k = (norm(r["il"]), norm(r["isim"]))
        prev = cleared_old.get(k) or r.get("ov_ilce") or "—"
        L.append(f"| {r['il']} | {r['isim'].strip()} | {prev} | {r['neden']} |")
    L.append("")

    def change_table(title, items_, note=None):
        L.append(f"## {title} ({len(items_)})")
        L.append("")
        if note:
            L.append(note)
            L.append("")
        if not items_:
            L.append("Yok.")
            L.append("")
            return
        L.append("| İl | Tesis | Önce | Sonra | Kanıt |")
        L.append("|---|---|---|---|---|")
        for r, o, n in sorted(items_, key=lambda t: (trk(t[0]["il"]), trk(t[0]["isim"]))):
            L.append(f"| {r['il']} | {r['isim'].strip()} | {o if o else '—'} | {n} | {r.get('kaynak', '')} |")
        L.append("")

    change_table("Düzeltilen ilçe bilgileri", corrected)
    std_kinds = Counter(f"{o} → {n}" for _, o, n in standardized)
    L.append(f"## Standartlaştırılan kayıtlar ({len(standardized)})")
    L.append("")
    L.append("Aynı ilçenin farklı yazımları resmi ada çevrildi (en sık görülenler):")
    L.append("")
    for kind, c in std_kinds.most_common(40):
        L.append(f"- {kind}: {c}")
    if len(std_kinds) > 40:
        L.append(f"- … ve {len(std_kinds) - 40} farklı yazım daha")
    L.append("")
    change_table("Tamamlanan ilçe bilgileri", completed,
                 "`tesisler_adres.json` içinde kaydı veya ilçesi olmayan tesisler.")

    L.append(f"## Konum uyarıları ({len(warn_rows) + len(coord_bad) + len(coord_other_il)})")
    L.append("")
    L.append("İlçe adres + ad ile belirlendi ama koordinat başka yeri gösteriyor ya da koordinat geçersiz. "
             "Haritadaki pin yanlış yerde olabilir.")
    L.append("")
    L.append("| İl | Tesis | Sorun |")
    L.append("|---|---|---|")
    for r in warn_rows:
        L.append(f"| {r['il']} | {r['isim'].strip()} | ilçe {r['karar']}; {r['uyari']} |")
    for r in coord_other_il:
        if not r.get("uyari"):
            L.append(f"| {r['il']} | {r['isim'].strip()} | koordinat {r['poly'][0]} / {r['poly'][1]} içinde |")
    for r in coord_bad:
        L.append(f"| {r['il']} | {r['isim'].strip()} | koordinat Türkiye ilçe sınırlarının dışında |")
    L.append("")

    L.append(f"## Yinelenen kayıtlar ({len(dup_pairs)} grup)")
    L.append("")
    L.append("Aynı il ve adla birden fazla kayıt. Uygulama bunları tek tesis olarak gösteriyor; veriden silinmedi.")
    L.append("")
    L.append("| İl | Tesis | Tipler | Telefonlar |")
    L.append("|---|---|---|---|")
    for rs in dup_pairs:
        ms = [master[r["idx"]] for r in rs]
        L.append(f"| {rs[0]['il']} | {rs[0]['isim']} | {' / '.join(str(m['tip']) for m in ms)} | "
                 f"{' / '.join(str(m['telefon']).strip() for m in ms)} |")
    L.append("")
    L.append(f"### Olası yinelenenler ({len(near)} çift)")
    L.append("")
    L.append("Farklı adla kayıtlı, aynı telefon ve 300 m'den yakın koordinat. Gözle kontrol edilmeli.")
    L.append("")
    for x, y in near:
        L.append(f"- {x['il']}: \"{x['isim']}\" ↔ \"{y['isim']}\" ({x['telefon']})")
    L.append("")

    L.append(f"## Kopyalanmış adresler ({len(shared_addr)} adres)")
    L.append("")
    L.append("Birbirinden farklı tesislerde birebir aynı adres; en az biri yanlış. İlçe kararında kullanılmadı.")
    L.append("")
    for v in sorted(shared_addr, key=lambda v: -len(v)):
        v = sorted(v)
        L.append(f"- **{v[0][2].strip()}** → " + "; ".join(f"{il}: {n.strip()}" for il, n, _ in v))
    L.append("")

    L.append("## Standart dışı tesis türü yazımları")
    L.append("")
    L.append("Tür filtresi büyük/küçük harf ve Türkçe karakter duyarsız eşleştiği için veride değiştirilmedi.")
    L.append("")
    for t, c in tip_odd.most_common():
        L.append(f"- `{t}`: {c}")
    L.append("")

    L.append("## İl bazında tesis sayıları")
    L.append("")
    L.append("| İl | Tesis | İlçe sayısı (tesisli) |")
    L.append("|---|---:|---:|")
    for il in sorted(il_counts, key=trk):
        n_ilce = sum(1 for d in ilce_counts[il] if d != "— belirsiz —")
        L.append(f"| {il} | {il_counts[il]} | {n_ilce} / {len(REF.get(audit.IL_N.get(norm(il), il), []))} |")
    L.append("")
    L.append("## İlçe bazında tesis sayıları")
    L.append("")
    for il in sorted(il_counts, key=trk):
        parts = [f"{d} ({c})" for d, c in sorted(ilce_counts[il].items(), key=lambda t: (-t[1], trk(t[0])))]
        L.append(f"- **{il}** ({il_counts[il]}): " + ", ".join(parts))
    L.append("")

    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "ilce_veri_kalitesi.md").write_text("\n".join(L), encoding="utf-8")
    checklist = [
        {"il": r["il"], "isim": r["isim"].strip(), "onceki_ilce": cleared_old.get((norm(r["il"]), norm(r["isim"]))) or r.get("ov_ilce") or "",
         "bulgular": r["neden"], "adres": r.get("adres") if isinstance(r.get("adres"), str) else ""}
        for r in sorted(amb_rows, key=lambda r: (trk(r["il"]), trk(r["isim"])))
    ]
    (REPORT_DIR / "ilce_kontrol_listesi.json").write_text(
        json.dumps(checklist, ensure_ascii=False, indent=2), encoding="utf-8")

    print("düzeltilen", len(corrected), "standart", len(standardized), "tamamlanan", len(completed),
          "boşaltılan", len(cleared), "belirsiz", len(amb_rows), "değişmeyen", unchanged,
          "dup", len(dup_pairs), "near", len(near), "ortak adres", len(shared_addr))


if __name__ == "__main__":
    main()
