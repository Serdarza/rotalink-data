"""Belediye sosyal tesisleri — aylık resmî menü / fiyat taraması.

master_database_updated.json içindeki `sosyal` tesisleri için yalnız belediyelerin
kendi sitelerinde (.bel.tr, .gov.tr ve config.json'daki onaylı alan adları)
yayımlanan yeme-içme fiyatlarını bulur ve sosyal_menuler.json'a yazar.

Kurallar:
  * Fiyat uydurulmaz, tahmin edilmez; her ürün kaynak belgede birebir yazandır.
  * Belgede tesisin kendi adı geçiyorsa kapsam "tesis"; belediyenin genel sosyal tesis
    tarifesiyse ve tesis adında o belediye açıkça yazıyorsa kapsam "belediye".
  * En yeni yılın belgesi seçilir; içinde bulunulan yıldan bir önceki yıldan eski
    belgeler kullanılmaz.
  * robots.txt'ye uyulur; erişim engellenen siteler zorlanmaz, rapora yazılır.
  * Siteye ulaşılamadığında önceki veri en fazla KEEP_DAYS_ON_ERROR gün korunur;
    site açıkken menü kalkmışsa tesisin menüsü kaldırılır.
  * Çok sayıda site hata verirse (ör. yurt dışı erişim engeli) hiçbir menü silinmez.
  * Veri değişmediyse sosyal_menuler.json yeniden yazılmaz (gereksiz commit olmaz).
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib import robotparser
from urllib.parse import urldefrag, urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "price_research"))
import common  # noqa: E402  (price_research/common.py: nazik HTTP + PDF/Excel okuma)
import prices  # noqa: E402

MASTER = ROOT / "master_database_updated.json"
OUT = ROOT / "sosyal_menuler.json"
STATE = HERE / "state.json"
SOURCES = HERE / "kaynaklar.json"
HISTORY = HERE / "fiyat_gecmisi.json"
CHANGES = HERE / "degisiklikler.json"
REVIEW = HERE / "inceleme.json"
APPROVALS = HERE / "onaylar.json"
REPORTS = HERE / "reports"
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
IL_ILCE: dict[str, list[str]] = json.loads((ROOT / "sosyal_monitor" / "il_ilce.json").read_text(encoding="utf-8"))

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
UA = "RotaLinkMenuBot/1.0 (+https://github.com/Serdarza/rotalink-data; belediye sosyal tesisi resmi menu kontrolu)"
ROBOTS_AGENT = "RotaLinkMenuBot"

OFFICIAL_SUFFIXES = (".bel.tr", ".gov.tr", ".gov.ct.tr")
MAX_PAGES_PER_SITE = 45
MAX_DEPTH = 3
MAX_OCR_PER_SITE = 3
MIN_ITEMS = 8
MAX_ITEMS = 400
MIN_PRICE, MAX_PRICE = 5.0, 5000.0
KEEP_DAYS_ON_ERROR = 100
MAX_SITE_ERROR_RATIO = 0.5
WORKERS = 12
SITE_TIME_BUDGET_SEC = 480
PROBE_TIMEOUT, PROBE_RETRIES = 10.0, 1
NO_DOMAIN_RETRY_DAYS = 90
MODE = os.environ.get("MENU_MODE", "full")  # full = aylık tam tarama, known = haftalık bilinen kaynaklar
# GitHub Actions iş süresi sınırı 6 saat; bu süreden sonra yeni siteye başlanmaz.
TIME_BUDGET_SEC = int(os.environ.get("MENU_TIME_BUDGET_MIN", "270")) * 60
_DEADLINE = time.monotonic() + TIME_BUDGET_SEC

try:
    import pymupdf

    pymupdf.TOOLS.mupdf_display_errors(False)
except Exception:  # noqa: BLE001
    pass

_FOLD = str.maketrans("çÇğĞıIİöÖşŞüÜâÂîÎûÛ", "ccggiiioossuuaaiiuu")


def fold(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").translate(_FOLD).lower())).strip()


def slug(s: str) -> str:
    return fold(s).replace(" ", "")


def tr_lower(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


def tr_upper_first(s: str) -> str:
    if not s:
        return s
    c = s[0]
    c = "İ" if c == "i" else ("I" if c == "ı" else c.upper())
    return c + s[1:]


def nice_name(raw: str) -> str:
    """'BARDAK ÇAY' → 'Bardak çay'; karışık yazım olduğu gibi kalır."""
    s = re.sub(r"\s+", " ", raw).strip(" .:-–…|")
    letters = [ch for ch in s if ch.isalpha()]
    if letters and sum(ch.isupper() for ch in letters) / len(letters) > 0.8:
        s = tr_upper_first(tr_lower(s))
    return s


# --------------------------------------------------------------------------- URL güvenliği

def official_url(url: str) -> bool:
    """Yalnız http(s), varsayılan port, alan adı resmî uzantılı ya da onaylı listede."""
    try:
        p = urlparse(url)
    except ValueError:
        return False
    if p.scheme not in ("http", "https") or p.username or p.password:
        return False
    try:
        port = p.port
    except ValueError:
        return False
    if port not in (None, 80, 443):
        return False
    host = (p.hostname or "").lower().rstrip(".")
    if not host or re.fullmatch(r"[\d.]+", host) or ":" in host:
        return False
    if host.endswith(OFFICIAL_SUFFIXES):
        return True
    return any(host == h or host.endswith("." + h) for h in EXTRA_OFFICIAL)


# Belediye iştirakleri: resmî ilişkisi elle doğrulanıp config.json'a yazılan alan adları.
ISTIRAK: dict[str, list[str]] = CONFIG.get("istirak", {})
EXTRA_OFFICIAL = set(CONFIG.get("ek_resmi_alanlar", [])) | {d for ds in ISTIRAK.values() for d in ds}


def site_root(host: str) -> str:
    host = host.lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def same_site(url: str, root: str) -> bool:
    host = site_root(urlparse(url).hostname or "")
    return host == root or host.endswith("." + root)


# --------------------------------------------------------------------------- belediye eşleme

@dataclass(frozen=True)
class Municipality:
    il: str
    ilce: str  # "" → büyükşehir / il belediyesi

    @property
    def key(self) -> str:
        return f"{self.il}|{self.ilce}"

    @property
    def name(self) -> str:
        return f"{self.ilce} Belediyesi" if self.ilce else f"{self.il} Belediyesi"


_BEL_RE = re.compile(
    r"((?:[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+){0,2}[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)\s+(Büyükşehir\s+)?Belediye(?:si|leri)?\b"
)


def _match_il(word: str) -> str | None:
    w = slug(word)
    return next((il for il in IL_ILCE if slug(il) == w), None)


def _match_ilce(il: str, word: str) -> str | None:
    w = slug(word)
    return next((d for d in IL_ILCE.get(il, []) if slug(d) == w and d != "Merkez"), None)


def municipality_of(rec: dict) -> Municipality | None:
    """Tesis adında açıkça geçen belediye ('Fatsa Belediyesi', 'Adana Büyükşehir Belediyesi', 'İBB')."""
    il, isim = rec.get("il", ""), rec.get("isim", "")
    for m in _BEL_RE.finditer(isim):
        words = m.group(1).split()
        metro = bool(m.group(2))
        if words and slug(words[-1]) == "buyuksehir":
            words, metro = words[:-1], True
        for k in range(len(words)):
            cand = " ".join(words[k:])
            if metro:
                hit = _match_il(cand)
                if hit:
                    return Municipality(hit, "")
                continue
            hit = _match_ilce(il, cand)
            if hit:
                return Municipality(il, hit)
            if _match_il(cand) == il:
                return Municipality(il, "")
    for alias, alias_il in CONFIG.get("takma_adlar", {}).items():
        if re.search(rf"\b{re.escape(alias)}\b", fold(isim)) and alias_il == il:
            return Municipality(il, "")
    # "Avcılar Sosyal Tesisleri": adında yer adı + genel kelimelerden başka bir şey yoksa o belediyenindir.
    f = fold(isim)
    if "sosyal tesis" in f:
        words = [w for w in f.split() if w not in _GENERIC]
        ilce = rec.get("ilce", "")
        if words and all(w == slug(ilce) for w in words) and _match_ilce(il, ilce):
            return Municipality(il, _match_ilce(il, ilce))
        if words and all(w == slug(il) for w in words):
            return Municipality(il, "")
    return None


def candidate_domains(m: Municipality) -> list[str]:
    override = CONFIG.get("alan_adi", {}).get(m.key)
    if override:
        return list(override)
    base = slug(m.ilce or m.il)
    out = [f"{base}.bel.tr"]
    if m.ilce:
        out.append(f"{base}{slug(m.il)}.bel.tr")
    return out


_GENERIC = {
    "belediye", "belediyesi", "buyuksehir", "sosyal", "tesis", "tesisi", "tesisleri", "tesisler",
    "ve", "kafe", "cafe", "kafeterya", "restoran", "restaurant", "lokanta", "lokantasi", "kir",
    "kahvesi", "cay", "bahcesi", "mesire", "alani", "kompleksi", "merkezi", "isletmesi", "iktisadi",
    "isletme", "mudurlugu", "ibb", "abb", "the", "ve",
}


def distinctive_tokens(rec: dict, muni: Municipality | None) -> list[str]:
    """Tesis adından belediye adı ve genel kelimeler atılmış ayırt edici kelimeler."""
    skip = set(_GENERIC) | {slug(rec.get("il", "")), slug(rec.get("ilce", ""))}
    if muni:
        skip |= {slug(w) for w in (muni.ilce or muni.il).split()}
    toks = [t for t in fold(rec.get("isim", "")).split() if t not in skip and len(t) >= 3]
    return toks


def mentions_facility(text: str, tokens: list[str]) -> bool:
    if not tokens or sum(len(t) for t in tokens) < 5:
        return False
    hay = f" {fold(text)} "
    return all(f" {t} " in hay for t in tokens)


def match_ratio(text: str, tokens: list[str]) -> float:
    """Ayırt edici kelimelerin metinde (yazım farkına toleranslı) geçme oranı."""
    if not tokens:
        return 0.0
    words = set(fold(text).split())
    hit = 0
    for t in tokens:
        if t in words or any(len(w) >= 4 and SequenceMatcher(None, t, w).ratio() >= 0.85 for w in words):
            hit += 1
    return hit / len(tokens)


# --------------------------------------------------------------------------- menü ayrıştırma

CATEGORIES: list[tuple[str, re.Pattern]] = [
    ("Salatalar", re.compile(r"\bsalata|\bsogus")),
    ("Çorbalar", re.compile(r"\bcorba")),
    ("Tatlılar", re.compile(
        r"\btatli|baklava|kunefe|sutlac|kazandibi|trilece|dondurma|\bpasta\b|\bkek\b|sufle|puding|helva|kadayif|"
        r"magnolia|cheesecake|waffle|lokma|revani|tiramisu|profiterol|keskul|irmik|asure|brownie|meyve tabag")),
    ("Soğuk içecekler", re.compile(
        r"soguk cay|ice ?tea|meyve suyu|portakal suyu|sikma|limonata|\bayran|\bkola\b|\bcola\b|gazoz|\bsoda\b|"
        r"\bsu\b(?! bore)|maden suyu|churchill|frappe|milkshake|smoothie|salgam|serbet|fanta|sprite|enerji icecegi|"
        r"kokteyl|\bboza\b|limonlu soda|icecek kutu|kutu icecek|soguk kahve|ice latte|\btang\b")),
    ("Sıcak içecekler", re.compile(
        r"\bcay\b|\bcayi\b|kahve|nescafe|espresso|latte|cappuccino|cappicino|kapucino|mocha|americano|filtre|"
        r"salep|sahlep|ihlamur|sicak cikolata|bitki|papatya|adacayi|kis cayi|nane limon|\bsut\b|sicak su|"
        r"macchiato|cortado|dibek|menengic")),
    ("Kahvaltı", re.compile(
        r"kahvalti|menemen|omlet|yumurta|mihlama|kuymak|\bbal\b|kaymak|peynir tabag|zeytin tabag|gozleme|"
        r"\bpisi|\bsimit|pogaca|\bacma\b|serpme|sucuk tava|sahanda|tereyag|recel|katmer|bazlama")),
    ("Atıştırmalıklar", re.compile(
        r"\btost|sandvic|sandvic|borek|patates|cips|nugget|sosis|kumpir|citir|corek|milfoy|kizartma|"
        r"cig kofte|midye|misir|cerez|kuruyemis|incir|kayisi|findik|fistik|leblebi|badem|bagdem|kaju|uzum")),
    ("Menüler", re.compile(r"\bmenu|cocuk menu|aile menu|fiks menu|set menu|tabldot")),
    ("Ana yemekler", re.compile(
        r"kebap|kebab|izgara|kofte|\bsis\b|beyti|iskender|doner|tavuk|\bet\b|bonfile|antrikot|pirzola|kanat|"
        r"balik|levrek|cipura|hamsi|alabalik|somon|manti|pilav|makarna|\bpide|lahmacun|pizza|hamburger|burger|"
        r"durum|tantuni|guvec|sac tava|sote|fasulye|fajita|wrap|yemek|kavurma|biftek|steak|schnitzel|"
        r"sinitzel|kuzu|ciger|kokorec|nohut|kuru fasulye|dolma|sarma|musakka|karniyarik|hunkar|ali nazik|lazanya|"
        r"spagetti|noodle|tantuni|etli|kiymali|kusbasi|kasarli pide")),
]

# Yeme-içme olmayan ücret kalemleri (salon kirası, otopark, organizasyon menüsü...).
EXCLUDE = re.compile(
    r"salon|dugun|nikah|nisan|\bkina\b|organizasyon|davet|otopark|\bpark ucret|\boda\b|konaklama|havuz|"
    r"\bgiris\b|kiralama|\bkira\b|\bm2\b|metrekare|abonman|uyelik|ruhsat|\bharc|zabita|imar|mezar|cenaze|"
    r"nakliye|vinc|reklam|\bilan\b|stant|tente|cadir|masa ucret|kuver|\bservis\b|depozito|ceza|kdv|toplam|"
    r"\bsaat\b|\bgun\b|\bay\b|aylik|yillik|sezon|bilet|seans|kisi basi organizasyon|hali saha|sauna|hamam|"
    r"fotograf|cekim|kamera|elektrik|\bsu bedeli|dogalgaz|abone|asansor|imalat|\bbeher\b|uretim|isyeri|"
    r"^[a-zçgıosu]\)")

HEADER_IGNORE = re.compile(r"^(urun|urun adi|fiyat|fiyati|aciklama|birim|sira|no|kdv dahil)(\s|$)")
# Yalnız başlık sayesinde kategori alacak kalemlerde adres / sayfa satırlarını eler.
NONFOOD_HINT = re.compile(r"\b(mah|mahalle|cad|cadde|sok|sokak|no|tel|telefon|faks|fax|adres|posta|sayfa|madde|"
                          r"karar|sayi|tarih|yil|yili)\b")

_PRICE_NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?"
_LINE_RE = re.compile(
    rf"^(?P<name>.*?[A-Za-zÇĞİÖŞÜçğıöşüâîû].*?)[\s:.\-–…]*"
    rf"(?P<prices>(?:\s*(?:₺\s*)?(?:{_PRICE_NUM})\s*(?:₺|TL\.?|tl\.?|Tl\.?)?)+)\s*$"
)
_ONLY_PRICE_RE = re.compile(rf"^(?:₺\s*)?(?:{_PRICE_NUM})\s*(?:₺|TL\.?|tl\.?)?$")
_NUM_RE = re.compile(_PRICE_NUM)
_LAW_RE = re.compile(r"\b\d{3,4}\s*S\.?\s*K\.?\s*\d+\.?\s*(?:md|mad)\.?", re.I)
_PCT_RE = re.compile(r"%\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*%")
_DATE_RE = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")
_UNIT_RE = re.compile(r"\b(?:adet|porsiyon|kişi başı|kisi basi|kişi|bardak|fincan|tabak|duble)\s*(?=₺|\d)", re.I)
_INDEX_RE = re.compile(r"^\s*\d{1,3}(?:\.\d{1,3})*[.)\-]?\s+(?!(?:TL|tl|Tl)\b)(?=[A-Za-zÇĞİÖŞÜçğıöşü])")


def parse_price(tok: str) -> float | None:
    t = tok.strip().replace(" ", "")
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?", t):
        return float(t.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d+,\d{1,2}", t):
        return float(t.replace(",", "."))
    if re.fullmatch(r"\d+\.\d{1,2}", t):
        return float(t)
    if re.fullmatch(r"\d+", t):
        return float(t)
    return None


def categorize(name: str) -> str | None:
    f = fold(name)
    for cat, rx in CATEGORIES:
        if rx.search(f):
            return cat
    return None


def clean_line(line: str) -> str:
    s = line.replace("|", " ").replace("\u00a0", " ")
    s = _LAW_RE.sub(" ", s)
    s = _DATE_RE.sub(" ", s)
    s = _PCT_RE.sub(" ", s)
    s = _UNIT_RE.sub(" ", s)
    s = _INDEX_RE.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def split_item(line: str) -> tuple[str, float] | None:
    """'BARDAK ÇAY 15,00' → ('BARDAK ÇAY', 15.0); 'KIYMALI PİDE 1,5 240,00 TL' → ('KIYMALI PİDE 1,5', 240.0).

    Satırda birden çok fiyat varsa (eski yıl / yeni yıl sütunu) sondaki alınır; küçük porsiyon
    sayıları (1, 1,5) ada eklenir. Üçten fazla fiyatlı satırlar (organizasyon tabloları) atlanır.
    """
    m = _LINE_RE.match(line)
    if not m or m.group("name").rstrip().endswith("/"):
        return None
    nums = _NUM_RE.findall(m.group("prices"))
    if not nums or len(nums) > 4:
        return None
    price = parse_price(nums[-1])
    if price is None or not (MIN_PRICE <= price <= MAX_PRICE):
        return None
    extra = []
    for n in nums[:-1]:
        v = parse_price(n)
        if v is not None and v < 10:
            extra.append(n)
        elif v is not None and len(nums) - 1 > 2:
            return None
    name = (m.group("name") + " " + " ".join(extra)).strip()
    return name, price


def valid_name(name: str) -> bool:
    f = fold(name)
    letters = sum(ch.isalpha() for ch in name)
    if letters < 3 or len(name) > 70 or "http" in f or "www" in f:
        return False
    if HEADER_IGNORE.match(f) or EXCLUDE.search(f):
        return False
    return True


@dataclass
class MenuItem:
    name: str
    price: float
    category: str
    unit: str = ""


_UNITS = [
    (re.compile(r"\b\d*[.,]?\d*\s*(kg|kilo|kilogram)\b"), "kg"),
    (re.compile(r"\b\d+\s*(gr|g|gram)\b"), "gram"),
    (re.compile(r"\b\d*[.,]?\d*\s*(lt|litre|cl|ml)\b"), "şişe/litre"),
    (re.compile(r"\bporsiyon\b"), "porsiyon"),
    (re.compile(r"\bbardak\b"), "bardak"),
    (re.compile(r"\bfincan\b"), "fincan"),
    (re.compile(r"\bduble\b"), "duble"),
    (re.compile(r"\b(\d+|tek|iki|cift)\s*kisilik\b"), "kişilik"),
    (re.compile(r"\badet\b"), "adet"),
]


def detect_unit(raw: str) -> str:
    f = fold(raw)
    for rx, unit in _UNITS:
        if rx.search(f):
            return unit
    return ""


def parse_menu(lines: list[str]) -> list[MenuItem]:
    """Satır listesinden yeme-içme kalemlerini çıkarır. Başlık satırları kategori ipucu olur;
    ücret başlıkları (salon, organizasyon...) altındaki kalemler atlanır."""
    items: list[MenuItem] = []
    seen: set[tuple[str, float]] = set()
    header_cat: str | None = None
    header_excluded = False
    pending_name: str | None = None
    for raw in lines:
        line = clean_line(raw)
        if not line:
            continue
        if _ONLY_PRICE_RE.match(line):
            if pending_name:
                nums = _NUM_RE.findall(line)
                price = parse_price(nums[-1]) if nums else None
                if price is not None and MIN_PRICE <= price <= MAX_PRICE:
                    _add(items, seen, pending_name, price, header_cat, header_excluded, detect_unit(pending_name))
            pending_name = None
            continue
        hit = split_item(line)
        if hit:
            _add(items, seen, hit[0], hit[1], header_cat, header_excluded, detect_unit(raw))
            pending_name = None
            continue
        pending_name = None
        if len(line) > 45 or re.search(r"\d{3,}", line):
            continue
        cat = header_category(line)
        words = len(line.split())
        if cat is None and EXCLUDE.search(fold(line)):
            header_cat, header_excluded = None, True
        elif cat and words <= 4 and line.upper() == line:
            header_cat, header_excluded = cat, False
        elif cat is None and line.isupper() and words <= 4:
            header_cat, header_excluded = None, False
        if valid_name(line) and categorize(line):
            pending_name = line
        if len(items) >= MAX_ITEMS:
            break
    return items


def header_category(line: str) -> str | None:
    f = fold(line)
    if re.search(r"\bicecek", f):
        return "Sıcak içecekler" if "sicak" in f else "Soğuk içecekler"
    return categorize(line)


_COLUMN_GLUE = re.compile(r"\s\d{1,3}\s+[A-ZÇĞİÖŞÜ]")


def _add(items, seen, raw_name, price, header_cat, header_excluded, unit="") -> None:
    # İki dilli menüler ("Peynirli Tost / Cheese Toast") yalnız Türkçe adıyla tutulur.
    name = nice_name(raw_name.split(" / ")[0].strip())
    if header_excluded or not valid_name(name) or _COLUMN_GLUE.search(name):
        return
    cat = categorize(name)
    if cat is None:
        if header_cat is None or len(name) > 40 or ":" in name or NONFOOD_HINT.search(fold(name)):
            return
        cat = header_cat
    key = (fold(name), price)
    if key in seen:
        return
    seen.add(key)
    items.append(MenuItem(name, price, cat, unit))


CATEGORY_ORDER = [c for c, _ in CATEGORIES]
DISPLAY_ORDER = ["Kahvaltı", "Çorbalar", "Ana yemekler", "Menüler", "Salatalar", "Atıştırmalıklar", "Tatlılar",
                 "Sıcak içecekler", "Soğuk içecekler"]


def group_items(items: list[MenuItem]) -> list[dict]:
    by: dict[str, list[dict]] = {}
    for it in items:
        p = {"ad": it.name, "fiyat": it.price}
        if it.unit:
            p["birim"] = it.unit
        by.setdefault(it.category, []).append(p)
    return [{"ad": c, "urunler": by[c]} for c in DISPLAY_ORDER if c in by]


# --------------------------------------------------------------------------- belge

FOOD_CONTEXT = re.compile(r"sosyal tesis|kafe|cafe|kafeterya|restoran|lokanta|cay bahcesi|menu|isletme|yeme icme|"
                          r"icecek|kahvalti|tesislerimiz")
LINK_STRONG = re.compile(r"men[uü]|fiyat|tarife|[uü]cret|price")
LINK_CONTEXT = re.compile(r"sosyal tesis|tesislerimiz|tesisler|kafe|cafe|restoran|lokanta|kafeterya|cay bahcesi|"
                          r"isletme|istirak|iktisadi|yeme icme")
# Tarifeler çoğu zaman meclis kararı / komisyon raporu eki olarak yayımlanır.
LINK_WEAK = re.compile(r"meclis|komisyon|karar|belge|dokuman|yayin|mudurluk|birim")
LINK_SKIP = re.compile(r"ihale|haber|duyuru arsiv|galeri|video|foto|imar plan|vefat|cenaze|nobetci|insan kaynak|"
                       r"facebook|twitter|instagram|youtube|whatsapp|mailto|tel:|javascript")


@dataclass
class Doc:
    url: str
    kind: str
    title: str
    link_text: str
    year: int | None
    items: list[MenuItem]
    text_head: str
    last_modified: str | None = None
    parent_title: str = ""
    mentions_sosyal: bool = False
    phones: frozenset = frozenset()
    sha256: str = ""

    def to_cache(self) -> dict:
        return {
            "sha256": self.sha256, "kind": self.kind, "title": self.title, "link_text": self.link_text,
            "year": self.year, "last_modified": self.last_modified, "parent_title": self.parent_title,
            "mentions_sosyal": self.mentions_sosyal, "phones": sorted(self.phones), "text_head": self.text_head[:1500],
            "items": [[i.name, i.price, i.category, i.unit] for i in self.items],
        }

    @staticmethod
    def from_cache(url: str, c: dict) -> "Doc":
        return Doc(url, c["kind"], c["title"], c["link_text"], c["year"],
                   [MenuItem(*i) for i in c["items"]], c["text_head"], c.get("last_modified"),
                   c.get("parent_title", ""), c.get("mentions_sosyal", False), frozenset(c.get("phones", [])),
                   c["sha256"])


_PHONE_RE = re.compile(r"(?:\+?90|0)?\s*\(?([2-5]\d{2})\)?[\s.-]*(\d{3})[\s.-]*(\d{2})[\s.-]*(\d{2})")


def phones_in(text: str) -> frozenset:
    return frozenset("".join(m.groups()) for m in _PHONE_RE.finditer(text or ""))


def source_date(doc: Doc) -> str | None:
    """Kaynağın kendi güncelleme tarihi (HTTP Last-Modified); bilinmiyorsa None."""
    if not doc.last_modified:
        return None
    try:
        return parsedate_to_datetime(doc.last_modified).date().isoformat()
    except (TypeError, ValueError):
        return None


def years_in(s: str, today: date) -> list[int]:
    return [int(y) for y in re.findall(r"(?<!\d)(20[1-3]\d)(?!\d)", s or "") if 2015 <= int(y) <= today.year + 1]


def doc_year(text_head: str, url: str, link_text: str, today: date) -> int | None:
    ys = years_in(f"{link_text} {url} {text_head}", today)
    return max(ys) if ys else None


def recent_enough(doc: Doc, today: date) -> bool:
    if doc.year is not None:
        return doc.year >= today.year - 1
    if doc.last_modified:
        try:
            lm = parsedate_to_datetime(doc.last_modified).date()
            return (today - lm).days <= 365
        except (TypeError, ValueError):
            return doc.kind == "html"
    return doc.kind == "html"


def html_lines(content: bytes, base_url: str) -> tuple[list[str], list[tuple[str, str]], str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(content, "lxml")
    links = [(urljoin(base_url, a["href"].strip()), a.get_text(" ", strip=True)[:150])
             for a in soup.find_all("a", href=True)]
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for el in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        el.decompose()
    for tag in ("tr", "li", "dt", "dd", "p", "h1", "h2", "h3", "h4", "h5", "h6"):
        for el in soup.find_all(tag):
            if el.parent is None:
                continue
            cells = el.find_all(["td", "th"]) if tag == "tr" else None
            txt = " ".join(c.get_text(" ", strip=True) for c in cells) if cells else el.get_text(" ", strip=True)
            el.replace_with(soup.new_string(f"\n{txt}\n"))
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in soup.get_text("\n").splitlines()]
    return [ln for ln in lines if ln], links, title


def link_score(url: str, text: str) -> int:
    f = fold(f"{text} {urlparse(url).path}")
    if LINK_SKIP.search(f) or LINK_SKIP.search(url.lower()):
        return 0
    s = 0
    if LINK_STRONG.search(f):
        s += 5
    if LINK_CONTEXT.search(f):
        s += 4
    if s == 0 and LINK_WEAK.search(f):
        s = 1
    return s


class Robots:
    def __init__(self, fetcher: common.Fetcher):
        self.fetcher = fetcher
        self._cache: dict[str, robotparser.RobotFileParser | None] = {}
        self._lock = threading.Lock()

    def allowed(self, url: str) -> bool:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        with self._lock:
            known = base in self._cache
            rp = self._cache.get(base)
        if not known:
            r = self.fetcher.get(base + "/robots.txt")
            rp = robotparser.RobotFileParser()
            if r.ok and r.status == 200 and r.content and "html" not in r.ctype:
                rp.parse(r.content.decode("utf-8", "ignore").splitlines())
            else:
                rp.parse([])
            with self._lock:
                self._cache[base] = rp
        return rp.can_fetch(ROBOTS_AGENT, url)


@dataclass
class SiteResult:
    domain: str
    ok: bool
    docs: list[Doc] = field(default_factory=list)
    error: str | None = None
    blocked: bool = False
    pages: int = 0
    reparsed: int = 0
    unchanged: int = 0
    istirak_adaylari: set = field(default_factory=set)


def homepage(domain: str, fetcher: common.Fetcher, robots: Robots, il: str) -> tuple[str | None, str | None]:
    """Alan adının açılan ve ilgili ile ait belediye sitesi olduğunu doğrular."""
    last_err = None
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}/"
        if not official_url(url):
            return None, "resmî alan adı değil"
        if not robots.allowed(url):
            return None, "robots.txt izin vermiyor"
        r = fetcher.get(url)
        final = r.final_url or url
        if not r.ok:
            last_err = r.error or f"HTTP {r.status}"
            continue
        if not official_url(final):
            return None, f"resmî olmayan adrese yönlendirdi: {urlparse(final).hostname}"
        text = fold(r.content[:400_000].decode("utf-8", "ignore"))
        if "belediye" not in text and not any(h in domain for h in EXTRA_OFFICIAL):
            return None, "belediye sitesi değil"
        if il and f" {fold(il)} " not in f" {text} ":
            return None, f"sayfada {il} geçmiyor"
        return final, None
    return None, last_err


_DOC_EXT = re.compile(r"\.(pdf|docx?|xlsx?|jpe?g|png|webp)$", re.I)
ISTIRAK_HINT = re.compile(r"\ba\.? ?s\.?\b|anonim|sirket|istirak|isletme|sosyal tesis|tesislerimiz|kafe|restoran")


def build_doc(final: str, kind: str, lines: list[str], title: str, ltext: str, parent: str,
              last_modified: str | None, sha: str, today: date) -> Doc | None:
    items = parse_menu(lines)
    head = "\n".join(lines[:80])
    if len(items) < MIN_ITEMS or not FOOD_CONTEXT.search(fold(f"{title} {ltext} {head} {final}")):
        return None
    full = "\n".join(lines)
    return Doc(final, kind, title, ltext, doc_year(head, final, ltext, today), items, head, last_modified,
               parent, "sosyal tesis" in fold(full), phones_in(full), sha)


def crawl_site(domain: str, il: str, fetcher: common.Fetcher, robots: Robots, today: date,
               cache: dict | None = None, probe: common.Fetcher | None = None) -> SiteResult:
    """Önceliklendirilmiş gezinme. cache: url → Doc.to_cache(); içerik özeti (SHA256) aynı olan
    PDF / Excel / görsel yeniden ayrıştırılmaz."""
    cache = cache if cache is not None else {}
    if time.monotonic() > _DEADLINE:
        return SiteResult(domain, False, error="zaman sınırı: bu ay taranamadı")
    site_deadline = min(_DEADLINE, time.monotonic() + SITE_TIME_BUDGET_SEC)
    start, err = homepage(domain, probe or fetcher, robots, il)
    if not start:
        return SiteResult(domain, False, error=err, blocked=bool(err and "robots" in err))
    root = site_root(urlparse(start).hostname or domain)
    queue: list[tuple[int, int, str, str, str]] = [(100, 0, start, "", "")]
    seen = {urldefrag(start)[0]}
    res = SiteResult(domain, True)
    ocr_left = MAX_OCR_PER_SITE
    while queue and res.pages < MAX_PAGES_PER_SITE and time.monotonic() < site_deadline:
        queue.sort(key=lambda t: (-t[0], t[1]))
        _score, depth, url, ltext, parent = queue.pop(0)
        url_years = years_in(f"{url} {ltext}", today)
        if url_years and max(url_years) < today.year - 1:
            continue
        if not robots.allowed(url):
            continue
        r = fetcher.get(url)
        res.pages += 1
        final = r.final_url or url
        if not r.ok or not official_url(final):
            continue
        kind = common.detect_kind(final, r.ctype)
        sha = r.sha256 or ""
        links: list[tuple[str, str]] = []
        doc = None
        if kind == "html":
            lines, links, title = html_lines(r.content, final)
            doc = build_doc(final, kind, lines, title, ltext, parent, r.last_modified, sha, today)
        elif kind in ("pdf", "docx", "xlsx", "xls", "gorsel"):
            cached = cache.get(final)
            if cached and cached.get("sha256") == sha:
                doc = Doc.from_cache(final, cached)
                doc.link_text, doc.parent_title = ltext or doc.link_text, parent or doc.parent_title
                res.unchanged += 1
            elif kind != "gorsel" or (ocr_left > 0 and LINK_STRONG.search(fold(ltext))):
                if kind == "gorsel":
                    ocr_left -= 1
                ex = common.extract(final, r.content, r.ctype)
                doc = build_doc(final, kind, ex.text.splitlines(), ltext, ltext, parent, r.last_modified, sha, today)
                res.reparsed += 1
            title = ltext
        else:
            continue
        if doc:
            res.docs.append(doc)
        page_title = title if kind == "html" else parent
        if depth >= MAX_DEPTH:
            continue
        for u, t in links:
            u = urldefrag(u)[0]
            if u in seen:
                continue
            if not official_url(u):
                host = (urlparse(u).hostname or "").lower()
                if host and u.startswith(("http://", "https://")) and ISTIRAK_HINT.search(fold(f"{t} {host}")):
                    res.istirak_adaylari.add((host, t[:80]))
                continue
            if not same_site(u, root):
                continue
            s = link_score(u, t)
            if s <= 0 or (s < 4 and _DOC_EXT.search(urlparse(u).path)):
                continue
            seen.add(u)
            queue.append((s - depth, depth + 1, u, t, page_title))
    return res


def recheck_source(url: str, cached: dict, fetcher: common.Fetcher, robots: Robots,
                   today: date) -> tuple[str, Doc | None]:
    """Haftalık kontrol: 'ayni' | 'degisti' | 'yok' | 'hata'."""
    if not official_url(url) or not robots.allowed(url):
        return "hata", None
    r = fetcher.get(url)
    if not r.ok:
        return ("yok" if r.status in (404, 410) else "hata"), None
    if (r.sha256 or "") == cached.get("sha256"):
        return "ayni", None
    kind = common.detect_kind(r.final_url or url, r.ctype)
    if kind == "html":
        lines, _links, title = html_lines(r.content, url)
    else:
        lines, title = common.extract(url, r.content, r.ctype).text.splitlines(), cached.get("title", "")
    doc = build_doc(url, kind, lines, title, cached.get("link_text", ""), cached.get("parent_title", ""),
                    r.last_modified, r.sha256 or "", today)
    return "degisti", doc


# --------------------------------------------------------------------------- eşleme

@dataclass
class Facility:
    rec: dict
    muni: Municipality | None
    sites: list[str]

    @property
    def key(self) -> str:
        return prices.facility_key(self.rec["il"], self.rec["isim"])


def _add_site(sites: list[str], d: str | None) -> None:
    if d and d not in sites:
        sites.append(d)


def build_facilities(sosyal: list[dict], resolved: dict[str, str | None]) -> list[Facility]:
    out = []
    for rec in sosyal:
        if not rec.get("il") or not rec.get("isim"):
            continue
        muni = municipality_of(rec)
        sites: list[str] = []
        if muni:
            _add_site(sites, resolved.get(muni.key))
            for d in ISTIRAK.get(muni.key, []):
                _add_site(sites, d)
        else:
            # Adında belediye geçmeyen tesis: yalnız belgede kendi adı geçerse eşlenir.
            ilce = rec.get("ilce") or ""
            for m in (Municipality(rec["il"], ilce) if _match_ilce(rec["il"], ilce) else None,
                      Municipality(rec["il"], "")):
                if m:
                    _add_site(sites, resolved.get(m.key))
                    for d in ISTIRAK.get(m.key, []):
                        _add_site(sites, d)
        out.append(Facility(rec, muni, sites))
    return out


def municipalities_needed(sosyal: list[dict]) -> set[Municipality]:
    need: set[Municipality] = set()
    for rec in sosyal:
        if not rec.get("il") or not rec.get("isim"):
            continue
        muni = municipality_of(rec)
        if muni:
            need.add(muni)
            continue
        ilce = rec.get("ilce") or ""
        if _match_ilce(rec["il"], ilce):
            need.add(Municipality(rec["il"], ilce))
        need.add(Municipality(rec["il"], ""))
    return need


def menu_dict(fac_rec: dict, muni: Municipality | None, doc: Doc, scope: str) -> dict:
    m = {
        "il": fac_rec["il"],
        "isim": fac_rec["isim"],
        "kapsam": scope,
        "kaynak": doc.url,
        "kaynak_adi": (muni.name if muni else urlparse(doc.url).hostname or ""),
        "belge": (doc.title or doc.link_text or "").strip()[:140],
        "yil": doc.year,
        "kategoriler": group_items(doc.items),
    }
    sd = source_date(doc)
    if sd:
        m["kaynak_tarihi"] = sd
    return m


def _conflicting(a: Doc, b: Doc) -> bool:
    """Aynı ürün iki belgede farklı fiyatlıysa True."""
    pa = {fold(i.name): i.price for i in a.items}
    return any(fold(i.name) in pa and pa[fold(i.name)] != i.price for i in b.items)


def pick_menu(fac: Facility, site_results: dict[str, SiteResult], today: date,
              approvals: dict | None = None) -> tuple[dict | None, dict | None]:
    """(yayımlanacak menü, inceleme kaydı). Emin olunamayan eşleşme ve tarihsiz çelişkili kaynak yayımlanmaz."""
    approved_match = set((approvals or {}).get("eslesme", []))
    tokens = distinctive_tokens(fac.rec, fac.muni)
    fac_phones = phones_in(f"{fac.rec.get('telefon', '')} {fac.rec.get('aciklama', '')}")
    cands: list[tuple[tuple, Doc, str]] = []
    unsure: list[tuple[float, Doc]] = []
    for d in fac.sites:
        sr = site_results.get(d)
        if not sr or not sr.ok:
            continue
        for doc in sr.docs:
            if not recent_enough(doc, today):
                continue
            ident = f"{doc.title} {doc.parent_title} {doc.link_text} {doc.url} {doc.text_head[:600]}"
            if (mentions_facility(ident, tokens) or (fac_phones & doc.phones)
                    or f"{fac.key}|{doc.url}" in approved_match):
                scope = "tesis"
            elif fac.muni and (doc.mentions_sosyal or "sosyal tesis" in fold(ident)):
                scope = "belediye"
            else:
                r = match_ratio(ident, tokens)
                if r >= 0.5 and sum(len(t) for t in tokens) >= 5:
                    unsure.append((r, doc))
                continue
            rank = (scope == "tesis", doc.year or 0, source_date(doc) or "", len(doc.items))
            cands.append((rank, doc, scope))
    if not cands:
        if unsure:
            r, doc = max(unsure, key=lambda x: x[0])
            return None, {"tur": "belirsiz_eslesme", "il": fac.rec["il"], "isim": fac.rec["isim"],
                          "kaynak": doc.url, "belge": doc.title[:120], "benzerlik": round(r, 2),
                          "onay_anahtari": f"{fac.key}|{doc.url}"}
        return None, None
    cands.sort(key=lambda c: c[0], reverse=True)
    best_rank, best, scope = cands[0]
    for rank, other, other_scope in cands[1:]:
        if other.url == best.url or other_scope != scope:
            continue
        same_date = (rank[1], rank[2]) == (best_rank[1], best_rank[2])
        if same_date and not best_rank[2] and _conflicting(best, other):
            return None, {"tur": "celiskili_kaynak", "il": fac.rec["il"], "isim": fac.rec["isim"],
                          "kaynak": best.url, "diger_kaynak": other.url,
                          "detay": "Aynı ürün iki resmî belgede farklı fiyatlı ve belgelerin tarihi ayırt edilemiyor."}
    return menu_dict(fac.rec, fac.muni, best, scope), None


# --------------------------------------------------------------------------- çalıştırma

def load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path: Path, obj, indent: int = 2) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")
    tmp.replace(path)


def resolve_domains(munis: set[Municipality], probe, robots, state: dict, today: date) -> dict[str, str | None]:
    cache: dict = state.setdefault("alanlar", {})
    resolved: dict[str, str | None] = {}

    def one(m: Municipality) -> tuple[str, str | None, bool]:
        cached = cache.get(m.key) or {}
        if cached.get("alan") is None and cached.get("denendi"):
            try:
                if (today - date.fromisoformat(cached["denendi"])).days < NO_DOMAIN_RETRY_DAYS:
                    return m.key, None, False
            except ValueError:
                pass
        if time.monotonic() > _DEADLINE:
            return m.key, None, False
        cands = candidate_domains(m)
        if cached.get("alan") in cands:
            cands = [cached["alan"]] + [c for c in cands if c != cached["alan"]]
        for d in cands:
            start, _err = homepage(d, probe, robots, m.il)
            if start:
                return m.key, d, True
        return m.key, None, True

    with ThreadPoolExecutor(WORKERS) as ex:
        for key, dom, tried in ex.map(one, sorted(munis, key=lambda m: m.key)):
            resolved[key] = dom
            if dom:
                cache[key] = {"alan": dom}
            elif tried:
                cache[key] = {"alan": None, "denendi": today.isoformat()}
    return resolved


@dataclass
class RunResult:
    found: dict[str, dict] = field(default_factory=dict)
    reviews: list[dict] = field(default_factory=list)
    not_found: set[str] = field(default_factory=set)
    keep: set[str] = field(default_factory=set)
    checked: int = 0
    errors: dict[str, str] = field(default_factory=dict)
    sites: int = 0
    reparsed: int = 0
    unchanged_sources: int = 0
    istirak: set = field(default_factory=set)
    keep_all: bool = False


def run_full(sosyal: list[dict], state: dict, sources: dict, fetcher, probe, robots, today: date,
             approvals: dict) -> RunResult:
    munis = municipalities_needed(sosyal)
    print(f"{len(sosyal)} tesis, {len(munis)} belediye")
    resolved = resolve_domains(munis, probe, robots, state, today)
    domains = sorted({d for d in resolved.values() if d}
                     | {d for k, ds in ISTIRAK.items() if k in resolved for d in ds})
    il_of = {}
    for d in domains:
        keys = [k for k, v in resolved.items() if v == d] or [k for k, ds in ISTIRAK.items() if d in ds]
        il_of[d] = keys[0].split("|")[0] if keys else ""
    print(f"{len(domains)} site taranacak")

    site_results: dict[str, SiteResult] = {}
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {d: ex.submit(crawl_site, d, il_of[d], fetcher, robots, today, sources, probe) for d in domains}
        for i, (d, fut) in enumerate(futs.items(), 1):
            try:
                site_results[d] = fut.result()
            except Exception as e:  # noqa: BLE001
                site_results[d] = SiteResult(d, False, error=f"{type(e).__name__}: {e}"[:200])
            if i % 25 == 0:
                print(f"  tarandı: {i}/{len(domains)}")

    rr = RunResult(sites=len(site_results))
    for d, sr in site_results.items():
        if not sr.ok:
            rr.errors[d] = sr.error or "bilinmeyen hata"
        rr.reparsed += sr.reparsed
        rr.unchanged_sources += sr.unchanged
        rr.istirak |= {(d, h, t) for h, t in sr.istirak_adaylari}
        for doc in sr.docs:
            sources[doc.url] = {**doc.to_cache(), "gorulme": today.isoformat()}
    rr.keep_all = bool(site_results) and len(rr.errors) / len(site_results) > MAX_SITE_ERROR_RATIO

    for fac in build_facilities(sosyal, resolved):
        reached = [d for d in fac.sites if site_results.get(d) and site_results[d].ok]
        if reached:
            rr.checked += 1
        menu, review = pick_menu(fac, site_results, today, approvals)
        if menu:
            rr.found[fac.key] = menu
        elif review:
            rr.reviews.append(review)
            rr.keep.add(fac.key)
        elif reached and len(reached) == len(fac.sites) and not rr.keep_all:
            rr.not_found.add(fac.key)
        else:
            rr.keep.add(fac.key)
    return rr


def run_known(published: list[dict], sources: dict, fetcher, robots, today: date) -> RunResult:
    """Haftalık: yalnız yayımlanmış menülerin kaynak belgelerini yeniden indirir; SHA256 aynıysa ayrıştırmaz."""
    rr = RunResult()
    belge = {p["kaynak"]: p.get("belge", "") for p in published if p.get("kaynak")}
    urls = sorted(belge)

    def one(u: str):
        return (u, *recheck_source(u, sources.get(u) or {"link_text": belge[u]}, fetcher, robots, today))

    changed: dict[str, Doc] = {}
    gone: set[str] = set()
    with ThreadPoolExecutor(WORKERS) as ex:
        for u, status, doc in ex.map(one, urls):
            rr.sites += 1
            if status == "ayni":
                rr.unchanged_sources += 1
            elif status == "degisti" and doc and doc.items:
                rr.reparsed += 1
                changed[u] = doc
                sources[u] = {**doc.to_cache(), "gorulme": today.isoformat()}
            elif status == "degisti":
                rr.reparsed += 1
                rr.reviews.append({"tur": "kaynak_okunamadi", "kaynak": u,
                                   "detay": "Belge değişti ama yeni içerikten fiyat çıkarılamadı; eski fiyatlar korundu."})
            elif status == "yok":
                gone.add(u)
            else:
                rr.errors[u] = status
    for p in published:
        key = prices.facility_key(p["il"], p["isim"])
        if p.get("kaynak") in gone:
            rr.not_found.add(key)
            rr.checked += 1
        doc = changed.get(p.get("kaynak"))
        if not doc:
            continue
        m = {k: v for k, v in p.items() if k in ("il", "isim", "kapsam", "kaynak", "kaynak_adi", "belge")}
        m.update({"yil": doc.year, "kategoriler": group_items(doc.items)})
        if source_date(doc):
            m["kaynak_tarihi"] = source_date(doc)
        rr.found[key] = m
        rr.checked += 1
    return rr


def prune_sources(sources: dict, published: list[dict], today: date) -> dict:
    used = {p.get("kaynak") for p in published}
    out = {}
    for u, c in sources.items():
        try:
            age = (today - date.fromisoformat(c.get("gorulme", "2000-01-01"))).days
        except ValueError:
            age = 10**6
        if u in used or age <= 180:
            out[u] = c
    return dict(sorted(out.items()))


def main() -> int:
    today = date.today()
    data = load_json(MASTER, {})
    sosyal = data.get("sosyal") or []
    only_il = {fold(x) for x in os.environ.get("MENU_ONLY_IL", "").split(",") if x.strip()}
    if only_il:
        sosyal = [r for r in sosyal if fold(r.get("il", "")) in only_il]
    state = load_json(STATE, {})
    sources = load_json(SOURCES, {})
    approvals = load_json(APPROVALS, {"buyuk_degisim": [], "eslesme": []})
    prev_doc = load_json(OUT, {"items": []})
    prev_items = prev_doc.get("items", [])
    in_scope = [p for p in prev_items if not only_il or fold(p["il"]) in only_il]
    untouched = [p for p in prev_items if only_il and fold(p["il"]) not in only_il]

    fetcher = common.Fetcher(per_host_delay=1.0, timeout=20.0, retries=2, max_bytes=20_000_000)
    probe = common.Fetcher(per_host_delay=1.0, timeout=PROBE_TIMEOUT, retries=PROBE_RETRIES, max_bytes=2_000_000)
    for f in (fetcher, probe):
        f.session.headers["User-Agent"] = UA
    robots = Robots(probe)

    if MODE == "known":
        rr = run_known(in_scope, sources, fetcher, robots, today)
    else:
        rr = run_full(sosyal, state, sources, fetcher, probe, robots, today, approvals)

    upd = prices.update_items(in_scope, rr.found, rr.not_found, rr.keep, today, approvals,
                              touch_checked=MODE != "known")
    items = sorted(upd.items + untouched, key=lambda x: (prices.fold_key(x["il"]), prices.fold_key(x["isim"])))
    reviews = rr.reviews + upd.reviews
    changed = items != prev_items

    if not DRY_RUN:
        if changed or not HISTORY.exists():
            write_json(OUT, {
                "not": "Belediye sosyal tesislerinin kendi resmî sitelerinde yayımlanan yeme-içme fiyatları. "
                       "Aylık tam tarama + haftalık kaynak kontrolü (sosyal_menu/menu.py). "
                       "kapsam: 'tesis' = tesisin kendi menüsü, 'belediye' = belediyenin sosyal tesisler için "
                       "genel fiyat tarifesi. durum: 'guncel' | 'kaynak_bulunamadi' (son doğrulanan fiyatlar korunur).",
                "guncelleme": today.isoformat(),
                "items": items,
            })
            history = load_json(HISTORY, {})
            prices.update_history(history, items, today)
            write_json(HISTORY, dict(sorted(history.items())), indent=1)
        if upd.changes:
            write_json(CHANGES, load_json(CHANGES, []) + upd.changes, indent=1)
        if MODE == "known":
            old = load_json(REVIEW, [])
            seen = {json.dumps(r, sort_keys=True) for r in old}
            reviews_out = old + [r for r in reviews if json.dumps(r, sort_keys=True) not in seen]
        else:
            reviews_out = reviews
        if reviews_out != load_json(REVIEW, []):
            write_json(REVIEW, reviews_out, indent=1)
        write_json(SOURCES, prune_sources(sources, items, today), indent=1)
        if MODE != "known":
            write_json(STATE, {"alanlar": dict(sorted(state.get("alanlar", {}).items()))}, indent=1)
    write_report(today, len(sosyal), rr, upd, reviews, items, changed)
    return 0


def write_report(today: date, total: int, rr: RunResult, upd: prices.UpdateResult, reviews: list[dict],
                 items: list[dict], changed: bool) -> None:
    REPORTS.mkdir(exist_ok=True)
    s = upd.stats
    summary = {
        "tarih": today.isoformat(), "mod": MODE, "dry_run": DRY_RUN,
        "toplam_belediye_tesisi": total if MODE != "known" else len(items),
        "kontrol_edilen": rr.checked,
        "fiyat_bulunan": s.fiyat_bulunan_tesis,
        "fiyat_guncellenen": s.guncellenen_fiyat,
        "yeni_fiyat_eklenen": s.yeni_fiyat,
        "kaynak_bulunamayan": s.kaynak_bulunamayan,
        "review_gereken": len(reviews),
        "hata": len(rr.errors),
        "taranan_site": rr.sites,
        "yeniden_ayristirilan_belge": rr.reparsed,
        "degismeyen_belge_sha256": rr.unchanged_sources,
        "yayimlanan_kayit": len(items),
        "veri_degisti": changed,
        "hatalarin_cogu_nedeniyle_silme_yapilmadi": rr.keep_all,
    }
    title = "aylık tam tarama" if MODE != "known" else "haftalık kaynak kontrolü"
    lines = [
        f"# Belediye tesisleri yemek fiyatı taraması — {today.isoformat()} ({title})",
        "",
        f"- Mod: {'DRY RUN (veri yazılmadı)' if DRY_RUN else 'canlı'}",
        f"- Toplam Belediye Tesisi: {summary['toplam_belediye_tesisi']}",
        f"- Kontrol edilen: {rr.checked}",
        f"- Fiyat bulunan: {s.fiyat_bulunan_tesis}",
        f"- Fiyat güncellenen: {s.guncellenen_fiyat}",
        f"- Yeni fiyat eklenen: {s.yeni_fiyat}",
        f"- Kaynak bulunamayan: {s.kaynak_bulunamayan}",
        f"- Review gereken: {len(reviews)}",
        f"- Hata: {len(rr.errors)}",
        f"- Taranan site/kaynak: {rr.sites} · yeniden ayrıştırılan belge: {rr.reparsed} · "
        f"değişmeyen (SHA256 aynı): {rr.unchanged_sources}",
        f"- sosyal_menuler.json kayıt: {len(items)} · değişti: {'evet' if changed else 'hayır'}",
    ]
    if rr.keep_all:
        lines.append("- UYARI: sitelerin yarısından fazlası hata verdi; hiçbir fiyat 'kaynak bulunamadı' yapılmadı.")
    lines += ["", "## Fiyat bulunan tesisler", ""]
    for m in sorted(rr.found.values(), key=lambda x: (fold(x["il"]), fold(x["isim"]))):
        n = sum(len(c["urunler"]) for c in m["kategoriler"])
        lines.append(f"- {m['il']} — {m['isim']}: {n} ürün, {m['kapsam']}, {m['yil'] or 'yıl yok'} — {m['kaynak']}")
    lines += ["", "## Fiyat değişiklikleri", ""]
    lines += [f"- {c['il']} — {c['isim']}: {c['urun']} {c['eski']} → {c['yeni']} TL" for c in upd.changes]
    lines += ["", "## İnceleme gereken (review_required)", ""]
    for r in reviews:
        change = f"{r['eski']} → {r['yeni']} " if "yeni" in r else ""
        lines.append(f"- [{r['tur']}] {r.get('il', '')} — {r.get('isim', '')}: {r.get('urun', '')} {change}"
                     f"{r.get('kaynak', '')}")
    lines += ["", "## Belediye iştiraki adayları (resmî ilişki elle doğrulanıp config.json 'istirak' alanına eklenmeli)", ""]
    lines += [f"- {d} → {h} ({t})" for d, h, t in sorted(rr.istirak)[:200]]
    lines += ["", "## Erişilemeyen siteler", ""]
    lines += [f"- {d}: {e}" for d, e in sorted(rr.errors.items())]
    stamp = f"{today.isoformat()}-{MODE}"
    (REPORTS / f"{stamp}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (REPORTS / f"{stamp}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n".join(lines[:14]))


if __name__ == "__main__":
    sys.exit(main())


