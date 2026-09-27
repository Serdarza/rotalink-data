# fiyatlar.json — detaylı tarife formatı

Her tesis kaydı `il` + `isim` ile master veritabanındaki tesisle eşleşir (birebir aynı yazılmalı).

## Özet alanlar (mevcut, değişmedi)

| Alan | Anlamı |
| --- | --- |
| `fiyat_sivil` | Sivil misafir fiyatı / aralığı (metin) |
| `fiyat_kamu_personeli` | Kamu personeli fiyatı / aralığı |
| `fiyat_kurum_personeli` | Kurum personeli (öğretmen, teşkilat mensubu vb.) |
| `kaynak` | Kaynak URL (uygulamada tıklanabilir gösterilir) |
| `gecerlilik` | Geçerlilik metni |

`null` değer = "Kalamaz", alan hiç yoksa = "Belirtilmedi".
Eski uygulama sürümleri yalnızca bu alanları okur; yeni kayıtlarda da doldurulması önerilir.

## Detaylı tarife (`tarife`, isteğe bağlı)

Hiçbir alt alan zorunlu değildir; boş bırakılan bölüm uygulamada görünmez.
Veri yoksa alan eklenmez — tahmini değer yazılmaz.

```json
"tarife": {
  "baslik": "2026 Konaklama Tarifesi",
  "donem": "2026",
  "birim": "gecelik",
  "guncelleme": "2026-09-27",
  "dogrulama": "resmi_kaynak",
  "kategoriler": [
    { "id": "ogretmen", "ad": "Öğretmen / Bakanlık Personeli" },
    { "id": "kamu", "ad": "Kamu" },
    { "id": "sivil", "ad": "Sivil" }
  ],
  "tablolar": [
    {
      "baslik": "Yaz dönemi",
      "donem": "01.06.2026 – 15.09.2026",
      "birim": "kişi başı / gece",
      "aciklama": "Ana bina",
      "kategoriler": ["Akademik", "Öğrenci"],
      "satirlar": [
        { "ad": "Tek Kişi Konaklama", "kisi": 1, "aciklama": "…", "birim": "oda/gece",
          "fiyatlar": { "ogretmen": 1850, "kamu": 2250, "sivil": "Bilgi için arayınız" } }
      ]
    }
  ],
  "kurallar":   ["Tek kişi konaklamada +%50 fiyat farkı uygulanır."],
  "giris_saati": "14:00",
  "cikis_saati": "11:00",
  "dahil":      ["Kahvaltı", "KDV"],
  "indirimler": ["0-6 yaş ücretsiz"],
  "ek_ucretler": ["Ek yatak: 500 TL"],
  "notlar":     ["Bayramlarda fiyat değişikliği olabilir."]
}
```

- **kategoriler**: fiyat kolonları. Tarife düzeyinde verilirse tüm tablolar kullanır; tablo kendi listesini verirse onu kullanır. Düz metin (`"Kamu"`) veya `{id, ad}` olabilir.
- **tablolar**: sezon / bina / hafta içi-sonu gibi ayrı tarifeler için birden fazla tablo. Tek tablo için `satirlar` doğrudan `tarife` altına da yazılabilir.
- **fiyatlar**: kategori id → sayı (TL, uygulama biçimlendirir) veya metin (olduğu gibi gösterilir). Anahtar yoksa hücre "—".
- **dogrulama**: `resmi_kaynak` · `tesis_dogruladi` · `kullanici_bildirimi` · `teyit_gerekli`. Bilinmiyorsa yazılmaz.
- **guncelleme**: `YYYY-AA-GG`.

Özet alanlar boşsa uygulama, tablodaki sayısal fiyatlardan kategori bazlı min–max özetini kendisi çıkarır.
Örnek kayıt: `Düzce / Akçakoca Öğretmen Evi`.
