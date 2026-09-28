# Aylık resmî fiyat kontrolü

`fiyatlar.json` içindeki kamu tesisi fiyatlarını her ayın 1'inde 04:00'te (TR) GitHub Actions üzerinde
resmî kaynaklarla karşılaştırır. Cursor'un veya bir bilgisayarın açık olması gerekmez.

## Çalışma prensibi

- **Fiyat uydurmaz, rakam yazmaz, silmez.** Yapay zekâ kullanılmaz. İş yalnızca şunları tespit eder:
  - `dogrulandi`: mevcut tarifedeki bütün rakamlar resmî kaynakta hâlâ geçiyor (veya dosya baytları aynı).
  - `degisti`: resmî kaynak değişmiş ve mevcut rakamların bir kısmı artık kaynakta yok.
  - `suresi_doldu`: tarifenin dönem bitiş tarihi geçmiş.
  - `celiski` (CONFLICT): resmî kaynaklar birbiriyle çelişiyor.
  - `olasi_yeni_tarife`: fiyatı olmayan tesisin resmî sayfasında 2026 tarihli yeni fiyat/tarife izi var.
  - `source_check_failed`: kaynağa erişilemedi. Veriye dokunulmaz.
- Canlı modda yalnızca `degisti` / `suresi_doldu` olan `resmi_kaynak` tarifeler `teyit_gerekli`
  olarak işaretlenir ve kullanıcıya not eklenir. Tarife tekrar doğrulanırsa işaret geri alınır.
  Yeni fiyatlar rapordaki resmî kaynaktan onaylanarak elle girilir.
- Yeni tesisler (MEB öğretmenevi listesi, emniyet ve kurum siteleri) `DISCOVERED` olarak raporlanır.
  MEB resmî öğretmenevi listesinde olup uygulamada olmayan öğretmenevleri, konumları OpenStreetMap'te
  kesin eşleşirse (ad, il, ilçe uyumlu; 300 m içinde kayıtlı başka tesis yok) canlı modda
  `master_database_updated.json`'a **fiyatsız** eklenir (ad, il, adres, telefon, konum).
  Tek çalışmada `otomatik_ekleme_sinir` değerinden fazla keşif çıkarsa hiçbiri eklenmez, raporlanır.
  `config.json` → `"otomatik_ekleme": false` ile kapatılabilir.
- HTML, PDF (tablolar dahil), Word (.docx), Excel (.xlsx/.xls, gizli sayfalar dahil) okunur.
  Görseller ve taranmış PDF'ler için OCR (RapidOCR) kullanılır.
- Koşullu GET (ETag / Last-Modified), alan adı başına bekleme, 429/5xx için üstel geri çekilme.
- Yazma işlemleri atomiktir: geçici dosya → JSON + şema doğrulama → yerine koyma.
  Yeni bir doğrulama hatası oluşursa dosya yazılmaz.

## Dosyalar

| Dosya | Görev |
|---|---|
| `config.json` | `canli` (false = her çalışma DRY RUN), süre/hız ayarları |
| `sources.json` | Kaynak kaydı: tesis → resmî kaynak URL'leri, kontrol yöntemi, son durum, URL hash/ETag |
| `kurumlar.json` | Keşif için kurum ana sayfaları, MEB listesi, emniyet siteleri |
| `monitor.py` | Aylık iş |
| `validate.py` | `fiyatlar.json` şema ve tutarlılık doğrulaması |
| `reports/` | `latest.md/json`, `YYYY-MM.md`, `degisiklikler.log` (TESİS / ESKİ / YENİ / KAYNAK / TARİH) |

## Canlı moda geçiş

İlk çalışmalar DRY RUN'dır (`config.json` → `"canli": false`). DRY RUN raporu incelenip onaylandıktan
sonra `canli` değeri `true` yapılır. Elle çalıştırma: Actions → "Aylık resmî fiyat kontrolü" →
Run workflow (`dry_run` kutusu işaretliyken hiçbir veri yazılmaz).

## Yerelde

```bash
pip install -r price_research/requirements.txt
python -m pytest price_research/tests -q
python price_research/validate.py
python price_research/monitor.py --dry-run --limit 20 --no-ocr
```

Gizli anahtar gerekmez. Repoya secret yazılmaz.
