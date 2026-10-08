"""81 il. Anahtar, arama katlaması; iso, OpenStreetMap sınır kodu. Yeni il uydurulmaz."""
from __future__ import annotations

ILLER: list[tuple[str, str]] = [
    ("Adana", "TR-01"), ("Adıyaman", "TR-02"), ("Afyonkarahisar", "TR-03"), ("Ağrı", "TR-04"),
    ("Amasya", "TR-05"), ("Ankara", "TR-06"), ("Antalya", "TR-07"), ("Artvin", "TR-08"),
    ("Aydın", "TR-09"), ("Balıkesir", "TR-10"), ("Bilecik", "TR-11"), ("Bingöl", "TR-12"),
    ("Bitlis", "TR-13"), ("Bolu", "TR-14"), ("Burdur", "TR-15"), ("Bursa", "TR-16"),
    ("Çanakkale", "TR-17"), ("Çankırı", "TR-18"), ("Çorum", "TR-19"), ("Denizli", "TR-20"),
    ("Diyarbakır", "TR-21"), ("Edirne", "TR-22"), ("Elazığ", "TR-23"), ("Erzincan", "TR-24"),
    ("Erzurum", "TR-25"), ("Eskişehir", "TR-26"), ("Gaziantep", "TR-27"), ("Giresun", "TR-28"),
    ("Gümüşhane", "TR-29"), ("Hakkâri", "TR-30"), ("Hatay", "TR-31"), ("Isparta", "TR-32"),
    ("Mersin", "TR-33"), ("İstanbul", "TR-34"), ("İzmir", "TR-35"), ("Kars", "TR-36"),
    ("Kastamonu", "TR-37"), ("Kayseri", "TR-38"), ("Kırklareli", "TR-39"), ("Kırşehir", "TR-40"),
    ("Kocaeli", "TR-41"), ("Konya", "TR-42"), ("Kütahya", "TR-43"), ("Malatya", "TR-44"),
    ("Manisa", "TR-45"), ("Kahramanmaraş", "TR-46"), ("Mardin", "TR-47"), ("Muğla", "TR-48"),
    ("Muş", "TR-49"), ("Nevşehir", "TR-50"), ("Niğde", "TR-51"), ("Ordu", "TR-52"),
    ("Rize", "TR-53"), ("Sakarya", "TR-54"), ("Samsun", "TR-55"), ("Siirt", "TR-56"),
    ("Sinop", "TR-57"), ("Sivas", "TR-58"), ("Tekirdağ", "TR-59"), ("Tokat", "TR-60"),
    ("Trabzon", "TR-61"), ("Tunceli", "TR-62"), ("Şanlıurfa", "TR-63"), ("Uşak", "TR-64"),
    ("Van", "TR-65"), ("Yozgat", "TR-66"), ("Zonguldak", "TR-67"), ("Aksaray", "TR-68"),
    ("Bayburt", "TR-69"), ("Karaman", "TR-70"), ("Kırıkkale", "TR-71"), ("Batman", "TR-72"),
    ("Şırnak", "TR-73"), ("Bartın", "TR-74"), ("Ardahan", "TR-75"), ("Iğdır", "TR-76"),
    ("Yalova", "TR-77"), ("Karabük", "TR-78"), ("Kilis", "TR-79"), ("Osmaniye", "TR-80"),
    ("Düzce", "TR-81"),
]


_FOLD = {
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
    "â": "a", "î": "i", "û": "u",
}


def fold(s: str) -> str:
    out = []
    for ch in (s or "").lower():
        if ch == "i" or ch == "ı":
            out.append("i")
        else:
            out.append(_FOLD.get(ch, ch))
    return " ".join("".join(out).split())


def sec(only: set[str] | None) -> list[tuple[str, str]]:
    """only boşsa 81 il. Tanımsız ad yok sayılır; liste dışına il eklenmez."""
    if not only:
        return list(ILLER)
    want = {fold(x) for x in only}
    return [row for row in ILLER if fold(row[0]) in want]
