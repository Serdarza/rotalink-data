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
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib import robotparser
from urllib.parse import urldefrag, urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "price_research"))
import common  # noqa: E402  (price_research/common.py: nazik HTTP + PDF/Excel okuma)

MASTER = ROOT / "master_database_updated.json"
OUT = ROOT / "sosyal_menuler.json"
STATE = HERE / "state.json"
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
    return any(host == h or host.endswith("." + h) for h in CONFIG.get("ek_resmi_alanlar", []))


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
    ("Ana yemekler", re.compile(
        r"kebap|kebab|izgara|kofte|\bsis\b|beyti|iskender|doner|tavuk|\bet\b|bonfile|antrikot|pirzola|kanat|"
        r"balik|levrek|cipura|hamsi|alabalik|somon|manti|pilav|makarna|\bpide|lahmacun|pizza|hamburger|burger|"
        r"durum|tantuni|guvec|sac tava|sote|fasulye|fajita|wrap|yemek|\bmenu|kavurma|biftek|steak|schnitzel|"
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
                    _add(items, seen, pending_name, price, header_cat, header_excluded)
            pending_name = None
            continue
        hit = split_item(line)
        if hit:
            _add(items, seen, hit[0], hit[1], header_cat, header_excluded)
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


def _add(items, seen, raw_name, price, header_cat, header_excluded) -> None:
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
    items.append(MenuItem(name, price, cat))


CATEGORY_ORDER = [c for c, _ in CATEGORIES]
DISPLAY_ORDER = ["Kahvaltı", "Çorbalar", "Ana yemekler", "Salatalar", "Atıştırmalıklar", "Tatlılar",
                 "Sıcak içecekler", "Soğuk içecekler"]


def group_items(items: list[MenuItem]) -> list[dict]:
    by: dict[str, list[dict]] = {}
    for it in items:
        by.setdefault(it.category, []).append({"ad": it.name, "fiyat": it.price})
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
        if "belediye" not in text and not any(h in domain for h in CONFIG.get("ek_resmi_alanlar", [])):
            return None, "belediye sitesi değil"
        if il and f" {fold(il)} " not in f" {text} ":
            return None, f"sayfada {il} geçmiyor"
        return final, None
    return None, last_err


_DOC_EXT = re.compile(r"\.(pdf|docx?|xlsx?|jpe?g|png|webp)$", re.I)


def crawl_site(domain: str, il: str, fetcher: common.Fetcher, robots: Robots, today: date) -> SiteResult:
    if time.monotonic() > _DEADLINE:
        return SiteResult(domain, False, error="zaman sınırı: bu ay taranamadı")
    start, err = homepage(domain, fetcher, robots, il)
    if not start:
        return SiteResult(domain, False, error=err, blocked=bool(err and "robots" in err))
    root = site_root(urlparse(start).hostname or domain)
    queue: list[tuple[int, int, str, str, str]] = [(100, 0, start, "", "")]
    seen = {urldefrag(start)[0]}
    res = SiteResult(domain, True)
    ocr_left = MAX_OCR_PER_SITE
    while queue and res.pages < MAX_PAGES_PER_SITE and time.monotonic() < _DEADLINE:
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
        links: list[tuple[str, str]] = []
        if kind == "html":
            lines, links, title = html_lines(r.content, final)
        elif kind in ("pdf", "docx", "xlsx", "xls") or (kind == "gorsel" and ocr_left > 0 and LINK_STRONG.search(fold(ltext))):
            if kind == "gorsel":
                ocr_left -= 1
            ex = common.extract(final, r.content, r.ctype)
            lines, title = ex.text.splitlines(), ltext
        else:
            continue
        items = parse_menu(lines)
        head = "\n".join(lines[:80])
        if len(items) >= MIN_ITEMS and FOOD_CONTEXT.search(fold(f"{title} {ltext} {head} {final}")):
            res.docs.append(Doc(final, kind, title, ltext, doc_year(head, final, ltext, today), items, head,
                                r.last_modified, parent, "sosyal tesis" in fold("\n".join(lines))))
        page_title = title if kind == "html" else parent
        if depth >= MAX_DEPTH:
            continue
        for u, t in links:
            u = urldefrag(u)[0]
            if u in seen or not official_url(u) or not same_site(u, root):
                continue
            s = link_score(u, t)
            if s <= 0 or (s < 4 and _DOC_EXT.search(urlparse(u).path)):
                continue
            seen.add(u)
            queue.append((s - depth, depth + 1, u, t, page_title))
    return res


# --------------------------------------------------------------------------- eşleme ve birleştirme

@dataclass
class Facility:
    rec: dict
    muni: Municipality | None
    sites: list[str]

    @property
    def key(self) -> str:
        return f"{fold(self.rec['il'])}|{fold(self.rec['isim'])}"


def build_facilities(sosyal: list[dict], resolved: dict[str, str | None]) -> list[Facility]:
    out = []
    for rec in sosyal:
        if not rec.get("il") or not rec.get("isim"):
            continue
        muni = municipality_of(rec)
        sites: list[str] = []
        if muni and resolved.get(muni.key):
            sites.append(resolved[muni.key])
        if not muni:
            # Adında belediye geçmeyen tesis: yalnız belgede kendi adı geçerse eşlenir.
            ilce = rec.get("ilce") or ""
            for m in (Municipality(rec["il"], ilce) if _match_ilce(rec["il"], ilce) else None,
                      Municipality(rec["il"], "")):
                if m and resolved.get(m.key) and resolved[m.key] not in sites:
                    sites.append(resolved[m.key])
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


def pick_menu(fac: Facility, site_results: dict[str, SiteResult], today: date) -> dict | None:
    tokens = distinctive_tokens(fac.rec, fac.muni)
    best, best_rank = None, None
    for d in fac.sites:
        sr = site_results.get(d)
        if not sr or not sr.ok:
            continue
        for doc in sr.docs:
            if not recent_enough(doc, today):
                continue
            ident = f"{doc.title} {doc.parent_title} {doc.link_text} {doc.url} {doc.text_head[:600]}"
            if mentions_facility(ident, tokens):
                scope = "tesis"
            elif fac.muni and (doc.mentions_sosyal or "sosyal tesis" in fold(ident)):
                scope = "belediye"
            else:
                continue
            rank = (scope == "tesis", doc.year or 0, len(doc.items))
            if best_rank is None or rank > best_rank:
                best, best_rank = (doc, scope), rank
    if not best:
        return None
    doc, scope = best
    return {
        "il": fac.rec["il"],
        "isim": fac.rec["isim"],
        "kapsam": scope,
        "kaynak": doc.url,
        "kaynak_adi": (fac.muni.name if fac.muni else urlparse(doc.url).hostname or ""),
        "belge": (doc.title or doc.link_text or "").strip()[:140],
        "yil": doc.year,
        "kategoriler": group_items(doc.items),
    }


def same_menu(a: dict, b: dict) -> bool:
    keys = ("kapsam", "kaynak", "yil", "kategoriler")
    return all(a.get(k) == b.get(k) for k in keys)


def merge(prev_items: list[dict], found: dict[str, dict], unreachable: set[str], today: date,
          keep_all: bool) -> list[dict]:
    """found: tesis anahtarı → yeni menü. unreachable: sitesine ulaşılamayan tesis anahtarları."""
    prev = {f"{fold(p['il'])}|{fold(p['isim'])}": p for p in prev_items}
    out = []
    for k, item in found.items():
        old = prev.get(k)
        if old and same_menu(old, item):
            out.append(old)
        else:
            out.append({**item, "kontrol": today.isoformat()})
    for k, old in prev.items():
        if k in found:
            continue
        try:
            age = (today - date.fromisoformat(old.get("kontrol", "2000-01-01"))).days
        except ValueError:
            age = 10**6
        if keep_all or (k in unreachable and age <= KEEP_DAYS_ON_ERROR):
            out.append(old)
    out.sort(key=lambda x: (fold(x["il"]), fold(x["isim"])))
    return out


# --------------------------------------------------------------------------- çalıştırma

def load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path: Path, obj, indent: int = 2) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")
    tmp.replace(path)


def resolve_domains(munis: set[Municipality], fetcher, robots, state: dict, today: date) -> dict[str, str | None]:
    cache: dict = state.setdefault("alanlar", {})
    resolved: dict[str, str | None] = {}

    def one(m: Municipality) -> tuple[str, str | None, list[str]]:
        notes = []
        cached = cache.get(m.key)
        cands = candidate_domains(m)
        if cached and cached.get("alan") and cached["alan"] in cands:
            cands = [cached["alan"]] + [c for c in cands if c != cached["alan"]]
        for d in cands:
            start, err = homepage(d, fetcher, robots, m.il)
            if start:
                return m.key, d, notes
            notes.append(f"{d}: {err}")
        return m.key, None, notes

    with ThreadPoolExecutor(WORKERS) as ex:
        for key, dom, _notes in ex.map(one, sorted(munis, key=lambda m: m.key)):
            resolved[key] = dom
            if dom:
                cache[key] = {"alan": dom}
    return resolved


def main() -> int:
    today = date.today()
    data = load_json(MASTER, {})
    sosyal = data.get("sosyal") or []
    only_il = {fold(x) for x in os.environ.get("MENU_ONLY_IL", "").split(",") if x.strip()}
    if only_il:
        sosyal = [r for r in sosyal if fold(r.get("il", "")) in only_il]
    state = load_json(STATE, {})
    prev_doc = load_json(OUT, {"items": []})

    fetcher = common.Fetcher(per_host_delay=1.0, timeout=25.0, retries=2, max_bytes=20_000_000)
    fetcher.session.headers["User-Agent"] = UA
    robots = Robots(fetcher)

    munis = municipalities_needed(sosyal)
    print(f"{len(sosyal)} tesis, {len(munis)} belediye")
    resolved = resolve_domains(munis, fetcher, robots, state, today)
    domains = sorted({d for d in resolved.values() if d})
    il_of = {d: next(k.split("|")[0] for k, v in resolved.items() if v == d) for d in domains}
    print(f"{len(domains)} belediye sitesi bulundu")

    site_results: dict[str, SiteResult] = {}
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {d: ex.submit(crawl_site, d, il_of[d], fetcher, robots, today) for d in domains}
        for i, (d, fut) in enumerate(futs.items(), 1):
            try:
                site_results[d] = fut.result()
            except Exception as e:  # noqa: BLE001
                site_results[d] = SiteResult(d, False, error=f"{type(e).__name__}: {e}"[:200])
            if i % 25 == 0:
                print(f"  tarandı: {i}/{len(domains)}")

    facilities = build_facilities(sosyal, resolved)
    found: dict[str, dict] = {}
    unreachable: set[str] = set()
    for fac in facilities:
        menu = pick_menu(fac, site_results, today)
        if menu:
            found[fac.key] = menu
        elif not fac.sites or any(not site_results.get(d, SiteResult(d, False)).ok for d in fac.sites):
            unreachable.add(fac.key)

    errors = sum(1 for r in site_results.values() if not r.ok)
    keep_all = bool(site_results) and errors / len(site_results) > MAX_SITE_ERROR_RATIO
    prev_items = prev_doc.get("items", [])
    in_scope = [p for p in prev_items if not only_il or fold(p["il"]) in only_il]
    untouched = [p for p in prev_items if only_il and fold(p["il"]) not in only_il]
    items = merge(in_scope, found, unreachable, today, keep_all) + untouched
    items.sort(key=lambda x: (fold(x["il"]), fold(x["isim"])))

    changed = items != prev_doc.get("items", [])
    if changed and not DRY_RUN:
        write_json(OUT, {
            "not": "Belediye sosyal tesislerinin kendi resmî sitelerinde yayımlanan yeme-içme fiyatları. "
                   "Aylık otomatik tarama (sosyal_menu/menu.py). kapsam: 'tesis' = tesisin kendi menüsü, "
                   "'belediye' = belediyenin sosyal tesisler için genel fiyat tarifesi.",
            "guncelleme": today.isoformat(),
            "items": items,
        })
    write_json(STATE, {"alanlar": dict(sorted(state.get("alanlar", {}).items()))}, indent=1)
    write_report(today, sosyal, munis, resolved, site_results, found, items, keep_all, changed)
    return 0


def write_report(today, sosyal, munis, resolved, site_results, found, items, keep_all, changed) -> None:
    REPORTS.mkdir(exist_ok=True)
    errors = {d: r.error for d, r in site_results.items() if not r.ok}
    docs = sum(len(r.docs) for r in site_results.values())
    lines = [
        f"# Sosyal tesis menü taraması — {today.isoformat()}",
        "",
        f"- Mod: {'DRY RUN (veri yazılmadı)' if DRY_RUN else 'canlı'}",
        f"- Tesis: {len(sosyal)} · belediye: {len(munis)} · sitesi bulunan: {sum(1 for v in resolved.values() if v)}",
        f"- Taranan site: {len(site_results)} · hata: {len(errors)} · menü belgesi: {docs}",
        f"- Bu ay menüsü bulunan tesis: {len(found)} "
        f"(tesis menüsü {sum(1 for m in found.values() if m['kapsam'] == 'tesis')}, "
        f"belediye tarifesi {sum(1 for m in found.values() if m['kapsam'] == 'belediye')})",
        f"- sosyal_menuler.json kayıt: {len(items)} · değişti: {'evet' if changed else 'hayır'}",
    ]
    if keep_all:
        lines.append("- UYARI: sitelerin yarısından fazlası hata verdi; önceki menüler korunarak silme yapılmadı.")
    lines += ["", "## Menüsü bulunan tesisler", ""]
    for m in sorted(found.values(), key=lambda x: (fold(x["il"]), fold(x["isim"]))):
        n = sum(len(c["urunler"]) for c in m["kategoriler"])
        lines.append(f"- {m['il']} — {m['isim']}: {n} ürün, {m['kapsam']}, {m['yil'] or 'yıl yok'} — {m['kaynak']}")
    lines += ["", "## Erişilemeyen siteler", ""]
    lines += [f"- {d}: {e}" for d, e in sorted(errors.items())]
    (REPORTS / f"{today.isoformat()}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:8]))


if __name__ == "__main__":
    sys.exit(main())
