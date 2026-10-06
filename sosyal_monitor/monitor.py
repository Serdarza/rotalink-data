"""Belediye sosyal tesisleri — 3 aylık Google Places taraması.

master_database_updated.json içindeki `sosyal` listesini canlı tutar:
  * Google "kalıcı olarak kapandı" (CLOSED_PERMANENTLY) diyen tesis listeden çıkar,
    kayıt silinmez: sosyal_monitor/kaldirilanlar.json arşivine taşınır.
  * Yeni açılan belediye sosyal tesisleri eklenir.
  * Emin olunamayanlar (bulunamayan, geçici kapalı) yalnızca rapora yazılır.

Güvenlik: API hatası oranı yüksekse veya tek çalıştırmada çok fazla ekleme /
çıkarma çıkarsa hiçbir değişiklik uygulanmaz. Anahtar: GOOGLE_PLACES_API_KEY.

Maliyet freni: Text Search Pro'nun aylık 5.000 ücretsiz isteği aşılmasın diye bir
çalıştırma en fazla MAX_CALLS_PER_RUN, aynı aydaki tüm çalıştırmalar toplam
MONTHLY_CALL_CAP istek atar. Sayaç state.json içindeki `aylik_cagri` alanındadır.
Sınıra takılan tarama hiçbir değişiklik uygulamaz.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
MASTER = ROOT / "master_database_updated.json"
STATE = HERE / "state.json"
ARCHIVE = HERE / "kaldirilanlar.json"
REPORTS = HERE / "reports"
IL_ILCE = json.loads((HERE / "il_ilce.json").read_text(encoding="utf-8"))

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
MAX_REMOVE_RATIO = 0.05
MIN_REMOVE_CAP = 5
MAX_ADD = 150
# İlk başarılı taramada (state.json'da son_tarama yok) birikmiş eksikler bir defalık eklenir.
MAX_ADD_FIRST = 600
MAX_ERROR_RATIO = 0.2
MATCH_MIN = 0.75
REMOVE_MIN = 0.9
DUP_MIN = 0.85
DISCOVERY_QUERIES = ("{il} belediyesi sosyal tesisleri", "{il} belediye sosyal tesis kafe")
DISCOVERY_PAGES = 3
MAX_CALLS_PER_RUN = 2000
MONTHLY_CALL_CAP = 4500

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
SEARCH_FIELDS = (
    "places.id,places.displayName,places.formattedAddress,places.businessStatus,"
    "places.types,nextPageToken"
)

_FOLD = str.maketrans("çÇğĞıIİöÖşŞüÜâÂîÎûÛ", "ccggiiioossuuaaiiuu")
_NAME_OK = re.compile(r"sosyal tesis|belediye", re.I)
_NAME_SERVICE = re.compile(r"sosyal tesis|kafe|cafe|restoran|lokanta|kır|çay bahçesi|tesis|mesire", re.I)
# Kamu kurumlarının tesisleri belediye sosyal tesisi değildir; konaklama verisinde ayrı tutulur.
_NAME_EXCLUDE = re.compile(
    r"polis|emniyet|jandarma|ordu ?evi|asker|garnizon|hava kuvvet|kara kuvvet|deniz kuvvet|"
    r"öğretmen|ogretmen|dsi\b|dsİ\b|tcdd|karayolları|ptt|valilik|üniversite|universite|hastane|"
    r"okul|cami|belediye başkanlığı|belediyesi$|hizmet binası|zabıta|itfaiye|müdürlüğü|"
    r"tbmm|merkez bankas|iller bankas|teiaş|tedaş|botaş|tüpraş|tapu|takav|il özel idaresi|"
    r"odası|\bjmo\b|vakf|sendika|kooperatif|spor|düğün|nikah|salon|havuz|tır ?park",
    re.I,
)
# Otomatik ekleme yalnız belediyeye ait olduğu adından belli olan yerler için.
_NAME_MUNICIPAL = re.compile(
    r"belediye|büyükşehir|buyuksehir|\bbld\b|\bbel\.|\babb\b|\bibb\b|beltur|belpa|burfaş|buski|kaytur",
    re.I,
)
_TYPE_EXCLUDE = {"city_hall", "local_government_office", "courthouse", "police", "school", "mosque"}


def fold(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").translate(_FOLD).lower())).strip()


def record_key(il: str, isim: str) -> str:
    return f"{fold(il)}|{fold(isim)}"


_GENERIC = {
    "belediye", "belediyesi", "buyuksehir", "sosyal", "tesis", "tesisi", "tesisleri", "tesisler",
    "ve", "kafe", "cafe", "kafeterya", "restoran", "restaurant", "lokanta", "lokantasi", "kir",
    "kahvesi", "cay", "bahcesi", "mesire", "alani", "kompleksi", "merkezi", "park", "parki",
}


def core(name: str) -> str:
    """Ortak kelimeler atılmış ayırt edici ad: 'Çilimli Belediyesi Sosyal Tesisi' → 'cilimli'."""
    return " ".join(w for w in fold(name).split() if w not in _GENERIC)


def similarity(a: str, b: str) -> float:
    ca, cb = core(a), core(b)
    if not ca or not cb:
        return 1.0 if fold(a) == fold(b) else 0.0
    return difflib.SequenceMatcher(None, ca, cb).ratio()


def address_has_il(address: str, il: str) -> bool:
    return f" {fold(il)} " in f" {fold(address)} "


def canonical_ilce(il: str, raw: str) -> str:
    ilceler = IL_ILCE.get(il) or []
    k = fold(raw).replace(" ", "")
    for d in ilceler:
        if fold(d).replace(" ", "") == k:
            return d
    return ""


def ilce_from_address(il: str, address: str) -> str:
    """'..., 01170 Çukurova/Adana, Türkiye' → 'Çukurova' (resmi listede varsa)."""
    for m in re.finditer(r"([^,/\d]+)/\s*([^,]+)", address or ""):
        if fold(m.group(2)) == fold(il):
            return canonical_ilce(il, m.group(1).strip())
    return ""


def display_name(place: dict) -> str:
    return ((place.get("displayName") or {}).get("text") or "").strip()


def clean_address(address: str) -> str:
    return re.sub(r",\s*(Türkiye|Turkey)$", "", (address or "").strip())


class CallBudgetExceeded(Exception):
    """İstek sınırı doldu; RuntimeError değildir, tek arama hatası gibi yutulmaz."""


class PlacesClient:
    def __init__(self, api_key: str, max_calls: int):
        import requests

        self._s = requests.Session()
        self._s.headers.update({"X-Goog-Api-Key": api_key, "Content-Type": "application/json"})
        self.max_calls = max_calls
        self.calls = 0
        self.errors = 0

    def search(self, query: str, page_token: str | None = None) -> tuple[list[dict], str | None]:
        body = {"textQuery": query, "languageCode": "tr", "regionCode": "TR", "pageSize": 20}
        if page_token:
            body["pageToken"] = page_token
        for attempt in range(3):
            if self.calls >= self.max_calls:
                raise CallBudgetExceeded(f"{self.max_calls} istek sınırına ulaşıldı")
            self.calls += 1
            try:
                r = self._s.post(SEARCH_URL, json=body, headers={"X-Goog-FieldMask": SEARCH_FIELDS}, timeout=30)
            except Exception as e:  # ağ hatası
                print(f"  HATA ağ: {e}")
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 200:
                data = r.json()
                return data.get("places") or [], data.get("nextPageToken")
            if r.status_code in (429, 500, 503):
                time.sleep(3 * (attempt + 1))
                continue
            print(f"  HATA HTTP {r.status_code}: {r.text[:200]}")
            break
        self.errors += 1
        raise RuntimeError(f"Places araması başarısız: {query}")


def best_match(record: dict, places: list[dict]) -> tuple[dict | None, float]:
    best, best_score = None, 0.0
    for p in places:
        if not address_has_il(p.get("formattedAddress", ""), record.get("il", "")):
            continue
        s = similarity(record.get("isim", ""), display_name(p))
        if s > best_score:
            best, best_score = p, s
    return (best, best_score) if best_score >= MATCH_MIN else (None, best_score)


def has_open_twin(record: dict, places: list[dict], closed: dict) -> bool:
    """Aynı ilde aynı adla açık başka bir yer varsa kapanan kayıt eski bir Google girdisi olabilir."""
    for p in places:
        if p is closed or p.get("businessStatus") != "OPERATIONAL":
            continue
        if not address_has_il(p.get("formattedAddress", ""), record.get("il", "")):
            continue
        if similarity(record.get("isim", ""), display_name(p)) >= MATCH_MIN:
            return True
    return False


def is_candidate(place: dict, il: str) -> bool:
    name = display_name(place)
    if place.get("businessStatus") not in (None, "OPERATIONAL"):
        return False
    if not address_has_il(place.get("formattedAddress", ""), il):
        return False
    if _NAME_EXCLUDE.search(name) or set(place.get("types") or []) & _TYPE_EXCLUDE:
        return False
    return bool(_NAME_OK.search(name) and _NAME_SERVICE.search(name))


def is_municipal(place: dict) -> bool:
    return bool(_NAME_MUNICIPAL.search(display_name(place)))


def new_record(place: dict, il: str) -> dict:
    address = clean_address(place.get("formattedAddress", ""))
    ilce = ilce_from_address(il, address)
    yer = f"{il} / {ilce}" if ilce else il
    types = set(place.get("types") or [])
    hizmet = ""
    if types & {"restaurant", "cafe", "coffee_shop", "tea_house", "food"}:
        hizmet = " Yeme-içme hizmeti verir."
    return {
        "il": il,
        "ilce": ilce,
        "isim": display_name(place),
        "adres": address,
        "aciklama": f"{yer} konumunda sosyal tesis.{hizmet}",
    }


def plan_changes(sosyal: list[dict], state: dict, client) -> dict:
    """Mevcut kayıtları kontrol eder, yeni adayları bulur; listeyi değiştirmez."""
    place_ids: dict = state.setdefault("place_ids", {})
    misses: dict = state.setdefault("misses", {})
    remove, temp_closed, not_found, added, review = [], [], [], [], []

    for i, rec in enumerate(sosyal, 1):
        il, isim = rec.get("il", ""), rec.get("isim", "")
        if not il or not isim:
            continue
        key = record_key(il, isim)
        try:
            places, _ = client.search(f"{isim} {il}")
        except RuntimeError:
            continue
        match, score = best_match(rec, places)
        if match is None:
            misses[key] = misses.get(key, 0) + 1
            not_found.append({"il": il, "isim": isim, "ardisik": misses[key], "en_iyi_benzerlik": round(score, 2)})
            continue
        misses.pop(key, None)
        place_ids[key] = match["id"]
        status = match.get("businessStatus")
        if status == "CLOSED_PERMANENTLY" and score < REMOVE_MIN:
            temp_closed.append({"il": il, "isim": isim, "not": "kapalı görünüyor, eşleşme zayıf"})
        elif status == "CLOSED_PERMANENTLY" and has_open_twin(rec, places, match):
            temp_closed.append({"il": il, "isim": isim, "not": "kapalı girdi var ama aynı adla açık tesis de var"})
        elif status == "CLOSED_PERMANENTLY":
            remove.append({"kayit": rec, "google_ad": display_name(match), "benzerlik": round(score, 2)})
        elif status == "CLOSED_TEMPORARILY":
            temp_closed.append({"il": il, "isim": isim})
        if i % 100 == 0:
            print(f"  kontrol: {i}/{len(sosyal)}")

    known_ids = set(place_ids.values())
    by_il: dict[str, list[str]] = {}
    for rec in sosyal:
        by_il.setdefault(fold(rec.get("il", "")), []).append(rec.get("isim", ""))

    for il in IL_ILCE:
        if il == "Kıbrıs":
            continue
        for q in DISCOVERY_QUERIES:
            token = None
            for _ in range(DISCOVERY_PAGES):
                try:
                    places, token = client.search(q.format(il=il), token)
                except RuntimeError:
                    break
                for p in places:
                    if p.get("id") in known_ids or not is_candidate(p, il):
                        continue
                    name = display_name(p)
                    existing = by_il.setdefault(fold(il), [])
                    if any(similarity(name, e) >= DUP_MIN for e in existing):
                        continue
                    rec = new_record(p, il)
                    (added if is_municipal(p) else review).append(rec)
                    existing.append(name)
                    known_ids.add(p["id"])
                    place_ids[record_key(il, name)] = p["id"]
                if not token:
                    break

    return {
        "remove": remove,
        "temp_closed": temp_closed,
        "not_found": not_found,
        "added": added,
        "review": review,
    }


def safety_check(plan: dict, total: int, client, first_run: bool = False) -> str | None:
    if client.calls and client.errors / client.calls > MAX_ERROR_RATIO:
        return f"API hata oranı yüksek ({client.errors}/{client.calls})"
    cap = max(MIN_REMOVE_CAP, int(total * MAX_REMOVE_RATIO))
    if len(plan["remove"]) > cap:
        return f"Çıkarılacak tesis sayısı güvenlik eşiğini aşıyor ({len(plan['remove'])} > {cap})"
    max_add = MAX_ADD_FIRST if first_run else MAX_ADD
    if len(plan["added"]) > max_add:
        return f"Eklenecek tesis sayısı güvenlik eşiğini aşıyor ({len(plan['added'])} > {max_add})"
    return None


def apply_plan(data: dict, plan: dict) -> list[dict]:
    remove_keys = {record_key(r["kayit"]["il"], r["kayit"]["isim"]) for r in plan["remove"]}
    kept, removed = [], []
    for rec in data["sosyal"]:
        (removed if record_key(rec.get("il", ""), rec.get("isim", "")) in remove_keys else kept).append(rec)
    data["sosyal"] = kept + plan["added"]
    return removed


def write_json(path: Path, obj, indent: int = 2) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_report(today: str, plan: dict | None, applied: bool, note: str, calls: int) -> None:
    REPORTS.mkdir(exist_ok=True)
    report = {
        "tarih": today,
        "uygulandi": applied,
        "not": note,
        "api_cagrisi": calls,
        **({k: plan.get(k, []) for k in ("remove", "added", "review", "temp_closed", "not_found")} if plan else {}),
    }
    write_json(REPORTS / f"{today}.json", report, indent=1)
    lines = [f"# Sosyal tesis taraması — {today}", "", f"- Uygulandı: {'evet' if applied else 'hayır'}", f"- Not: {note}"]
    if plan:
        lines += [
            f"- Kalıcı kapandığı için çıkarılan: {len(plan['remove'])}",
            f"- Yeni eklenen: {len(plan['added'])}",
            f"- Adında belediye geçmediği için eklenmeyen (incelenecek): {len(plan.get('review', []))}",
            f"- Geçici kapalı (dokunulmadı): {len(plan['temp_closed'])}",
            f"- Google'da bulunamayan (dokunulmadı): {len(plan['not_found'])}",
            "",
        ]
        if plan["remove"]:
            lines += ["## Çıkarılanlar", *[f"- {r['kayit']['il']} — {r['kayit']['isim']}" for r in plan["remove"]], ""]
        if plan["added"]:
            lines += ["## Eklenenler", *[f"- {r['il']} — {r['isim']} ({r['adres']})" for r in plan["added"]], ""]
        if plan.get("review"):
            lines += ["## İncelenecek (eklenmedi)", *[f"- {r['il']} — {r['isim']} ({r['adres']})" for r in plan["review"]], ""]
    (REPORTS / f"{today}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def estimated_calls(record_count: int) -> int:
    """Bir taramanın en fazla atacağı istek (yeniden denemeler hariç)."""
    iller = sum(1 for il in IL_ILCE if il != "Kıbrıs")
    return record_count + iller * len(DISCOVERY_QUERIES) * DISCOVERY_PAGES


def call_budget(state: dict, month: str) -> tuple[int, int]:
    """(bu çalıştırmanın kullanabileceği istek, bu ay önceden kullanılan)."""
    used = int((state.get("aylik_cagri") or {}).get(month, 0))
    return max(0, min(MAX_CALLS_PER_RUN, MONTHLY_CALL_CAP - used)), used


def add_usage(state: dict, month: str, calls: int) -> None:
    usage = state.setdefault("aylik_cagri", {})
    usage[month] = int(usage.get(month, 0)) + calls
    for old in sorted(usage)[:-12]:
        del usage[old]


def record_usage_only(month: str, calls: int) -> None:
    """Değişiklik uygulanmayan çalıştırmada yalnız aylık sayacı günceller."""
    if not calls:
        return
    state = load_state()
    add_usage(state, month, calls)
    write_json(STATE, state, indent=1)


def main() -> int:
    today = date.today().isoformat()
    month = today[:7]
    key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    if not key:
        write_report(today, None, False, "GOOGLE_PLACES_API_KEY tanımlı değil; tarama yapılmadı.", 0)
        return 0

    data = json.loads(MASTER.read_text(encoding="utf-8"))
    sosyal = data.get("sosyal") or []
    state = load_state()
    budget, used = call_budget(state, month)
    need = estimated_calls(len(sosyal))
    if need > budget:
        write_report(
            today, None, False,
            f"İstek sınırı: tarama en fazla {need} istek gerektiriyor, kullanılabilir {budget} "
            f"(bu ay kullanılan {used}/{MONTHLY_CALL_CAP}, çalıştırma başına en fazla {MAX_CALLS_PER_RUN}). "
            "Tarama yapılmadı.",
            0,
        )
        return 0

    client = PlacesClient(key, budget)
    try:
        plan = plan_changes(sosyal, state, client)
    except CallBudgetExceeded as e:
        record_usage_only(month, client.calls)
        write_report(today, None, False, f"{e}; hiçbir değişiklik uygulanmadı.", client.calls)
        return 0
    except BaseException:
        record_usage_only(month, client.calls)
        raise

    problem = safety_check(plan, len(sosyal), client, first_run="son_tarama" not in state)
    if problem or DRY_RUN:
        record_usage_only(month, client.calls)
        write_report(today, plan, False, problem or "DRY RUN", client.calls)
        return 0

    removed = apply_plan(data, plan)
    if removed or plan["added"]:
        write_json(MASTER, data)
        archive = json.loads(ARCHIVE.read_text(encoding="utf-8")) if ARCHIVE.exists() else []
        archive += [{**r, "kaldirilma_tarihi": today, "neden": "Google: kalıcı olarak kapandı"} for r in removed]
        write_json(ARCHIVE, archive, indent=1)
    state["son_tarama"] = today
    add_usage(state, month, client.calls)
    write_json(STATE, state, indent=1)
    write_report(today, plan, True, "Tamamlandı", client.calls)
    return 0


if __name__ == "__main__":
    sys.exit(main())
