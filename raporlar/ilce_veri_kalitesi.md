# İl / İlçe Veri Kalitesi Raporu

Tarih: 2026-10-01 · Kaynak: `master_database_updated.json` (tesisler) + `tesisler_adres.json`

Referans: İçişleri il/ilçe listesi (81 il, 973 ilçe) ile OpenStreetMap ilçe sınırları (geoBoundaries, ODbL) karşılaştırıldı; KKTC için 6 ilçe (Lefkoşa, Gazimağusa, Girne, Güzelyurt, İskele, Lefke). Büyükşehir olmayan 51 ilde merkez ilçe resmi adıyla "Merkez".

## Yöntem

Her tesis için üç bağımsız kanıt karşılaştırıldı; ilçe tahminle doldurulmadı:

1. **Konum:** koordinatın düştüğü ilçe sınırı (poligon). Başka tesisle birebir aynı koordinat zayıf kanıt sayıldı.
2. **Resmi adres:** master adresindeki `İlçe/İL`, `İlçe – İL`, `İlçe, İL` kalıpları; yoksa adreste tek geçen ilçe adı. Birden fazla farklı tesiste birebir tekrar eden (kopyalanmış) adresler kanıt sayılmadı.
3. **Tesis adı / Google adresi:** addaki ilçe adı ve `tesisler_adres.json` Google adresi destekleyici kanıt olarak kullanıldı.

Konum ve adres aynı ilçeyi gösteriyorsa kabul edildi. Çelişkide adres ilçesinin sınırı koordinata 2 km'den yakınsa adres; ad ile desteklenen taraf; aksi halde kayıt **belirsiz** listesine alındı ve ilçe alanı boş bırakıldı.

## Özet

| Ölçüt | Sayı |
|---|---:|
| Toplam tesis kaydı | 1924 |
| Tekil tesis (il + ad) | 1920 |
| İl bilgisi eksik kayıt | 0 |
| Standart dışı il adı | 0 (82 il değeri referansla birebir) |
| İlçe bilgisi eksik (önce, master `ilce`) | 1909 |
| `tesisler_adres.json` kaydı olmayan tesis (önce) | 540 |
| İlçesi doğrulanan tesis (sonra) | 1839 |
| Düzeltilen ilçe (yanlış → doğru) | 86 |
| Standartlaştırılan ilçe yazımı | 286 |
| Tamamlanan (eksik → eklendi) | 531 |
| Değişmeyen (zaten doğru) | 936 |
| Belirsiz kalan (kontrol listesi) | 81 |
| Doğrulanamadığı için boşaltılan eski ilçe | 72 |
| Yinelenen kayıt (aynı il + ad) | 4 grup |
| Olası yinelenen (farklı ad, aynı telefon, <300 m) | 19 çift |
| Konum uyarısı (koordinat kontrol edilmeli) | 48 |

## Belirsiz kalan kayıtlar (kontrol listesi)

İlçe alanı boş bırakıldı; tesis il genelinde ("Tüm ilçeler") listelenir. Doğrulandıktan sonra `tesisler_adres.json` içindeki `ilce` alanına standart ilçe adı yazılmalı.

| İl | Tesis | Önceki kayıt | Bulgular |
|---|---|---|---|
| Adana | Adana Nezihe Yalvaç Uygulama Oteli | Çukurova | konum Çukurova; adres Seyhan |
| Adana | DSİ Yeni Baraj Misafirhanesi | Çukurova | konum Sarıçam; adres Ceyhan |
| Ağrı | Ağrı Öğretmenevi | Ağrı Merkez | konum Merkez; adres Diyadin |
| Aksaray | Aksaray Karayolları 3. Bölge Müdürlüğü Misafirhanesi | Aksaray Merkez | koordinat Kilis/Musabeyli içinde; eşlenik adres Merkez |
| Ankara | Ankara Hacı Bayram Veli Üniversitesi Sosyal Tesisleri | Yenimahalle | konum Yenimahalle; adres Çankaya |
| Ankara | Çalışma Ve Sosyal Güvenlik Bakanlığı Misafirhanesi | Çankaya | konum Çankaya; adres Yenimahalle |
| Ankara | Deçev Misafirhanei | Çankaya | konum Keçiören; eşlenik adres Çankaya |
| Ankara | PTT Misafirhanesi | Altındağ | konum Altındağ; adres Yenimahalle |
| Ankara | T.C. Karayolları Genel Müdürlüğü Misafirhanesi | Yenimahalle | konum Yenimahalle; adres Çankaya |
| Antalya | Antalya MEB Uygulama Oteli | Muratpaşa | konum Alanya; adres Konyaaltı |
| Antalya | İller Bankası A.Ş. Antalya Bölge Müdürlüğü Misafirhanesi | — | konum Muratpaşa; adres Kepez |
| Antalya | TRT Lara Kampı | Aksu | konum Muratpaşa; adreste birden çok ilçe |
| Bolu | Bolu DSİ Eğitim ve Dinlenme Tesisleri | Bolu Merkez | konum Merkez; adres Mudurnu |
| Bursa | Bursa Hakim Evi | Osmangazi | konum Osmangazi; adres Yıldırım |
| Çanakkale | Çanakkale Maliye Güzelyalı Eğitim ve Dinlenme Tesisileri Misafirhanesi | Çanakkale Merkez | koordinat ilçe sınırına düşmüyor; eşlenik adres Merkez |
| Çanakkale | Çanakkale Subay Orduevi | Çanakkale Merkez | koordinat ilçe sınırına düşmüyor; eşlenik adres Merkez |
| Çanakkale | Çanakkale Yahya Çavuş Orman Kampı | Çanakkale Merkez | koordinat ilçe sınırına düşmüyor; eşlenik adres Merkez |
| Denizli | DSİ Denizli Misafirhanesi | Denizli Merkezefendi | konum Merkezefendi; adres Sarayköy |
| Diyarbakır | GAP Uluslararası Tarımsal Araştırma Ve Eğitim Merkezi Konukevi | Sur | konum Sur; adres Silvan |
| Elazığ | Elazığ Karayolları 8. Bölge Dinlenme Tesisi ve Konukevi | — | konum Merkez (koordinat başka tesisle ortak); adreste ilçe yok |
| Elazığ | Elazığ Meteoroloji 13. Bölge Md.lüğü Misafirhanesi | — | konum Merkez (koordinat başka tesisle ortak); adreste ilçe yok |
| Elazığ | Elazığ Polisevi | Elazığ Merkez | konum Merkez; adres Keban |
| Eskişehir | Eskişehir Astsubay Orduevi | — | konum Tepebaşı (koordinat başka tesisle ortak); adreste ilçe yok |
| Gaziantep | Gaziantep Büyükşehir Belediyesi Gazi Konukevi | Şahinbey | konum Şehitkamil; eşlenik adres Şahinbey |
| Hatay | Gülcihan Yerel Özel Eğitim Merkezi Komutanlığı | Arsuz | koordinat ilçe sınırına düşmüyor; adreste ilçe yok |
| Hatay | Hatay Karayolları Misafirhanesi | — | konum Arsuz; adres Antakya |
| Hatay | Hatay Uluçınar Özel Eğitim Merkezi K.lığı | — | konum Arsuz; adres İskenderun |
| Hatay | Hatay Valiliği İskenderun Konuk Evi | İskenderun | koordinat ilçe sınırına düşmüyor; adreste ilçe yok; adda İskenderun |
| Hatay | İskenderun Deniz Uluçınar Öz. Eğitim Merkezi | Arsuz | konum Arsuz; adreste ilçe yok; adda İskenderun |
| Hatay | İskenderun Orduevi | İskenderun | koordinat ilçe sınırına düşmüyor; adres Antakya; adda İskenderun |
| Hatay | Maliye Bakanlığı Hatay İli Defterdarlığı Dinlenme Tesisi | Arsuz | koordinat ilçe sınırına düşmüyor; adreste ilçe yok |
| Isparta | Isparta DSİ Misafirhanesi | Merkez | konum Merkez; adres Eğirdir |
| Isparta | Isparta İl Özel İdaresi Sosyal Tesisleri | Merkez | konum Merkez; adres Eğirdir |
| İstanbul | Adile Mermerci Uygulama Oteli | Zeytinburnu | konum Gaziosmanpaşa; eşlenik adres Zeytinburnu |
| İstanbul | Beylerbeyi Askeri Gazino Müdürlüğü | Üsküdar | koordinat ilçe sınırına düşmüyor; eşlenik adres Üsküdar |
| İstanbul | Beylerbeyi Sabancı Polisevi Sosyal Tesisi | Üsküdar | koordinat ilçe sınırına düşmüyor; eşlenik adres Üsküdar |
| İstanbul | Hazine ve Maliye Bakanlığı Beyazıt Eğitim Tesisi ve Konukevi | Fatih | koordinat ilçe sınırına düşmüyor; eşlenik adres Fatih |
| İstanbul | İstanbul Defterdarlığı Misafirhanesi | Fatih | koordinat ilçe sınırına düşmüyor; eşlenik adres Fatih |
| İstanbul | İstanbul Karayolları 1. Bölge Müdürlüğü Sosyal Tesisleri | Kağıthane | konum Sarıyer; eşlenik adres Kağıthane |
| İstanbul | İstanbul Makina Kimya Endüstrisi Sosyal Tesisleri | Beyoğlu | konum Kadıköy; eşlenik adres Beyoğlu |
| İstanbul | Selimiye Astsubay Orduevi | Sarıyer | konum Üsküdar; eşlenik adres Sarıyer |
| İstanbul | Yıldız Teknik Üniversitesi Misafirhanesi | Esenler | konum Esenler; adres Beşiktaş |
| İzmir | DHMİ Havacılık Akademisi İzmir Eğitim Tesisi | — | konum Gaziemir; adreste birden çok ilçe |
| İzmir | Hava Eğitim Komutanlığı Gazinosu | Konak | koordinat ilçe sınırına düşmüyor; eşlenik adres Konak |
| İzmir | İzmir Adalet Sarayı Sosyal Tesisleri | Bayraklı | konum Konak; adres Karşıyaka |
| İzmir | İzmir Polis Evi Düğün Salonu | Konak | koordinat ilçe sınırına düşmüyor; eşlenik adres Konak |
| İzmir | Yolluca Denizciler Kampı | Urla | koordinat ilçe sınırına düşmüyor; eşlenik adres Urla |
| Karaman | Karaman İl Özel İdaresi Merkez | Karaman Merkez | koordinat Kilis/Musabeyli içinde; eşlenik adres Merkez |
| Kastamonu | Kastamonu Orman Bölge Müdürlüğü Misafirhanesi | Merkez | konum Merkez; eşlenik adres Tosya |
| Kıbrıs | Gazimağusa Orduevi | Kuzey | KKTC sınır verisi yok; adreste ilçe yok; adda Gazimağusa |
| Kıbrıs | Girne Yalı Orduevi | Kyrenia | KKTC sınır verisi yok; eşlenik adres Girne; adda Girne |
| Kıbrıs | Güven Orduevi | Gazimağusa | KKTC sınır verisi yok; eşlenik adres Gazimağusa |
| Kırklareli | Kırklareli Öğretmenevi ve ASO | Kırklareli Merkez | konum Kofçaz; eşlenik adres Merkez |
| Kocaeli | Karamürselbey Eğitim Merkezi Komutanlığı | Altınova | koordinat Yalova/Altınova içinde; adreste ilçe yok |
| Kocaeli | Kocaeli Defterdarlığı Maliye Misafirhanesi | İzmit | konum İzmit; adres Körfez |
| Konya | Konya Uygulama Oteli | Selçuklu | konum Karatay; eşlenik adres Selçuklu |
| Manisa | Manisa Jandarma Sosyal Tesisleri | Şehzadeler | konum Şehzadeler; adres Alaşehir |
| Manisa | Yunusemre Belediyesi Misafirhanesi | Yunusemre | koordinat Kilis/Musabeyli içinde; eşlenik adres Yunusemre; adda Yunusemre |
| Mardin | Mardin Kışla Gazino Müdürlüğü | Mardin Merkez | konum Artuklu; adres Nusaybin |
| Mersin | Mersin Defterdarlığı Maliye Misafirhanesi | Akdeniz | konum Silifke; adres Yenişehir |
| Mersin | Türkiye Yol İş Sendikası Eğitim Ve Dinlenme Tesisleri | Silifke | konum Silifke; adres Erdemli |
| Muğla | Marmaris Aksaz Deniz Askeri Gazino Müdürlüğü | Marmaris | konum Köyceğiz; eşlenik adres Marmaris; adda Marmaris |
| Muğla | Muğla Milas Bodrum Havalimanı Misafirhanesi | — | konum Milas; adreste birden çok ilçe |
| Sakarya | Kefken Özel Eğitim Merkezi K.lığı | Kandıra | koordinat Kocaeli/Kandıra içinde; adreste ilçe yok |
| Sakarya | Sakarya Tarım Orman Misafirhanesi | Adapazarı | konum Adapazarı; adres Arifiye |
| Samsun | Samsun Kurupelit Eğitim Merkezi | Atakum | koordinat ilçe sınırına düşmüyor; eşlenik adres Atakum |
| Samsun | Samsun Tarım Misafirhanesi | İlkadım | konum İlkadım; adres Atakum |
| Şanlıurfa | Şanlıurfa Jandarma Sosyal Tesisleri | Karaköprü | konum Haliliye; adres Karaköprü |
| Sinop | Ahmet Muhip Dıranas Uygulama Oteli | Sinop Merkez | koordinat ilçe sınırına düşmüyor; eşlenik adres Merkez |
| Tokat | Tokat Polisevi | Tokat Merkez | konum Merkez; adres Niksar |
| Trabzon | Teiaş 14. Bölge Müdürlüğü Misafirevi | Ortahisar | konum Ortahisar; adres Arsin |
| Trabzon | Trabzon Defterdarlığı Yıldızlı Misafirhane Ve Eğitim Tesisi | Akçaabat | koordinat ilçe sınırına düşmüyor; eşlenik adres Akçaabat |
| Trabzon | Trabzon KTÜ Sahil Tesisleri | Trabzon Merkez | koordinat ilçe sınırına düşmüyor; adreste ilçe yok |
| Trabzon | Trabzon Öğretmenevi | Ortahisar | koordinat Ordu/İkizce içinde; eşlenik adres Ortahisar |
| Trabzon | TRT Trabzon Misafirhanesi | Akçaabat | koordinat ilçe sınırına düşmüyor; eşlenik adres Akçaabat |
| Van | Van İl Tarım Misafirhanesi | Van Merkez | konum Tuşba; adres Erciş |
| Van | Van Karayolları 11. Bölge | — | konum Tuşba; adres Edremit |
| Van | Van YYÜ Konuk Evi Uygulama Oteli | Tuşba | konum Tuşba; adreste birden çok ilçe |
| Yalova | Yalova Dsi Yazlık Dinlenme Tesisleri | Yalova Merkez | koordinat Kilis/Musabeyli içinde; eşlenik adres Merkez |
| Yalova | Yalova Zirai Mücadele Yazlık Dinlenme Tesisleri | Yalova Merkez | koordinat ilçe sınırına düşmüyor; eşlenik adres Merkez |
| Yozgat | DSİ Yozgat Misafirhanesi | Yozgat Merkez | koordinat Kilis/Musabeyli içinde; eşlenik adres Merkez |

## Düzeltilen ilçe bilgileri (86)

| İl | Tesis | Önce | Sonra | Kanıt |
|---|---|---|---|---|
| Adana | Adana Adliyesi Göltepe Eğitim ve Sosyal Tesisi | Çukurova | Sarıçam | adres (konum sınıra 1.8 km) |
| Adana | Adana Saimbeyli Öğretmenevi Ve Akşam Sanat Okulu | Feke | Saimbeyli | adres+ad |
| Adana | Adana Seyhan İlçe Tarım ve Orman Müdürlüğü Misafirhanesi | Seyhan | Yüreğir | adres (konum sınıra 0.2 km) |
| Afyonkarahisar | Emirdağ Öğretmen Evi ve Akşam Sanat Okulu | Afyonkarahisar Merkez | Emirdağ | konum+adres |
| Ağrı | Doğubayazıt Askeri Gazino Müdürlüğü | Ağrı Merkez | Doğubayazıt | konum+ad |
| Ağrı | Eleşkirt Askeri Gazino Müdürlüğü | Ağrı Merkez | Eleşkirt | konum+ad |
| Ağrı | Patnos Jandarma Kışlası Gazino Müdürlüğü | Ağrı Merkez | Patnos | konum+ad |
| Ağrı | Taşlıçay Öğretmenevi | Ağrı Merkez | Taşlıçay | adres+ad |
| Amasya | Amasya Uygulama Oteli | Amasya District | Merkez | konum+adres |
| Ankara | Ankara Vilayet Evleri | Çankaya | Gölbaşı | konum+adres |
| Ankara | Öğretmenevi – Başkent | Yenimahalle | Çankaya | adres (konum sınıra 0.3 km) |
| Ankara | Orman Genel Müdürlüğü Misafirhanesi | Yenimahalle | Çankaya | adres (konum sınıra 0.2 km) |
| Ardahan | Çıldır Kışla Gazino Müdürlüğü | Kars Merkez | Çıldır | konum+ad |
| Aydın | Aydın Polisevi | Aydın Merkez | Efeler | konum |
| Aydın | Selçuk Şehit Er Mehmet Yüce İMKB Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | Selçuk | Kuşadası | adres |
| Balıkesir | Balıkesir Maliye Defterdarlık Misafirhanesi | Balıkesir Merkez | Karesi | konum |
| Balıkesir | Balıkesir Polisevi Merkez | Merkez | Karesi | konum |
| Balıkesir | Çevre Ve Şehircilik Balıkesir İl Müdürlüğü Misafirhanesi | Balıkesir Merkez | Karesi | konum |
| Balıkesir | DSİ 25. Bölge Müdürlüğü Çayırhisar Misafirhanesi ve Eğitim Tesisi | Balıkesir Merkez | Karesi | konum |
| Balıkesir | Edremit Maliye Defterdarlık Misafirhanesi | Balıkesir Merkez | Edremit | adres+ad |
| Bitlis | Bitlis Eren Üniversitesi Yahya Eren Konukevi | Koruk/merkez | Merkez | konum+adres |
| Denizli | Denizli Polisevi | Denizli Merkez | Pamukkale | konum |
| Erzincan | Çayırlı Öğretmenevi | Erzincan Merkez | Çayırlı | adres+ad |
| Eskişehir | Eskişehir Büyükşehir Belediyesi Porsuk Konuk Evi | Tepebaşı | Odunpazarı | adres (konum sınıra 0.0 km) |
| Giresun | Giresun Polisevi | Teyyaredüzü | Merkez | konum |
| Hakkari | Hakkari Üniversitesi Rektörlük Hizmet Binası ve Sosyal Tesisleri | Biçer | Merkez | konum+adres |
| Iğdır | Jandarma Sosyal Tesisleri | Jandarma Sosyal | Merkez | konum |
| Isparta | PTT Isparta Baş müdürlüğü Misafirhane | PTT Isparta | Merkez | konum |
| Isparta | Süleyman Demirel Üniversitesi Konukevi Uygulama Oteli Misafirhanesi | Süleyman Demirel | Merkez | konum |
| İstanbul | Bakırköy Başöğretmen Lokali ve Öğretmenevi | Küçükçekmece | Bakırköy | konum+adres |
| İstanbul | Kadıköy(Zübeyde hanım) Vali Erol Çakır Öğretmenevi | Ataşehir | Kadıköy | adres (konum sınıra 1.2 km) |
| İstanbul | Merter Polisevi (PEKOM) | Zeytinburnu | Güngören | adres (konum sınıra 0.4 km) |
| İstanbul | Yurtkurt Ortaköy Misafirhanesi | Beşiktaş | Ümraniye | konum+adres |
| İzmir | İzmir DEU Sosyal Tesisleri | Konak | Buca | adres |
| İzmir | İzmir Karayolları Sosyal Tesisleri | Güzelbahçe | Bornova | konum+adres |
| Kahramanmaraş | Kahramanmaraş Orduevi | Kahramanmaraş Merkez | Dulkadiroğlu | konum |
| Kahramanmaraş | Kahramanmaraş Sütçü İmam Üniversitesi Uygulama Oteli | Kahramanmaraş Merkez | Dulkadiroğlu | konum+adres |
| Karaman | Başyayla Öğretmenevi | Karaman Merkez | Başyayla | konum+ad |
| Kayseri | Kayseri Öğretmenevi | Talas | Kocasinan | konum+adres |
| Kıbrıs | Barış Plajı Kışla Gazino Md.lüğü | Çatalköy | Girne | adres |
| Kıbrıs | Çamlıbel Kışla Gazino Md.lüğü | KKTC | Girne | adres |
| Kıbrıs | Değirmenlik Kışla Gazino Md.lüğü | KKTC | Lefkoşa | adres |
| Kıbrıs | Güzelyurt Askeri Gazino Md.lüğü | KKTC | Güzelyurt | adres+ad |
| Kıbrıs | Kırklar Askeri Gazino Md.lüğü | KKTC | Lefkoşa | adres |
| Kıbrıs | Ortadoğu Teknik Üniversitesi Kuzey Kıbrıs Kampüsü Konukevi | Kalkanlı | Güzelyurt | adres |
| Kıbrıs | Ortaköy Askeri Gazino Md.lüğü | Ortaköy | Lefkoşa | adres |
| Kıbrıs | Paşaköy Kışla Gazino Md.lüğü | Kuzey | Gazimağusa | adres |
| Kıbrıs | Ulukışla Kışla Gazino Md.lüğü | Ulukışla | Gazimağusa | adres |
| Kocaeli | Dsi 15. Şube Müdürlüğü İzmit | İzmit | Başiskele | adres (konum sınıra 0.4 km) |
| Kocaeli | İzmit OGM Kavakçılık Sosyal Tesis ve Misafirhanesi | Başiskele | İzmit | adres (konum sınıra 0.0 km) |
| Konya | Seydişehir Öğretmenevi | Seydişlehir | Seydişehir | konum+adres |
| Malatya | İnönü Üniversitesi Hastahane Oteli | Malatya Merkez | Battalgazi | konum |
| Malatya | Malatya Çevre ve Şehircilik İl Müdürlüğü Misafirhanesi | Malatya Merkez | Battalgazi | konum+adres |
| Malatya | Malatya Orduevi | Malatya Merkez | Battalgazi | konum+adres |
| Malatya | Malatya PTT Misafirhanesi | Yeşilyurt | Battalgazi | adres (konum sınıra 0.4 km) |
| Malatya | Malatya TCDD Misafirhanesi | Malatya Merkez | Yeşilyurt | konum |
| Manisa | Manisa Polisevi | Manisa Merkez | Yunusemre | konum+adres |
| Mardin | Mardin Polisevi | Mardin Merkez | Artuklu | konum+eşlenik adres |
| Mardin | Şatana Konağı (Maü Uygulama Oteli) | Mardin Merkez | Artuklu | konum |
| Mersin | Mersin Karayolları Merkez Bölge Misafirhanesi | Akdeniz | Toroslar | konum+adres |
| Muğla | Muğla Jandarma Misafirhanesi | Muğla Merkez | Menteşe | konum+adres |
| Muğla | Muğla Orman Müdürlüğü Misafirhane | Muğla Merkez | Menteşe | konum |
| Muğla | Muğla Sıtkı Koçman Üniversitesi Sosyal Tesisler Konuk Evi | Muğla Merkez | Menteşe | konum |
| Ordu | Ordu Merkez Öğretmenevi ve Akşam Sanat Okulu | Ordu Merkez | Altınordu | konum |
| Ordu | Ordu Orduevi Askeri Gazino | Ordu Merkez | Altınordu | konum |
| Sakarya | Sakarya TUVASAŞ Misafirhanesi | Serdivan | Adapazarı | adres (konum sınıra 0.4 km) |
| Şanlıurfa | HARRAN ÜNİVERSİTESİ URFA EVİ UYGULAMA OTELİ | Şanlıurfa Merkez | Eyyübiye | konum+eşlenik adres |
| Şanlıurfa | Şanlıurfa DSİ Misafirhanesi | Şanlıurfa Merkez | Haliliye | konum |
| Şanlıurfa | Şanlıurfa Kışla Gazinosu | Şanlıurfa Merkez | Haliliye | konum |
| Tekirdağ | Tekirdağ DSİ Misafirhanesi | Tekirdağ Merkez | Süleymanpaşa | konum |
| Tekirdağ | Tekirdağ Karayolları 18. Şube Şefliği | Tekirdağ Merkez | Süleymanpaşa | konum+adres |
| Tekirdağ | Tekirdağ Kumbağ Polis Kampı | Tekirdağ Merkez | Süleymanpaşa | konum |
| Tekirdağ | Tekirdağ Polisevi | Tekirdağ Merkez | Süleymanpaşa | konum |
| Trabzon | Akçaabat Anadolu Otelcilik ve Turizm Meslek Lisesi Uygulama Oteli | Söğütlü | Akçaabat | konum+adres |
| Trabzon | Çevre ve Şehircilik Bakanlığı Trabzon İl Müdürlüğü Sosyal Tesisleri | Trabzon Merkez | Ortahisar | konum |
| Trabzon | KTÜ Koru Tesisleri Üniversite | Trabzon Merkez | Ortahisar | konum |
| Trabzon | Trabzon Dsi Misafirhanesi | Trabzon Merkez | Ortahisar | konum |
| Trabzon | Trabzon Gençlik ve Spor İl Müdürlüğü Misafirhanesi | Trabzon Merkez | Ortahisar | konum+adres |
| Trabzon | Trabzon Karayolları Sosyal Tesisleri | Trabzon Merkez | Ortahisar | konum |
| Trabzon | Yol-İş Sendikası Trabzon Misafirhanesi | Trabzon Merkez | Ortahisar | konum |
| Van | Van Orduevi | Van Merkez | İpekyolu | konum |
| Van | Van PTT Misafirhane | Van Merkez | Tuşba | konum |
| Van | Van Tcdd Misafirhane | Van Merkez | Tuşba | konum |
| Van | Van Yol-İş Sendikası Misafirhanesi | Van Merkez | İpekyolu | konum |
| Zonguldak | Zonguldak Öğretmenevi İncivez | Zonguldak Merkez | Kozlu | konum+adres |
| Zonguldak | Zonguldak TTK Misafirhanesi | Zonguldak Merkez | Çaycuma | konum+adres |

## Standartlaştırılan kayıtlar (286)

Aynı ilçenin farklı yazımları resmi ada çevrildi (en sık görülenler):

- Kastamonu Merkez → Merkez: 11
- Sivas Merkez → Merkez: 11
- Sinop Merkez → Merkez: 10
- Çanakkale Merkez → Merkez: 9
- Kars Merkez → Merkez: 9
- Tokat Merkez → Merkez: 9
- Amasya Merkez → Merkez: 8
- Bartın Merkez → Merkez: 8
- Kütahya Merkez → Merkez: 8
- Batman Merkez → Merkez: 7
- Bolu Merkez → Merkez: 7
- Edirne Merkez → Merkez: 7
- Kırıkkale Merkez → Merkez: 7
- Rize Merkez → Merkez: 7
- Yozgat Merkez → Merkez: 7
- Afyonkarahisar Merkez → Merkez: 6
- Bayburt Merkez → Merkez: 6
- Burdur Merkez → Merkez: 6
- Elazığ Merkez → Merkez: 6
- Erzincan Merkez → Merkez: 6
- Muş Merkez → Merkez: 6
- Niğde Merkez → Merkez: 6
- Siirt Merkez → Merkez: 6
- Tunceli Merkez → Merkez: 6
- Uşak Merkez → Merkez: 6
- Artvin Merkez → Merkez: 5
- Bingöl → Merkez: 5
- Çankırı Merkez → Merkez: 5
- Çorum Merkez → Merkez: 5
- Düzce → Merkez: 5
- Giresun Merkez → Merkez: 5
- Karaman Merkez → Merkez: 5
- Kırklareli Merkez → Merkez: 5
- Kırşehir Merkez → Merkez: 5
- Nevşehir Merkez → Merkez: 5
- Osmaniye Merkez → Merkez: 5
- Zonguldak Merkez → Merkez: 5
- Ağrı Merkez → Merkez: 4
- Aksaray Merkez → Merkez: 4
- Ardahan Merkez → Merkez: 4
- … ve 11 farklı yazım daha

## Tamamlanan ilçe bilgileri (531)

`tesisler_adres.json` içinde kaydı veya ilçesi olmayan tesisler.

| İl | Tesis | Önce | Sonra | Kanıt |
|---|---|---|---|---|
| Adana | 10.Tanker Üs K.lığı Kışla Gazino Md.lüğü | — | Yüreğir | adres (konum sınıra 0.5 km) |
| Adana | Adana İl Sağlık Md.lüğü Misafirhanesi | — | Seyhan | konum+adres |
| Adana | Adana İmamoğlu Öğretmenevi | — | İmamoğlu | konum+adres |
| Adana | Adana Meteoroloji 6. Bölge Müdürlüğü Misafirhanesi | — | Yüreğir | konum+adres |
| Adana | Adana Taşköprü Konukevi | — | Seyhan | konum+adres |
| Adana | Adana TEDAŞ Misafirhanesi | — | Yüreğir | konum+adres |
| Adıyaman | Adıyaman Çelikhan Öğretmenevi | — | Çelikhan | konum+adres |
| Adıyaman | Adıyaman Devlet Su İşleri Misafirhanesi | — | Merkez | konum+adres |
| Adıyaman | Adıyaman Havalimanı Misafirhanesi | — | Merkez | konum |
| Adıyaman | Adıyaman Tut Öğretmenevi | — | Tut | konum+adres |
| Adıyaman | Adıyaman Üniversitesi Turizm Uygulama Oteli | — | Merkez | konum+adres |
| Afyonkarahisar | Afyonkarahisar Emir Murat Özdilek Uygulama Oteli | — | Merkez | konum+adres |
| Afyonkarahisar | Afyonkarahisar Karayolları 31.Şube Şefliği ve Misafirhanesi | — | Merkez | konum+adres |
| Afyonkarahisar | Afyonkarahisar Orman İşletme Misafirhanesi | — | Merkez | konum+adres |
| Afyonkarahisar | Afyonkarahisar Vardiya Yatakhanesi Md.lüğü | — | Merkez | konum+adres |
| Ağrı | Ağrı Ahmed-i Hani Havalimanı Misafirhanesi | — | Merkez | konum |
| Ağrı | Ağrı İbrahim Çeçen Üniversitesi Misafirhanesi | — | Merkez | konum+adres |
| Ağrı | Ağrı TEİAŞ Misafirhanesi | — | Merkez | konum+adres |
| Ağrı | Gökay Askeri Vardiya Yatakhanesi Md.lüğü | — | Doğubayazıt | konum+adres |
| Aksaray | Aksaray İl Jandarma K.lığı Misafirhanesi | — | Merkez | konum+adres |
| Ankara | Ankara 3.Hv.İs.İnş.Tb.K.lığı Vardiya Yatakhanesi Md.lüğü | — | Etimesgut | konum+adres |
| Ankara | Ankara 4.Kolordu K.lığı Kışla Gazino Md.lüğü | — | Mamak | konum+adres |
| Ankara | Ankara Açık Ceza İnfaz Kurumu Adaletevi Misafirhanesi | — | Çankaya | konum+adres |
| Ankara | Ankara Bala Öğretmenevi | — | Bala | konum+adres |
| Ankara | Ankara Bayındır Otel | — | Çankaya | konum+adres |
| Ankara | Ankara Beypazarı Öğretmenevi | — | Beypazarı | konum+adres |
| Ankara | Ankara Dışkapı Uzman Erbaş Misafirhanesi | — | Altındağ | konum+adres |
| Ankara | Ankara Dz.K.K.lığı Kh.Kışla Gazino Md.lüğü | — | Çankaya | konum+adres |
| Ankara | Ankara Gölbaşı Hakimevi | — | Gölbaşı | konum+adres |
| Ankara | Ankara Haymana Öğretmenevi | — | Haymana | konum+adres |
| Ankara | Ankara Jandarma ve Sahil Güvenlik Akademesi Sosyal Tesis Md.lüğü | — | Çankaya | konum+adres |
| Ankara | Ankara Kızılay Uzman Erbaş Misafirhanesi | — | Çankaya | konum+adres |
| Ankara | Ankara Kızılcahamam Hakimevi | — | Kızılcahamam | konum+adres |
| Ankara | Ankara Kızılcahamam Öğretmenevi | — | Kızılcahamam | konum+adres |
| Ankara | Ankara Kr.Hvcl.K.lığı Kışla Gazino Md.lüğü | — | Etimesgut | konum+adres |
| Ankara | Ankara Mürted Hava Meydan K.lığı Kışla Gazino Md.lüğü | — | Kahramankazan | konum+adres |
| Ankara | Ankara Nallıhan Öğretmenevi | — | Nallıhan | adres+ad |
| Ankara | Ankara Polatlı Acıkır Kışla Gazino Md.lüğü | — | Polatlı | konum+adres |
| Ankara | Ankara Polisevi | — | Gölbaşı | konum+adres |
| Ankara | Ankara Sahil Güvenlik K.lığı Misafirhanesi | — | Çankaya | konum+adres |
| Ankara | Ankara Ticaret Bakanlığı Eğitim Merkezi ve Konukevi | — | Akyurt | konum+adres |
| Ankara | Ankara Türk Eğitim-Sen Öğrenci Misafirhanesi | — | Altındağ | konum+adres |
| Ankara | Ankara Türkiye Belediyeler Birliği Konukevi | — | Çankaya | konum |
| Ankara | DHMİ Havacılık Akademisi Ankara Esenboğa Eğitim Tesisi | — | Çubuk | konum |
| Ankara | Kara Kuvvetleri K.lığı Kışla Gazino Md.lüğü | — | Çankaya | konum+adres |
| Ankara | Sıhhıye Orduevi Md.lüğü | — | Çankaya | konum |
| Ankara | Sıhhıye Orduevi Md.lüğü Astsubay Misafirhanesi | — | Çankaya | konum |
| Ankara | TEKSİF EĞİTİM & DİNLENME TESİSİ | — | Çankaya | konum+adres |
| Antalya | Antalya Alanya Belediyesi Sosyal Tesisleri | — | Alanya | konum+adres |
| Antalya | Antalya Alanya Karayolları Misafirhanesi | — | Alanya | konum+adres |
| Antalya | Antalya Alanya Ümit Altay Uygulama Oteli | — | Alanya | konum+adres |
| Antalya | Antalya Havalimanı Misafirhanesi | — | Muratpaşa | konum |
| Antalya | Antalya Hava Meydan K.lığı Vardiya Yatakhanesi Md.lüğü | — | Muratpaşa | konum+adres |
| Antalya | Antalya Jandarma Sosyal Tesis Md.lüğü | — | Muratpaşa | adres (konum sınıra 0.0 km) |
| Antalya | Antalya Kaş Meteoroloji Müdürlüğü Misafirhanesi | — | Kaş | konum+adres |
| Antalya | Antalya Kaş Uygulama Oteli | — | Kaş | konum+adres |
| Antalya | Antalya Kemer Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | — | Kemer | konum+adres |
| Antalya | Antalya Lara Polisevi İktisadi İşletmesi | — | Muratpaşa | konum+adres |
| Antalya | Antalya Manavgat Maliye Misafirhanesi | — | Manavgat | konum+adres |
| Antalya | Antalya Manavgat Uygulama Oteli | — | Manavgat | konum+adres |
| Antalya | Antalya Orman Müdürlüğü Misafirhanesi | — | Muratpaşa | konum+adres |
| Antalya | Antalya Sahil Güvenlik Okul K.lığı Kışla Gazino Md.lüğü | — | Kepez | konum+adres |
| Antalya | Kepez Belediyesi (Hasta) Konuk Evi | — | Kepez | konum+eşlenik adres |
| Antalya | Sahil Güvenlik Antalya Grup K.lığı Vardiya Yatakhanesi Md.lüğü | — | Konyaaltı | konum+adres |
| Ardahan | Ardahan Tarım Orman Bakanlığı Arıcılık Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Artvin | Artvin Orduevi Md.lüğü | — | Merkez | konum+adres |
| Artvin | Artvin Orman Bölge Müdürlüğü Misafirhanesi | — | Merkez | konum+adres |
| Artvin | Artvin Şavşat Öğretmenevi | — | Şavşat | konum+adres |
| Aydın | Aydın Demiryol-İş Sendikası Didim Eğitim ve Dinlenme Tesisleri | — | Didim | konum+adres |
| Aydın | Aydın İLKSAN Didim Sosyal Tesisi | — | Didim | konum+adres |
| Aydın | Aydın Kuşadası Güvercinada Uygulama Oteli | — | Kuşadası | konum+adres |
| Aydın | Aydın Söke Zirai Üretim İşletmesi Tarımsal Yayım ve Hizmetiçi Eğitim Merkezi Md.lüğü Misafirhanesi | — | Söke | adres+ad |
| Aydın | Aydın TKİ Didim Eğitim ve Dinlenme Tesisi | — | Didim | konum+adres |
| Aydın | Aydın TŞOF Didim Eğitim ve Dinlenme Tesisi | — | Didim | konum+adres |
| Balıkesir | 6.Ana Jet Üs K.lığı Kışla Gazino Md.lüğü | — | Bandırma | konum+adres |
| Balıkesir | Balıkesir 9.Ana Jet Üs K.lığı Kışla Gazino Md.lüğü | — | Karesi | konum |
| Balıkesir | Balıkesir Akçay Polisevi | — | Edremit | konum+adres |
| Balıkesir | Balıkesir Ayvalık Jandarma Sosyal Tesisleri | — | Ayvalık | konum+adres |
| Balıkesir | Balıkesir Ayvalık Vilayetler Evi (VE Hotels) | — | Ayvalık | konum+adres |
| Balıkesir | Balıkesir Bakım Okulu ve Eğitim Merkezi K.lığı Kışla Gazino Md.lüğü | — | Altıeylül | konum+adres |
| Balıkesir | Balıkesir Cunda Uygulama Oteli | — | Ayvalık | konum+adres |
| Balıkesir | Balıkesir Gazi Mustafa Kemal Turizm Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | — | Karesi | konum+adres |
| Balıkesir | Balıkesir İl Özel İdaresi Sosyal Tesisleri | — | Karesi | konum |
| Balıkesir | Balıkesir Koca Seyit Havalimanı Misafirhanesi | — | Edremit | adres (konum sınıra 0.0 km) |
| Balıkesir | Balıkesir Merkez Havalimanı Misafirhanesi | — | Altıeylül | konum |
| Balıkesir | Balıkesir PTT Misafirhanesi | — | Altıeylül | konum+adres |
| Bartın | Bartın Kurucaşile PTT Misafirhanesi | — | Kurucaşile | konum+adres |
| Bartın | Bartın Ulus Kumluca Belediye Oteli | — | Ulus | konum+adres |
| Bartın | Dz.K.Amasra Vardiya Yatakhanesi | — | Amasra | konum+adres |
| Batman | Batman Belediyesi Konukevi | — | Merkez | konum+adres |
| Batman | Batman Defterdalığı Misafirhanesi | — | Merkez | konum+adres |
| Batman | Batman Üniversitesi Hasankeyf Uygulama Oteli | — | Hasankeyf | konum+adres |
| Bayburt | Bayburt Baksı Müzesi Konukevi | — | Merkez | konum |
| Bayburt | Bayburt DSİ 225.Şube Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Bayburt | Bayburt İl Sağlık Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Bayburt | Bayburt Loru Han (Kenan Yavuz Etnografya Müzesi Konukevi) | — | Demirözü | konum+adres |
| Bayburt | Tedaş Bayburt Misafirhanesi | — | Merkez | konum+adres |
| Bilecik | Bilecik Söğüt Öğretmenevi | — | Söğüt | konum+adres |
| Bilecik | Söğüt Jandarma Sosyal Tesis Md.lüğü | — | Söğüt | konum+adres |
| Bingöl | Bingöl Adaklı Öğretmenevi | — | Adaklı | konum+adres |
| Bingöl | Bingöl Çevre ve Şehircilik İl Müdürlüğü Misafirhanesi | — | Merkez | konum+adres |
| Bingöl | Bingöl Havalimanı Misafirhanesi | — | Merkez | konum |
| Bingöl | Bingöl Karlıova Öğretmenevi | — | Karlıova | konum+ad |
| Bingöl | Bingöl Kışla Gazino Md.lüğü | — | Merkez | konum+adres |
| Bingöl | Kiğı Jandarma Sosyal Tesis Md.lüğü | — | Kiğı | konum+adres |
| Bitlis | Bitlis DSİ Misafirhanesi | — | Merkez | konum+adres |
| Bitlis | Bitlis İl Sağlık Müdürlüğü Misafirhanesi | — | Merkez | konum+adres |
| Bitlis | Bitlis Tatvan Karayolları Misafirhanesi | — | Tatvan | konum+adres |
| Bolu | Bolu Abant İzzet Baysal Üniversistesi Sosyal Tesisleri | — | Merkez | konum+adres |
| Bolu | Bolu Karayolları 41. Şube Şefliği Misafirhanesi | — | Merkez | konum+adres |
| Bursa | Bursa Çekirge Polis Eğitim ve Dinlenme Tesisi | — | Osmangazi | konum+adres |
| Bursa | Bursa Dini İhtisas Merkezi Md.lüğü Misafirhanesi ve TDV Sosyal Tesisleri | — | Nilüfer | konum+adres |
| Bursa | Bursa Gemlik Daniş Ekim Öğretmenevi | — | Gemlik | konum+adres |
| Bursa | Bursa Mudanya Öğretmenevi | — | Mudanya | konum+adres |
| Bursa | Bursa Orhangazi Öğretmenevi | — | Orhangazi | konum+adres |
| Bursa | Bursa PTT Misafirhanesi | — | Osmangazi | konum+adres |
| Bursa | Bursa Şehit Erol Olçok Turizm Mesleki ve Teknik Anadolu Lisesi Şehit Abdullah Tayyip Olçok Uygulama Oteli | — | Osmangazi | konum+adres |
| Bursa | Bursa SGK İl Müdürlüğü Misafirhanesi | — | Osmangazi | konum+adres |
| Bursa | Bursa Tapu Kadastro Vakfı Misafirhanesi | — | Osmangazi | konum+adres |
| Bursa | Bursa TEİAŞ 2.Bölge Md.lüğü Misafirhanesi | — | Nilüfer | konum+adres |
| Bursa | Bursa Ziraat Bankası Misafirhanesi | — | Osmangazi | konum+adres |
| Bursa | İstanbul Teknik Üniversitesi Bursa Konukevi | — | Nilüfer | konum+adres |
| Bursa | Uludağ Jandarma Kış Eğitim Merkezi K.lığı | — | Osmangazi | konum+adres |
| Çanakkale | Çanakkale Adalet Bakanlığı Gökçeada Kampı | — | Gökçeada | konum+adres |
| Çanakkale | Çanakkale Askeri Gazino Md.lüğü Barbaros Sosyal Tesisleri | — | Eceabat | konum+adres |
| Çanakkale | Çanakkale Çevre ve Şehircilik İl Müdürlüğü Misafirhanesi | — | Merkez | konum+adres |
| Çanakkale | Çanakkale Deniz Hava Üs K.lığı Kışla Gazino Md.lüğü | — | Merkez | konum+adres |
| Çanakkale | Çanakkale Gelibolu Karayolları Misafirhanesi | — | Gelibolu | konum+adres |
| Çanakkale | Çanakkale Gökçeada Öğretmenevi | — | Gökçeada | konum+adres |
| Çanakkale | Çanakkale Jandarma Sosyal Tesis Md.lüğü | — | Merkez | konum+adres |
| Çanakkale | Çanakkale Karayolları 142.Şube Şefliği Misafirhanesi | — | Merkez | konum+adres |
| Çanakkale | Çanakkale Şehit Pilot Oktay Güngördü Vardiya Yatakhanesi Md.lüğü | — | Merkez | konum+adres |
| Çanakkale | Çanakkale TEİAŞ İletim, İşletme ve Bakım Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Çanakkale | Gökçeada Askeri Gazino Md.lüğü | — | Gökçeada | konum+adres |
| Çankırı | Çankırı Belediyesi Sosyal Tesisi | — | Merkez | konum+adres |
| Çankırı | Çankırı Ilgaz Kış Sporları Eğitim Merkezi | — | Ilgaz | adres+ad |
| Çankırı | Çankırı İl Özel İdaresi Misafirhanesi | — | Merkez | konum |
| Çankırı | Çankırı Kızılırmak Öğretmenevi | — | Kızılırmak | konum+adres |
| Çorum | Çorum Alaca Öğretmenevi | — | Alaca | konum+adres |
| Çorum | Çorum Bayat Öğretmenevi | — | Bayat | konum+adres |
| Çorum | Çorum Belediyesi Refakatçi Misafirhanesi | — | Merkez | konum+adres |
| Çorum | Çorum Karayolları 73.Şube Misafirhanesi | — | Merkez | konum+adres |
| Çorum | Çorum Polisevi | — | Merkez | konum+adres |
| Denizli | Denizli Askeri Gazinosu | — | Merkezefendi | adres (konum sınıra 0.1 km) |
| Denizli | Denizli Çardak Havalimanı Misafirhanesi | — | Çardak | konum+adres |
| Denizli | Denizli İl Sağlık Md.lüğü Misafirhanesi | — | Merkezefendi | konum+adres |
| Denizli | Denizli Karayolları 27.Şube Şefliği Misafirhanesi | — | Pamukkale | konum+adres |
| Denizli | Denizli Kışla Gazino Md.lüğü | — | Pamukkale | konum+adres |
| Denizli | Denizli Orman Bölge Md.lüğü Misafirhanesi | — | Pamukkale | konum+adres |
| Denizli | Denizli Pamukkale Üniversitesi Sosyal Tesisleri ve Konukevi | — | Pamukkale | konum+adres |
| Denizli | Denizli TEİAŞ 21.İletim Tesis ve İşletme Grup Md.lüğü Misafirhanesi | — | Merkezefendi | konum+adres |
| Denizli | Türkiye Diyanet Vakfı Denizli Konukevi | — | Merkezefendi | konum+adres |
| Diyarbakır | Diyarbakır 52.Bakım Fabrika Md.üğü Vardiya Yatakhanesi | — | Kayapınar | konum+adres |
| Diyarbakır | Diyarbakır 8.Ana Jet Üs K.lığı Kışla Gazino Md.lüğü | — | Bağlar | konum+adres |
| Diyarbakır | Diyarbakır Açık Ceza İnfaz Kurumu Misafirhanesi | — | Kayapınar | adres (konum sınıra 0.1 km) |
| Diyarbakır | Diyarbakır Bilgekışla Kışla Gazino Md.lüğü | — | Kayapınar | konum+adres |
| Diyarbakır | Diyarbakır Büyükşehir Belediyesi Kız Öğrenci Misafirhanesi | — | Yenişehir | konum+adres |
| Diyarbakır | Diyarbakır Çevre ve Şehircilik İl Md.lüğü Misafirhanesi | — | Bağlar | konum+adres |
| Diyarbakır | Diyarbakır Eğil Öğretmenevi | — | Eğil | konum+adres |
| Diyarbakır | Diyarbakır Gümrük Md.lüğü Misafirhanesi | — | Kayapınar | konum+adres |
| Diyarbakır | Diyarbakır Hakimevi | — | Sur | konum+adres |
| Diyarbakır | Diyarbakır Hani Jandarma Komando Tabur K.lığı Vardiya Yatakhanesi Md.lüğü | — | Hani | konum+adres |
| Diyarbakır | Diyarbakır İl Tarım ve Orman Md.lüğü Misafirhanesi | — | Yenişehir | konum+adres |
| Diyarbakır | Diyarbakır Jandarma Bölge K.lığı Sosyal Tesis Md.lüğü | — | Yenişehir | konum+adres |
| Diyarbakır | Diyarbakır Meteoroloji 15.Bölge Md.lüğü Misafirhanesi | — | Bağlar | konum+adres |
| Diyarbakır | Diyarbakır Orman İşletme Md.lüğü Misafirhanesi | — | Sur | konum |
| Diyarbakır | Diyarbakır Şehit Er Hayri Ayhan Kışlası Vardiya Yatakhanesi Md.lüğü | — | Ergani | konum+adres |
| Diyarbakır | Diyarbakır Silvan Jandarma Komando Alay K.lığı Sosyal Tesis Md.lüğü | — | Silvan | konum+adres |
| Diyarbakır | Diyarbakır TCDD Misafirhanesi | — | Yenişehir | konum+adres |
| Diyarbakır | Diyarbakır Üçkuyu Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | — | Yenişehir | konum+adres |
| Diyarbakır | Diyarbakır Vilayetler Evi (VE Hotels) | — | Sur | konum+adres |
| Diyarbakır | Lice Jandarma Komando Alay K.lığı Vardiya Yatakhanesi Md.lüğü | — | Lice | konum+adres |
| Diyarbakır | Türkiye Diyanet Vakfı Diyarbakır Konukevi | — | Yenişehir | konum+adres |
| Edirne | Edirne Askeri Gazino Md.lüğü | — | Merkez | konum+adres |
| Edirne | Edirne Başakşehir Belediyesi Enez Gençlik Kampı | — | Enez | konum+adres |
| Edirne | Edirne DSİ 114.Şube Md.lüğü İpsala Misafirhanesi | — | İpsala | konum+adres |
| Edirne | Edirne İl Özel İdaresi Misafirhanesi | — | Merkez | konum+adres |
| Edirne | Edirne İpsala 116. Jandarma Tesisleri | — | İpsala | konum+adres |
| Edirne | Edirne İstanbul Üniversitesi Enez Kampı | — | Enez | konum+adres |
| Edirne | Edirne Keşan Mecidiye Askeri Kampı (MSB Özel Eğitim Merkezi) | — | Keşan | konum+adres |
| Edirne | Edirne Maliye Kampı | — | Keşan | konum+adres |
| Edirne | Edirne Süloğlu Askeri Gazino Md.lüğü | — | Süloğlu | konum+adres |
| Edirne | Edirne TCDD Yatakhanesi | — | Merkez | konum+adres |
| Edirne | Edirne Trakya Üniversitesi Enez Kampı | — | Enez | konum+adres |
| Elazığ | Elazığ Ağın Yusuf Karabatak Öğretmenevi | — | Ağın | konum+adres |
| Elazığ | Elazığ Arıcak Öğretmenevi | — | Arıcak | konum+adres |
| Elazığ | Elazığ Askeri Gazinosu | — | Merkez | konum+adres |
| Elazığ | Elazığ Havalimanı Misafirhanesi | — | Merkez | konum |
| Elazığ | Elazığ İl Sağlık Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Erzincan | DHMİ Havacılık Akademisi Erzincan Eğitim Tesisi | — | Merkez | konum |
| Erzincan | Erzincan Çevre Şehircilik İl Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Erzurum | Diyanet Akademisi Erzurum Ömer Nasuhi Bilmen Dini Yüksek İhtisas Merkezi Misafirhanesi | — | Aziziye | konum+adres |
| Erzurum | Erzurum Atatürk Üniversitesi Konukevi-3 | — | Yakutiye | konum+adres |
| Erzurum | Erzurum Çevre ve Şehircilik İl Md.lüğü Misafirhanesi | — | Yakutiye | konum+adres |
| Erzurum | Erzurum Ilıca Kışla Gazino Md.lüğü | — | Aziziye | konum+adres |
| Erzurum | Erzurum Karaçoban Öğretmenevi | — | Karaçoban | konum+adres |
| Erzurum | Erzurum Oltu Askeri Gazino Md.lüğü | — | Oltu | konum+adres |
| Erzurum | Erzurum Orduevi Md.lüğü | — | Yakutiye | konum+adres |
| Erzurum | Hüseyin Turgut Erzurum Eğitim Merkezi Misafirhanesi | — | Yakutiye | konum+adres |
| Eskişehir | 1.Hava Bakım Fabrikası Vardiya Yatakhanesi Md.lüğü | — | Tepebaşı | konum+adres |
| Eskişehir | Eskişehir 1.Ana Jet Üs K.lığı Vardiya Yatakhanesi Md.lüğü | — | Tepebaşı | konum+adres |
| Eskişehir | Eskişehir Çevre ve Şehircilik İl Md.lüğü Misafirhanesi | — | Tepebaşı | konum+adres |
| Eskişehir | Eskişehir Hakimevi | — | Odunpazarı | konum+adres |
| Eskişehir | Eskişehir Jandarma Sosyal Tesis Md.lüğü | — | Odunpazarı | konum+adres |
| Eskişehir | Eskişehir Kışla Gazino Md.lüğü | — | Odunpazarı | konum+adres |
| Eskişehir | Eskişehir Meteoroloji 3.Bölge Md.lüğü Misafirhanesi | — | Odunpazarı | konum+adres |
| Eskişehir | Eskişehir Orman Bölge Müdürlüğü Misafirhanesi | — | Odunpazarı | konum+adres |
| Eskişehir | Eskişehir Sivrihisar Meydan K.lığı Kışla Gazino Md.lüğü | — | Sivrihisar | konum+adres |
| Eskişehir | Eskişehir Toprak Mahsulleri Ofisi Başmüdürlüğü Misafirhanesi | — | Odunpazarı | konum+adres |
| Gaziantep | Gaziantep Havalimanı Misafirhanesi | — | Oğuzeli | konum+adres |
| Gaziantep | Gaziantep İslahiye Sabancı Öğretmenevi | — | İslahiye | konum+adres |
| Gaziantep | Gaziantep Jandarma Sosyal Tesis Md.lüğü | — | Şahinbey | konum+adres |
| Gaziantep | Gaziantep Oğuzeli Öğretmenevi | — | Oğuzeli | konum+adres |
| Gaziantep | Gaziantep Şehit Karayılan Turizm Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | — | Şahinbey | konum+adres |
| Gaziantep | İslahiye Kışla Gazino Md.lüğü | — | İslahiye | konum+adres |
| Gaziantep | Türkiye Diyanet Vakfı Gaziantep Misafirhanesi | — | Şehitkamil | konum+adres |
| Giresun | Giresun Çamoluk Öğretmenevi | — | Çamoluk | konum+adres |
| Giresun | Giresun Doğankent Öğretmenevi | — | Doğankent | konum+adres |
| Giresun | Giresun DSİ Misafirhanesi | — | Merkez | konum+adres |
| Giresun | Giresun Karayolları 104.Şube Şefliği Misafirhanesi | — | Merkez | konum+adres |
| Giresun | Giresun Orman Bölge Müdürlüğü Misafirhanesi | — | Merkez | konum+adres |
| Giresun | Giresun Piraziz Öğretmenevi | — | Piraziz | konum+adres |
| Giresun | Yeşil Giresun Turizm Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | — | Merkez | konum+adres |
| Gümüşhane | Gümüşhane Jandarma Sosyal Tesis Md.lüğü | — | Merkez | konum+adres |
| Hakkari | Çukurca Askeri Gazino Md.lüğü | — | Çukurca | konum+adres |
| Hakkari | Hakkari Derecik Vardiya Yatakhanesi Md.lüğü | — | Derecik | konum+ad |
| Hakkari | Hakkari DSİ 174.Şube Şefliği Misafirhanesi | — | Merkez | konum+adres |
| Hakkari | Hakkari İl Özel İdaresi Misafirhanesi | — | Merkez | konum+adres |
| Hakkari | Hakkari Karayolları Misafirhanesi | — | Merkez | konum+adres |
| Hakkari | Hakkari Kışla Gazino Md.lüğü | — | Merkez | konum+adres |
| Hakkari | Hakkari Şemdinli Kışla Gazino Md.lüğü | — | Şemdinli | konum+adres |
| Hakkari | Hakkari Şemdinli Öğretmenevi | — | Şemdinli | konum+adres |
| Hakkari | Hakkari Yüksekova Askeri Gazinosu | — | Yüksekova | konum+adres |
| Hakkari | Hakkari Yüksekova Selahaddin Eyyubi Havalimanı Misafirhanesi | — | Yüksekova | konum+adres |
| Hatay | Dörtyol Jandarma Vardiya Yatakhanesi Md.lüğü | — | Dörtyol | konum+adres |
| Hatay | DSİ 63.Şube Md.lüğü Hatay Misafirhanesi | — | Antakya | konum+adres |
| Hatay | Hatay Defterdarlığı Dinlenme Tesisi ve Kampı | — | Arsuz | konum+adres |
| Hatay | Hatay Havalimanı Misafirhanesi | — | Antakya | konum |
| Hatay | Hatay Kışla Gazino Md.lüğü | — | Antakya | konum |
| Hatay | Hatay Mustafa Kemal Üniversitesi Misafirhanesi | — | Antakya | konum+adres |
| Hatay | Hatay TCDD Arsuz Eğitim ve Dinlenme Tesisi ve Kampı | — | Arsuz | konum+adres |
| Hatay | Hatay Yatırım İzleme ve Koordinasyon Başkanlığı Arsuz Eğitim ve Dinlenme Tesisi | — | Arsuz | konum+adres |
| Hatay | PTT Hatay Misafirhanesi | — | Antakya | konum+adres |
| Iğdır | Iğdır Askeri Gazino Md.lüğü | — | Merkez | konum+adres |
| Iğdır | Iğdır DSİ Misafirhanesi | — | Merkez | konum+adres |
| Iğdır | Iğdır İl Sağlık Müdürlüğü Misafirhanesi | — | Merkez | konum+adres |
| Iğdır | Iğdır Meteoroloji 16. Bölge Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Iğdır | Iğdır Şehit Bülent Aydın Havalimanı Misafirhanesi | — | Merkez | konum |
| Isparta | Isparta Kara Havacılık Okulu Kışla Gazino Md.lüğü | — | Keçiborlu | konum+adres |
| Isparta | Isparta Karayolları 135.Şube Şefliği Misafirhanesi | — | Merkez | konum+adres |
| Isparta | Isparta Kızaldağ Milli Parkı Konaklama Tesisleri | — | Şarkikaraağaç | konum+adres |
| Isparta | Isparta Orman Bölge Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| İstanbul | Adalet Bakanlığı Ord. Prof. Dr. Sulhi Dönmezer İstanbul Eğitim Merkezi Misafirhanesi | — | Bahçelievler | konum+adres |
| İstanbul | Bahçelievler Abidin Pak Öğretmenevi ve Akşam Sanat Okulu | — | Bahçelievler | konum+adres |
| İstanbul | Çaykur İstanbul Misafirhanesi | — | Sarıyer | konum+adres |
| İstanbul | Deniz Harp Okulu K.lığı Kışla Gazino Md.lüğü | — | Tuzla | konum+adres |
| İstanbul | DHMİ Florya Atatürk Havalimanı Misafirhanesi | — | Bakırköy | konum+adres |
| İstanbul | DHMİ Havacılık Akademisi İstanbul Eğitim Tesisi | — | Bakırköy | konum+adres |
| İstanbul | Diyanet Evi Sultanahmet | — | Fatih | konum+adres |
| İstanbul | DSİ 14. Bölge Misafirhanesi | — | Üsküdar | konum+adres |
| İstanbul | Et ve Süt Kurumu İstanbul Misafirhanesi | — | Beylikdüzü | konum+adres |
| İstanbul | İstanbul Alemdağ Jandarma Tabur K.lığı Vardiya Yatakhanesi Md.lüğü | — | Çekmeköy | konum+adres |
| İstanbul | İstanbul Anadolu Hakimevi | — | Ümraniye | konum+adres |
| İstanbul | İstanbul Ataşehir TEDAŞ-AYEDAŞ Bölge Misafirhanesi | — | Ataşehir | konum+adres |
| İstanbul | İstanbul Beylikdüzü Atatürk Öğretmenevi | — | Beylikdüzü | konum+adres |
| İstanbul | İstanbul Beyoğlu PTT Misafirhanesi | — | Beyoğlu | konum+adres |
| İstanbul | İstanbul Boğaz K.lığı Kışla Gazino Md.lüğü | — | Beykoz | konum+adres |
| İstanbul | İstanbul Hadımköy Kışla Gazino Md.lüğü | — | Esenyurt | konum+adres |
| İstanbul | İstanbul Hava Harp Okulu K.lığı Kışla Gazino Md.lüğü | — | Bakırköy | konum+adres |
| İstanbul | İstanbul İkmal Maliye Okulu K.lığı Kışla Gazino Md.lüğü | — | Maltepe | konum+adres |
| İstanbul | İstanbul Kara Dikimevi Md.lüğü Vardiya Yatakhanesi Md.lüğü | — | Maltepe | konum+adres |
| İstanbul | İstanbul Maltepe Kışla Gazino Md.lüğü | — | Maltepe | konum+adres |
| İstanbul | İstanbul MKE Misafirhanesi | — | Beyoğlu | konum+adres |
| İstanbul | İstanbul Pendik Pavli Vardiya Yatakhanesi Şb.Md.lüğü | — | Pendik | konum+adres |
| İstanbul | İstanbul Piyade Okul K.lığı Kışla Gazino Md.lüğü | — | Tuzla | konum+adres |
| İstanbul | İstanbul SGK Üsküdar Misafirhanesi | — | Üsküdar | konum+adres |
| İstanbul | İstanbul TCDD Fenarbahçe Sosyal Tesisleri | — | Kadıköy | konum+adres |
| İstanbul | İstanbul Ümraniye TEİAŞ 4.Bölge Md.lüğü Misafirhanesi | — | Ümraniye | konum+adres |
| İstanbul | İstanbul Vakıflar 1.Bölge Md.lüğü Misafirhanesi | — | Beyoğlu | konum+adres |
| İstanbul | İstanbul Vilayetler Birliği Boğaziçi Oteli | — | Sarıyer | konum+adres |
| İstanbul | İstanbul Yenilevent Askeri Gazino Md.lüğü | — | Beşiktaş | konum+adres |
| İstanbul | Meteoroloji 1. Bölge Müdürlüğü Misafirhanesi | — | Kartal | konum+adres |
| İstanbul | Sarıgazi Askeri Gazino Md.lüğü | — | Çekmeköy | konum+adres |
| İzmir | Alaçatı Öğretmenevi ve Akşam Sanat Okulu | — | Çeşme | konum+adres |
| İzmir | DHMİ İzmir Adnan Menderes Havalimanı Misafirhanesi | — | Gaziemir | konum+adres |
| İzmir | İzmir Alsancak Tarihi Uygulama Oteli | — | Konak | konum+adres |
| İzmir | İzmir Balçova Termal Otel ve Sosyal Tesisleri | — | Balçova | konum+adres |
| İzmir | İzmir Bergama Askeri Gazino Md.lüğü | — | Bergama | konum+adres |
| İzmir | İzmir Buca Açık Ceza İnfaz Kurumu Misafirhanesi | — | Buca | konum+adres |
| İzmir | İzmir Çeşme Polisevi | — | Çeşme | konum+adres |
| İzmir | İzmir Çeşme Turizm Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | — | Çeşme | konum+adres |
| İzmir | İzmir Dokuz Eylül Üniversitesi Öğretim Elemanı ve Araştırmacı Konukevi | — | Buca | konum+adres |
| İzmir | İzmir Dokuz Eylül Üniversitesi Seferihisar Öğrenci Eğitim ve Dinlenme Tesisleri | — | Seferihisar | konum+adres |
| İzmir | İzmir DSİ 2.Bölge Md.lüğü Gümüldür Kampı | — | Menderes | konum+adres |
| İzmir | İzmir Hava Teknik Okl.K.lığı Vardiya Yatakhanesi Md.lüğü ve Gaziemir Askeri Gazino Md.lüğü | — | Gaziemir | konum+adres |
| İzmir | İzmir Ilıca PTT Eğitim Merkezi ve Konukevi | — | Çeşme | konum+adres |
| İzmir | İzmir İl Jandarma K.lığı Sosyal Tesis Md.lüğü | — | Buca | konum+adres |
| İzmir | İzmir Karaburun-Akdağ Havacılık Akademisi Eğitim Tesisi | — | Karaburun | konum+adres |
| İzmir | İzmir Menemen Kışla Gazino Md.lüğü | — | Menemen | konum+adres |
| İzmir | İzmir Narlıdere Polisevi (Moral Eğitim Merkezi) | — | Narlıdere | konum+adres |
| İzmir | İzmir Sahil Güvenlik Hava K.lığı Kışla Gazino Md.lüğü | — | Gaziemir | konum+adres |
| İzmir | İzmir Seferihisar Jandarma Sosyal Tesis Md.lüğü | — | Seferihisar | konum+adres |
| İzmir | İzmir Seferihisar Polisevi (Polis Kampı) | — | Seferihisar | konum+adres |
| İzmir | İzmir Selçuk Uygulama Oteli | — | Selçuk | konum+adres |
| İzmir | İzmir SGK Misafirhanesi | — | Konak | konum+adres |
| İzmir | İzmir Tarım ve Orman Bakanlığı Foça Kampı | — | Foça | konum+adres |
| İzmir | İzmir Türkiye Diyanet Vakfı Tire Konukevi | — | Tire | konum+adres |
| İzmir | İzmir Urla Polisevi | — | Urla | konum+adres |
| İzmir | İzmir Yeni Foça Polisevi (Foça) | — | Foça | adres+ad |
| İzmir | Meteoroloji 2. Bölge Müdürlüğü Misafirhanesi | — | Konak | konum+adres |
| İzmir | Narlıdere Kışla Gazino Md.lüğü | — | Narlıdere | konum+adres |
| Kahramanmaraş | Kahramanmaraş Çevre ve Şehircilik İl Müdürlüğü Misafirhanesi | — | Onikişubat | konum+adres |
| Kahramanmaraş | Kahramanmaraş Ekinözü Öğretmenevi | — | Ekinözü | konum+adres |
| Kahramanmaraş | Kahramanmaraş İl Sağlık Müdürlüğü Misafirhanesi | — | Onikişubat | konum |
| Kahramanmaraş | Kahramanmaraş Karayolları Misafirhanesi | — | Onikişubat | konum+adres |
| Karabük | Karabük Eflani Öğretmenevi | — | Eflani | konum+adres |
| Karabük | Karabük Karayolları 153.Şube Şefliği Misafirhanesi | — | Safranbolu | konum+adres |
| Karabük | Karabük Safranbolu Cemil Meriç Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | — | Safranbolu | konum+adres |
| Karabük | Karabük Safranbolu PTT Misafirhanesi | — | Safranbolu | konum+adres |
| Karaman | Karaman Çevre ve Şehircilik İl Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Karaman | Karaman İl Sağlık Md.lüğü Eğitim ve Konaklama Tesisi | — | Merkez | konum+adres |
| Kars | Kars Harakani Havalimanı Misafirhanesi | — | Merkez | konum |
| Kars | Kars İl Sağlık Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Kastamonu | Ilgaz Jandarma Kış Eğitim Merkezi K.lığı | — | Merkez | konum+adres |
| Kastamonu | Kastamonu Azdavay Belediyesi Mehmet Avni İman Sosyal Tesisleri | — | Azdavay | konum+adres |
| Kastamonu | Kastamonu Çatalzeytin Öğretmenevi | — | Çatalzeytin | konum+adres |
| Kastamonu | Kastamonu Doğanyurt Necdet Ruhi Aygün Öğretmenevi | — | Doğanyurt | konum+adres |
| Kastamonu | Kastamonu İhsangazi Belediye Misafirhanesi | — | İhsangazi | konum+adres |
| Kastamonu | Kastamonu İlbank Misafirhanesi | — | Merkez | konum+adres |
| Kastamonu | Kastamonu Jandarma Komando Vardiya Yatakhanesi Md.lüğü | — | Merkez | konum+adres |
| Kastamonu | Kastamonu Karayolları 15.Bölge Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Kastamonu | Kastamonu Tapu ve Kadastro 19.Bölge Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Kayseri | 12.Hava Ulaştırma Ana Üs K.lığı Kışla Gazino Md.lüğü | — | Kocasinan | konum+adres |
| Kayseri | Kayseri 2.Hava Bakım Fabrika Md.lüğü Vardiya Yatakhanesi Md.lüğü | — | Melikgazi | konum+adres |
| Kayseri | Kayseri Erciyes Jandarma Kış Eğitim Merkezi K.lığı | — | Melikgazi | konum+adres |
| Kayseri | Kayseri Havalimanı Misafirhanesi | — | Kocasinan | konum |
| Kayseri | Kayseri İl Sağlık Md.lüğü Bölge Eğitim Araştırma ve Uygulama Merkezi Misafirhanesi | — | Melikgazi | konum+adres |
| Kayseri | Kayseri Jandarma Vardiya Yatakhanesi Md.lüğü | — | Melikgazi | konum+adres |
| Kayseri | Kayseri Kışla Gazino Md.lüğü | — | Melikgazi | konum+adres |
| Kıbrıs | Güngör Kışla Gazino Md.lüğü | — | Lefkoşa | adres |
| Kıbrıs | Yeşilyurt Askeri Gazino Md.lüğü | — | Güzelyurt | adres |
| Kilis | Kilis İl Özel İdare Misafirhanesi | — | Merkez | konum+adres |
| Kırşehir | Kırşehir Çiçekdağı Şehit Yücel Yılmaz Öğretmenevi | — | Çiçekdağı | konum+adres |
| Kırşehir | Kırşehir Karayolları Misafirhanesi | — | Merkez | konum+adres |
| Kocaeli | Gölcük Tersanesi Kışla Gazino Md.lüğü | — | Gölcük | konum+adres |
| Kocaeli | Kocaeli Darıca Yerel Özel Eğitim Merkezi (Kamp) | — | Darıca | konum+adres |
| Kocaeli | Kocaeli Gümrük ve Muhafaza Baş Md.lüğü Misafirhanesi | — | İzmit | konum+adres |
| Kocaeli | Kocaeli Jandarma Sosyal Tesis K.lığı | — | İzmit | konum+adres |
| Kocaeli | Kocaeli Kandıra Kefken Kampı | — | Kandıra | konum+adres |
| Kocaeli | Kocaeli Kartepe Askeri Gazino Md.lüğü | — | Kartepe | konum+adres |
| Kocaeli | Kocaeli Üniversitesi Derbent Uygulama Oteli | — | Kartepe | konum+adres |
| Kocaeli | Türkiye Diyanet Vakfı Kocaeli Konukevi | — | Başiskele | konum+adres |
| Konya | Konya 3.Ana Jet Üssü Kışla Gazino Md.lüğü | — | Selçuklu | konum+adres |
| Konya | Konya Çumra DSİ Misafirhanesi | — | Çumra | konum+adres |
| Konya | Konya Ereğli Polisevi | — | Ereğli | konum+adres |
| Konya | Konya Fidanlık Misafirhanesi | — | Meram | konum+adres |
| Konya | Konya Hakimevi | — | Karatay | konum+adres |
| Konya | Konya Havalimanı Misafirhanesi | — | Selçuklu | konum |
| Konya | Konya Ilgın DSİ İşletme Şefliği Misafirhanesi | — | Ilgın | konum+adres |
| Konya | Konya Karapınar Askeri Gazino Md.lüğü | — | Karapınar | konum+adres |
| Konya | Konya Subay Orduevi | — | Meram | adres (konum sınıra 0.1 km) |
| Konya | Konya Yunak Öğretmenevi | — | Yunak | konum+adres |
| Kütahya | Dumlupınar Üniversitesi Konukevi | — | Merkez | konum+adres |
| Kütahya | Kütahya Askeri Gazino Md.lüğü | — | Merkez | konum+adres |
| Kütahya | Kütahya Belediyesi Misafirhanesi | — | Merkez | konum+adres |
| Kütahya | Kütahya Hava Er Eğitim K.lığı Kışla Gazino Md.lüğü | — | Merkez | konum+adres |
| Kütahya | Kütahya Tavşanlı Öğretmenevi | — | Tavşanlı | konum+adres |
| Malatya | 7.Ana Jet Üs K.lığı Kışla Gazino Md.lüğü | — | Yeşilyurt | konum+adres |
| Malatya | Malatya 2.Ordu K.lığı Askeri Gazino Md.lüğü | — | Yeşilyurt | konum+adres |
| Malatya | Malatya Arapgir Şehit Hüsnü Bilgiç Öğretmenevi | — | Arapgir | konum+adres |
| Malatya | Malatya Doğanyol Tanrıverdi Öğretmenevi | — | Doğanyol | konum+adres |
| Malatya | Malatya Fırat Gümrük ve Dış Ticaret Bölge Müdürlüğü Misafirhanesi | — | Yeşilyurt | konum+adres |
| Manisa | Akhisar Vardiya Yatakhanesi Md.lüğü | — | Akhisar | konum+adres |
| Manisa | Kırkağaç Jandarma Sosyal Tesis Md.lüğü | — | Kırkağaç | konum+adres |
| Manisa | Manisa Ege Linyitleri İşletmesi Md.lüğü Misafirhanesi | — | Soma | konum+adres |
| Manisa | Manisa Gördes Ataman-Koç Öğretmenevi | — | Gördes | konum+adres |
| Manisa | Manisa Orman İşletme Md.lüğü Misafirhanesi | — | Yunusemre | konum+adres |
| Manisa | Türkiye Diyanet Vakfı Manisa Konukevi | — | Yunusemre | konum+adres |
| Manisa | Türk Metal Sendikası Manisa Misafirhanesi | — | Şehzadeler | konum |
| Mardin | 223.No.lu Hv.Rd.Kt.K.lığı Kışla Gazino Md.lüğü | — | Artuklu | konum+adres |
| Mardin | Mardin Jandarma Sosyal Tesis Md.lüğü | — | Artuklu | konum+adres |
| Mardin | Mardin Mazıdağı Öğretmenevi | — | Mazıdağı | konum+adres |
| Mardin | Mardin Ömerli Öğretmenevi ve Akşam Sanat Okulu Müdürlüğü | — | Ömerli | konum+adres |
| Mardin | Mardin Prof. Dr. Aziz Sancar Havalimanı Misafirhanesi | — | Kızıltepe | konum |
| Mardin | Nusaybin Kışla Gazino Md.lüğü | — | Nusaybin | konum+adres |
| Mersin | DHMİ Çukurova Uluslararası Havalimanı Misafirhanesi | — | Tarsus | konum+adres |
| Mersin | DSİ 6. Bölge Kapızlı Eğitim Ve Dinlenme Tesisi | — | Silifke | konum+adres |
| Mersin | Mersin Anamur Meteoroloji Md.lüğü Misafirhanesi | — | Anamur | adres+ad |
| Mersin | Mersin Çağ Üniversitesi Yaşar Bayboğan Konukevi | — | Tarsus | konum+adres |
| Mersin | Mersin Hizmet İçi Eğitim Enstitüsü | — | Yenişehir | konum+adres |
| Mersin | Mersin Sahil Güvenlik Akdeniz Bölge K.lığı Vardiya Yatakhanesi Md.lüğü | — | Akdeniz | konum+adres |
| Muğla | Dalaman Hava Meydan K.lığı Vardiya Yatakhanesi Md.lüğü | — | Dalaman | konum+adres |
| Muğla | Muğla Bodrum Turgut Reis Turizm Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | — | Bodrum | konum+adres |
| Muğla | Muğla Dalaman Deniz Hava Üs K.lığı Kışla Gazino Md.lüğü | — | Dalaman | konum+adres |
| Muğla | Muğla Dalaman Havalimanı Misafirhanesi | — | Dalaman | konum+adres |
| Muğla | Muğla Datça Hava Radar Mevzi Komutanlığı Sosyal Tesisleri | — | Datça | konum+adres |
| Muğla | Muğla Datça Kışla Gazino Md.lüğü | — | Datça | konum+adres |
| Muğla | Muğla Datça Meteoroloji Misafirhanesi | — | Datça | konum+adres |
| Muğla | Muğla Fethiye Şehit Yüzbaşı Özgür Özekin Turizm Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | — | Fethiye | konum+adres |
| Muğla | Muğla Köyceğiz Karayolları Misafirhanesi | — | Köyceğiz | konum+adres |
| Muğla | Muğla Marmaris Karayolları 26.Şube Şefliği Misafirhanesi | — | Marmaris | konum+adres |
| Muğla | Muğla Marmaris Meteoroloji Misafirhanesi | — | Marmaris | konum+adres |
| Muğla | Muğla Milas Hava Meydan K.lığı Vardiya Yatakhanesi Md.lüğü | — | Milas | konum+adres |
| Muğla | Muğla Mumcular Kışla Gazino Md.lüğü | — | Bodrum | konum+adres |
| Muğla | Muğla Sıtkı Koçman Üniversitesi Akyaka Uygulama Oteli | — | Ula | konum+adres |
| Muğla | Muğla Sıtkı Koçman Üniversitesi Sosyal Tesisler | — | Menteşe | konum |
| Muğla | Muğla Tarım İşletmeleri Genel Md.lüğü Dalaman Misafirhanesi | — | Dalaman | konum+adres |
| Muğla | Muğla Turgutreis Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | — | Bodrum | konum+adres |
| Muğla | Muğla Ula Öğretmenevi | — | Ula | konum+adres |
| Muş | Muş Askeri Gazino Md.lüğü | — | Merkez | konum+adres |
| Muş | Muş DSİ 172.Şube Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Muş | Muş Gıda, Tarım ve Hayvacılık İl Md.lüğü Misafirhanesi | — | Merkez | konum+adres |
| Muş | Muş Havaliamanı DHMİ Misafirhanesi | — | Merkez | konum+adres |
| Muş | Muş Hava Meydan K.lığı Vardiya Yatakhanesi Md.lüğü | — | Merkez | konum+adres |
| Muş | Muş Jandarma Sosyal Tesis Md.lüğü | — | Merkez | konum+adres |
| Muş | Muş Karayolları 113.Şube Şefliği Misafirhanesi | — | Merkez | konum+adres |
| Muş | Muş Nusret Sarman Lisesi Uygulama Oteli | — | Merkez | konum+adres |
| Muş | Muş Şeker Fabrikası Misafirhanesi | — | Merkez | konum+adres |
| Nevşehir | Nevşehir Gülşehir Öğretmenevi | — | Gülşehir | konum+adres |
| Nevşehir | Nevşehir Karayolları 67.Şube Şefliği Misafirhanesi | — | Merkez | konum+adres |
| Niğde | Niğde Bor Askeri Misafirhanesi (Gazino) | — | Bor | konum+adres |
| Niğde | Niğde Bor Kışla Gazino Md.lüğü | — | Bor | konum+adres |
| Niğde | Niğde İl Tarım ve Orman Müdürlüğü Misafirhanesi | — | Merkez | konum+adres |
| Ordu | Ordu 222 No.lu Hv.Rd.Kt.K.lığı Vardiya Yatakhanesi Md.lüğü | — | Perşembe | konum+adres |
| Ordu | Ordu Adliyesi Misafirhanesi | — | Altınordu | konum+adres |
| Ordu | Ordu Diyanet Misafirhanesi | — | Altınordu | konum+adres |
| Ordu | Ordu Öğretmenevi ve Akşam Sanat Okulu | — | Altınordu | konum+adres |
| Osmaniye | Osmaniye Askeri Gazino Md.lüğü | — | Merkez | konum+adres |
| Osmaniye | Osmaniye Çevre ve Şehircilik İl Müdürlüğü Misafirhanesi | — | Toprakkale | konum+adres |
| Osmaniye | Osmaniye Düziçi Öğretmenevi | — | Düziçi | konum+adres |
| Osmaniye | Osmaniye Sultan Alparslan Turizm Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | — | Merkez | konum+adres |
| Rize | Adalet Bakanlığı EDB Rize Personel Eğitim Merkezi ve Misafirhanesi | — | Merkez | adres (konum sınıra 0.2 km) |
| Rize | Rize – Artvin Havalimanı Misafirhanesi | — | Pazar | konum |
| Rize | Rize Çamlıhemşin Yamantürk Öğretmenevi | — | Çamlıhemşin | konum+adres |
| Rize | Rize Çaykur Sosyal Tesisleri | — | Merkez | konum+adres |
| Rize | Rize İl Özel İdaresi Misafirhanesi | — | Merkez | konum+adres |
| Rize | Rize Öğretmenevi ve Akşam Sanat Okulu | — | Merkez | konum |
| Rize | Rize Orman İşletme Md.lüğü Milli Parklar Misafirhanesi | — | Merkez | konum+adres |
| Rize | Şehit Altuğ Verdi Rize Polisevi | — | Merkez | adres (konum sınıra 0.1 km) |
| Sakarya | Et ve Süt Kurumu Sakarya Et Kombinası Md.lüğü Misafirhanesi | — | Erenler | konum+adres |
| Sakarya | Sakarya Karasu Öğretmenevi | — | Karasu | konum+adres |
| Sakarya | Sakarya Söğütlü Öğretmenevi ve Akşama Sanat Okulu | — | Söğütlü | konum+adres |
| Sakarya | Sakarya Taraklı Öğretmenevi | — | Taraklı | konum+adres |
| Sakarya | Sakarya Üniversitesi Kırkpınar Turizm Meslek Yüksekokulu Uygulama Oteli | — | Sapanca | konum+adres |
| Samsun | Samsun Büyükşehir Belediyesi Anakent Sosyal Tesisleri ve Misafirhanesi | — | Canik | konum+adres |
| Samsun | Samsun Çay-Kur Bölge Md.lüğü Misafirhanesi | — | İlkadım | konum |
| Samsun | Samsun Defterdarlığı Bölgesel Eğitim Merkezi ve Misafirhanesi | — | İlkadım | konum+adres |
| Samsun | Samsun Etibakır A.Ş. Misafirhanesi | — | Tekkeköy | konum+adres |
| Samsun | Samsun İl Özel İdaresi Misafirhanesi | — | İlkadım | konum+adres |
| Samsun | Samsun TEİAŞ 10.Bölge Md.lüğü Misafirhanesi | — | Tekkeköy | konum+adres |
| Samsun | Samsun Toprak Mahsulleri Ofisi Misafirhanesi | — | Tekkeköy | konum+adres |
| Şanlıurfa | Şanlıurfa Ceylanpınar Tarım İşletmesi Md.lüğü Misafirhanesi | — | Ceylanpınar | konum+adres |
| Şanlıurfa | Şanlıurfa Defterdarlık Misafirhanesi | — | Haliliye | konum |
| Şanlıurfa | Şanlıurfa GAP Havalimanı Misafirhanesi | — | Haliliye | konum |
| Şanlıurfa | Şanlıurfa Karaköprü Onikilier Öğretmenevi | — | Karaköprü | konum+adres |
| Şanlıurfa | Şanlıurfa Karayolları Misafirhanesi | — | Karaköprü | konum+adres |
| Şanlıurfa | Şanlıurfa Siverek Kışla Gazino Md.lüğü | — | Siverek | konum+adres |
| Şanlıurfa | Şanlıurfa Suruç Kışla Gazino Md.lüğü | — | Suruç | konum+adres |
| Şanlıurfa | Türkiye Diyanet Vakfı Şanlıurfa Konukevi | — | Eyyübiye | adres (konum sınıra 1.2 km) |
| Siirt | Siirt Askeri Gazinosu | — | Merkez | konum |
| Siirt | Siirt Baykan Öğretmenevi | — | Baykan | konum+adres |
| Siirt | Siirt Çevre ve Şehircilik İl Müdürlüğü Misafirhanesi | — | Merkez | konum+adres |
| Siirt | Siirt Jandarma Vardiya Yatakhanesi Md.lüğü | — | Merkez | konum+adres |
| Siirt | Siirt Kaymakam Suçi Misafirhanesi | — | Eruh | konum+adres |
| Siirt | Siirt Kışla Gazino Md.lüğü | — | Merkez | konum+adres |
| Sinop | Sinop Gençlik ve Spor İl Md.lüğü Sporcu Kampı | — | Merkez | konum+adres |
| Şırnak | Çakırsöğüt Jandarma Sosyal Tesis Md.lüğü | — | Merkez | konum+adres |
| Şırnak | Şırnak Askeri Gazinosu | — | Merkez | konum+adres |
| Şırnak | Şırnak Cizre Kışla Gazino Md.lüğü | — | Cizre | konum+adres |
| Şırnak | Şırnak Cizre Polisevi (Polis Lokali) | — | Cizre | konum+adres |
| Şırnak | Şırnak Defterdarlığı Misafirhanesi | — | Merkez | konum+adres |
| Şırnak | Şırnak İdil Öğretmenevi | — | İdil | konum+adres |
| Şırnak | Şırnak Jandarma Sosyal Tesis Md.lüğü | — | Merkez | konum+adres |
| Şırnak | Şırnak Karayolları Misafirhanesi | — | Cizre | konum+adres |
| Şırnak | Şırnak Şenoba Kışla Gazino Md.lüğü | — | Uludere | konum+adres |
| Şırnak | Şırnak Şerafettin Elçi Havalimanı Misafirhanesi | — | İdil | konum |
| Şırnak | Şırnak Silopi Kışla Gazino Md.lüğü | — | Silopi | konum+adres |
| Şırnak | Şırnak Silopi Polisevi | — | Silopi | konum+adres |
| Şırnak | Şırnak Uludere Öğretmenevi | — | Uludere | konum+adres |
| Sivas | Sivas Defterdarlığı Maliye Misafirhanesi | — | Merkez | konum+adres |
| Sivas | Sivas Doğanşar Öğretmenevi | — | Doğanşar | konum+adres |
| Sivas | Sivas Gölova Selahattin Ayan Öğretmenevi | — | Gölova | konum+adres |
| Sivas | Sivas Koyulhisar Öğretmenevi | — | Koyulhisar | konum+adres |
| Sivas | Sivas Mihmandar Uygulama Tesisleri | — | Merkez | konum |
| Sivas | Sivas Nuri Demirağ Havalimanı Misafirhanesi | — | Merkez | konum |
| Sivas | Sivas TEİAŞ Misafirhanesi | — | Merkez | konum+adres |
| Tekirdağ | Çorlu Hava Meydan K.lığı Vardiya Yatakhanesi Md.lüğü | — | Çorlu | konum+adres |
| Tekirdağ | Çorlu Orduevi Md.lüğü | — | Çorlu | konum+adres |
| Tekirdağ | Tekirdağ Çerkezköy Askeri Gazino Md.lüğü | — | Çerkezköy | konum+adres |
| Tekirdağ | Tekirdağ Çerkezköy Polisevi | — | Çerkezköy | konum+adres |
| Tekirdağ | Tekirdağ Çorlu Karayolları Misafirhanesi | — | Çorlu | adres (konum sınıra 0.4 km) |
| Tekirdağ | Tekirdağ Hayrabolu Askeri Gazino Md.lüğü | — | Hayrabolu | konum+adres |
| Tekirdağ | Tekirdağ Maliye Misafirhanesi | — | Şarköy | konum+adres |
| Tekirdağ | Tekirdağ Malkara Askeri Gazino Md.lüğü | — | Malkara | konum+adres |
| Tekirdağ | Tekirdağ Namık Kemal Üniversitesi Sosyal Tesisleri ve Misafirhanesi | — | Süleymanpaşa | konum |
| Tekirdağ | Tekirdağ Saray Askeri Gazino Md.lüğü | — | Saray | konum+adres |
| Tekirdağ | Tekirdağ Şarköy Turizm Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | — | Şarköy | konum+adres |
| Tekirdağ | Tekirdağ Şarköy Vardiya Yatakhanesi Md.lüğü | — | Şarköy | konum+adres |
| Tekirdağ | Ulusal Deniz Emniyeti Başkanlığı Tekirdağ Misafirhanesi | — | Marmaraereğlisi | konum+adres |
| Tokat | Tokat Askeri Gazino Md.lüğü | — | Merkez | konum+adres |
| Tokat | Tokat Defterdarlığı Misafirhanesi | — | Merkez | konum+adres |
| Trabzon | Trabzon Askeri Gazino Md.lüğü | — | Ortahisar | konum |
| Trabzon | Trabzon Sürmene İnci Hamitcan Aksoy Öğretmenevi | — | Sürmene | konum+adres |
| Tunceli | Tunceli Hozat Kışla Gazino Md.lüğü | — | Hozat | konum+adres |
| Tunceli | Tunceli İl Özel İdaresi Munzur Doğa Oteli | — | Merkez | konum+adres |
| Tunceli | Tunceli Jandarma Sosyal Tesis Md.lüğü | — | Merkez | konum+adres |
| Tunceli | Tunceli Karayolları Misafirhanesi | — | Merkez | konum+adres |
| Tunceli | Tunceli Munzur Üniversitesi Misafirhanesi | — | Merkez | konum+adres |
| Tunceli | Tunceli Pertek Öğretmenevi | — | Pertek | konum+adres |
| Tunceli | Tunceli TEDAŞ Misafirhanesi | — | Merkez | konum+adres |
| Uşak | Uşak Jandarma Sosyal Tesis Md.lüğü | — | Merkez | konum+adres |
| Uşak | Uşak Karayolları Misafirhanesi | — | Merkez | konum+adres |
| Uşak | Uşak Orman İşletme Müdürlüğü Misafirhanesi | — | Merkez | konum+adres |
| Van | Çevre ve Şehircilik Van İl Md.lüğü Misafirhanesi | — | Edremit | konum+adres |
| Van | Erciş Askeri Gazino Md.lüğü | — | Erciş | konum+adres |
| Van | Van Albayrak Kışla Gazino Md.lüğü | — | Başkale | konum+adres |
| Van | Van Çaldıran Kışla Gazino Md.lüğü | — | Çaldıran | konum+adres |
| Van | Van DHMİ Misafirhanesi | — | Edremit | konum+adres |
| Van | Van DSİ Erciş İşletme Bakım Başmühendisliği Misafirhanesi | — | Erciş | konum+adres |
| Van | Van Edremit Jandarma Sosyal Tesis Md.lüğü | — | Edremit | konum+adres |
| Van | Van Hava Radar K.lığı Vardiya Yatakhanesi Md.lüğü | — | Edremit | konum+adres |
| Van | Van Jandarma Sosyal Tesis Md.lüğü | — | İpekyolu | konum |
| Van | Van Karayolları Misafirhanesi | — | Edremit | konum+adres |
| Van | Van Özalp Kışla Gazino Md.lüğü | — | Özalp | konum+adres |
| Van | Van Toprakkale Kışla Gazino Md.lüğü | — | İpekyolu | konum |
| Yalova | Yalova Altınova Kışla Gazino Md.lüğü | — | Altınova | konum+adres |
| Yalova | Yalova Çiftlikköy Kışla Gazino Md.lüğü | — | Çiftlikköy | konum+adres |
| Yozgat | Yozgat Karayolları 65.Şube Şefliği Misafirhanesi | — | Merkez | konum+adres |
| Yozgat | Yozgat Şefaatli Öğretmenevi | — | Şefaatli | konum+adres |
| Yozgat | Yozgat Yenifakılı Öğretmenevi | — | Yenifakılı | konum+adres |
| Zonguldak | Zonguldak Ereğli Polisevi | — | Ereğli | konum+adres |

## Konum uyarıları (48)

İlçe adres + ad ile belirlendi ama koordinat başka yeri gösteriyor ya da koordinat geçersiz. Haritadaki pin yanlış yerde olabilir.

| İl | Tesis | Sorun |
|---|---|---|
| Adana | Adana Saimbeyli Öğretmenevi Ve Akşam Sanat Okulu | ilçe Saimbeyli; koordinat Feke içinde, kontrol edilmeli |
| Adana | Adana Yumurtalık Hava Kuvvetleri Askeri Kampı | ilçe Yumurtalık; adreste Sarıçam yazıyor, kontrol edilmeli |
| Ağrı | Taşlıçay Öğretmenevi | ilçe Taşlıçay; koordinat Merkez içinde, kontrol edilmeli |
| Aydın | Selçuk Şehit Er Mehmet Yüce İMKB Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli | ilçe Kuşadası; koordinat İzmir/Selçuk içinde, kontrol edilmeli |
| Balıkesir | Edremit Maliye Defterdarlık Misafirhanesi | ilçe Edremit; koordinat Balıkesir/Karesi içinde, kontrol edilmeli |
| Erzincan | Çayırlı Öğretmenevi | ilçe Çayırlı; koordinat Merkez içinde, kontrol edilmeli |
| Ankara | Ankara Nallıhan Öğretmenevi | ilçe Nallıhan; koordinat Çankaya içinde, kontrol edilmeli |
| Çankırı | Çankırı Ilgaz Kış Sporları Eğitim Merkezi | ilçe Ilgaz; koordinat Kastamonu/Merkez içinde, kontrol edilmeli |
| Aydın | Aydın Söke Zirai Üretim İşletmesi Tarımsal Yayım ve Hizmetiçi Eğitim Merkezi Md.lüğü Misafirhanesi | ilçe Söke; koordinat Didim içinde, kontrol edilmeli |
| Mersin | Mersin Anamur Meteoroloji Md.lüğü Misafirhanesi | ilçe Anamur; koordinat Yenişehir içinde, kontrol edilmeli |
| Hakkari | Hakkari Derecik Vardiya Yatakhanesi Md.lüğü | ilçe Derecik; adreste Şemdinli yazıyor, kontrol edilmeli |
| Aksaray | Aksaray Karayolları 3. Bölge Müdürlüğü Misafirhanesi | koordinat Kilis / Musabeyli içinde |
| Gümüşhane | Gümüşhane Halk Sağlığı Müdürlüğü Hekimevi | koordinat Kilis / Musabeyli içinde |
| Karaman | Karaman İl Özel İdaresi Merkez | koordinat Kilis / Musabeyli içinde |
| Kocaeli | Karamürselbey Eğitim Merkezi Komutanlığı | koordinat Yalova / Altınova içinde |
| Manisa | Yunusemre Belediyesi Misafirhanesi | koordinat Kilis / Musabeyli içinde |
| Mersin | Mersin Karayolları Narlıkuyu Dinlenme Tesisleri | koordinat Kilis / Musabeyli içinde |
| Sakarya | Kefken Özel Eğitim Merkezi K.lığı | koordinat Kocaeli / Kandıra içinde |
| Trabzon | Trabzon Öğretmenevi | koordinat Ordu / İkizce içinde |
| Yalova | Yalova Dsi Yazlık Dinlenme Tesisleri | koordinat Kilis / Musabeyli içinde |
| Yozgat | DSİ Yozgat Misafirhanesi | koordinat Kilis / Musabeyli içinde |
| Balıkesir | Ayvalık Öğretmenevi | koordinat Türkiye ilçe sınırlarının dışında |
| Balıkesir | Ören Özel Eğitim Merkezi Komutanlığı | koordinat Türkiye ilçe sınırlarının dışında |
| Çanakkale | Çanakkale Maliye Güzelyalı Eğitim ve Dinlenme Tesisileri Misafirhanesi | koordinat Türkiye ilçe sınırlarının dışında |
| Çanakkale | Çanakkale Subay Orduevi | koordinat Türkiye ilçe sınırlarının dışında |
| Çanakkale | Çanakkale Yahya Çavuş Orman Kampı | koordinat Türkiye ilçe sınırlarının dışında |
| Hatay | Gülcihan Yerel Özel Eğitim Merkezi Komutanlığı | koordinat Türkiye ilçe sınırlarının dışında |
| Hatay | Hatay Valiliği İskenderun Konuk Evi | koordinat Türkiye ilçe sınırlarının dışında |
| Hatay | İskenderun Orduevi | koordinat Türkiye ilçe sınırlarının dışında |
| Hatay | Maliye Bakanlığı Hatay İli Defterdarlığı Dinlenme Tesisi | koordinat Türkiye ilçe sınırlarının dışında |
| İstanbul | Beylerbeyi Askeri Gazino Müdürlüğü | koordinat Türkiye ilçe sınırlarının dışında |
| İstanbul | Beylerbeyi Sabancı Polisevi Sosyal Tesisi | koordinat Türkiye ilçe sınırlarının dışında |
| İstanbul | Hazine ve Maliye Bakanlığı Beyazıt Eğitim Tesisi ve Konukevi | koordinat Türkiye ilçe sınırlarının dışında |
| İstanbul | İstanbul Defterdarlığı Misafirhanesi | koordinat Türkiye ilçe sınırlarının dışında |
| İzmir | Hava Eğitim Komutanlığı Gazinosu | koordinat Türkiye ilçe sınırlarının dışında |
| İzmir | İzmir DEU Sosyal Tesisleri | koordinat Türkiye ilçe sınırlarının dışında |
| İzmir | İzmir Polis Evi Düğün Salonu | koordinat Türkiye ilçe sınırlarının dışında |
| İzmir | Yolluca Denizciler Kampı | koordinat Türkiye ilçe sınırlarının dışında |
| Samsun | Samsun Kurupelit Eğitim Merkezi | koordinat Türkiye ilçe sınırlarının dışında |
| Samsun | Samsun Tck Sosyal Tesisleri | koordinat Türkiye ilçe sınırlarının dışında |
| Sinop | Ahmet Muhip Dıranas Uygulama Oteli | koordinat Türkiye ilçe sınırlarının dışında |
| Trabzon | Trabzon Defterdarlığı Yıldızlı Misafirhane Ve Eğitim Tesisi | koordinat Türkiye ilçe sınırlarının dışında |
| Trabzon | Trabzon KTÜ Sahil Tesisleri | koordinat Türkiye ilçe sınırlarının dışında |
| Trabzon | TRT Trabzon Misafirhanesi | koordinat Türkiye ilçe sınırlarının dışında |
| Yalova | Yalova Zirai Mücadele Yazlık Dinlenme Tesisleri | koordinat Türkiye ilçe sınırlarının dışında |
| İzmir | İzmir Yeni Foça Polisevi (Foça) | koordinat Türkiye ilçe sınırlarının dışında |

## Yinelenen kayıtlar (4 grup)

Aynı il ve adla birden fazla kayıt. Uygulama bunları tek tesis olarak gösteriyor; veriden silinmedi.

| İl | Tesis | Tipler | Telefonlar |
|---|---|---|---|
| Ankara | TEİAŞ Enerji Misafirhanesi | DSİ Misafirhanesi / TEDAŞ Misafirhanesi | (0312) 418 85 01 / 0 (312) 203 87 18 |
| İzmir | Ilıksu Yerel Özel Eğitim Merkezi | orduevi / orduevi | 0 232 753 07 00 / 02327530700 |
| Karabük | Karabük jandarma sosyal tesisleri | orduevi / Üniversite Uygulama Oteli | 03704152526 / 0370 415 25 26 |
| Konya | Konya İl Jandarma Komutanlığı Misafirhanesi | ORDUEVİ / Çevre ve Şehircilik Misafirhanesi | 03322359010 / 03322359010 |

### Olası yinelenenler (19 çift)

Farklı adla kayıtlı, aynı telefon ve 300 m'den yakın koordinat. Gözle kontrol edilmeli.

- Ankara: "Çalışma Ve Sosyal Güvenlik Bakanlığı Misafirhanesi" ↔ "SGK Kavaklıdere Eğitim Tesisi" ((0312) 468 28 48)
- Ankara: "Lalahan Oramiral Emin Göksan Deniz Askeri Gazino Müdürlüğü" ↔ "Ora. Emin Göksan Askerî Gazino Müdürlüğü" (0 312 865 18 03)
- Bayburt: "Bayburt Üniversitesi Konukevi" ↔ "Bayburt Üniversitesi Uygulama Oteli" (04583332020)
- Diyarbakır: "Dicle Üniversitesi Misafirhane" ↔ "Dicle Üniversitesi, Havuzbaşı Sosyal Tesisleri" ((0412) 248 83 28)
- Gaziantep: "Gaziantep Defterdarlığı (Maliye) Misafirhanesi" ↔ "Gaziantep Üniversitesi Turizm Uygulama Oteli" (03423609045)
- Isparta: "Isparta DSİ Misafirhanesi" ↔ "Isparta DSİ Misafirhanesi ve Sosyal Tesisler" (0246 232 64 00)
- İstanbul: "Marmara Üniversitesi Konukevi" ↔ "Marmara Üniversitesi Misafirhanesi" (02167774190)
- İzmir: "DHMİ Havacılık Akademisi İzmir Eğitim Tesisi" ↔ "DHMİ İzmir Adnan Menderes Havalimanı Misafirhanesi" ((0232) 274 26 26)
- İzmir: "İzmir Metoroloji Bölge Müdürlüğü Misafirhanesi" ↔ "Meteoroloji 2. Bölge Müdürlüğü Misafirhanesi" (0232 285 39 65)
- İzmir: "Konak Astsubay Orduevi Ana Bina" ↔ "Konak Subay Orduevi" (02324411442)
- Kütahya: "Dumlupınar Üniversitesi Konukevi" ↔ "Kütahya Dumlupınar Üniversitesi Konukevi" (02744431362)
- Malatya: "İnönü Üniversitesi Hastahane Oteli" ↔ "Malatya Mehmet Şahin Nalbant Konukevi" (0 422 341 06 60)
- Mardin: "Mardin Hekimevi" ↔ "Mardin Hekimevi (İl Sağlık Müdürlüğü Misafirhanesi)" (04822127703)
- Muğla: "Muğla Sıtkı Koçman Üniversitesi Sosyal Tesisler" ↔ "Muğla Sıtkı Koçman Üniversitesi Sosyal Tesisler Konuk Evi" (0252 211 21 99)
- Ordu: "Ordu Devlet Su İşleri Misafirhanesi" ↔ "Ordu DSİ Misafirhanesi" (04525223326)
- Ordu: "Ordu Merkez Öğretmenevi ve Akşam Sanat Okulu" ↔ "Ordu Öğretmenevi ve Akşam Sanat Okulu" (0452 225 43 58)
- Osmaniye: "Jandarma Sosyal Tesis Müdürlüğü" ↔ "Osmaniye Jandarma Sosyal Tesisleri" (0-328-8130053)
- Rize: "Rize Merkez Öğretmenevi ve Akşam Sanat Okulu" ↔ "Rize Öğretmenevi ve Akşam Sanat Okulu" (0464 226 09 16)
- Zonguldak: "Jandarma Askeri Gazino Zonguldak Orduevi" ↔ "Zonguldak İl Jandarma Askeri Gazino Müdürlüğü" (0372 252 20 09)

## Kopyalanmış adresler (57 adres)

Birbirinden farklı tesislerde birebir aynı adres; en az biri yanlış. İlçe kararında kullanılmadı.

- **Aşağı Dudullu Mh. Cami cd. No:32. Ümraniye-İSTANBUL** → İstanbul: Adile Mermerci Uygulama Oteli; İstanbul: Anadolu Üniversitesi Aksaray Konukevi; İstanbul: Ataköy Konuk Evi Telekom; İstanbul: Avcılar Belediyesi Misafirhanesi Yurt; İstanbul: Balkan Vakfı Konukevi; İstanbul: Baltalimanı Polisevi; İstanbul: Beylerbeyi Sabancı Polisevi Sosyal Tesisi; İstanbul: Devlet Hava Meydanları İşletmesi Airport Akademi Misafirhane; İstanbul: Eti Maden İstanbul Misafirhanesi; İstanbul: Ortaköy Polis Evi Sosyal Tesisleri; İstanbul: Personel Misafirhanesi (TBMM-Milli Saraylar); İstanbul: Petrol İş Sendikası Eğitim Salonu ve Misafirhanesi; İstanbul: Polis Evi Ortaköy; İstanbul: SGK Topkapı Misafirhanesi; İstanbul: Sanayi Bakanlığı Şişli Misafirhanesi; İstanbul: Sancaktepe Konuk Evi; İstanbul: Sarıyer Polis Moral Eğitim Tesisleri; İstanbul: Selahaddin Eyyubi Mesleki ve Teknik Anadolu Lisesi ve Uygulama Oteli; İstanbul: Selimpaşa Uygulama Oteli Silivri/İstanbul; İstanbul: TBMM Yıldız Konukevi; İstanbul: Tarım İş Sendikası Konuk Evi Kartal; İstanbul: Türkiye Petrolleri Anonim Ortaklığı (TPAO), İstanbul İrtibat Ofisi & Misafirhanesi; İstanbul: Vakıfbank Kavacık Misafirhanesi; İstanbul: Yurtkurt Ortaköy Misafirhanesi; İstanbul: Ziraat Bankası Balmumcu Misafirhanesi; İstanbul: Ümraniye Öğretmenevi ASO; İstanbul: İlksan Kartal Konukevi; İstanbul: İlksan İstanbul Anadolu Yakası Eğitimciler Konukevi; İstanbul: İstanbul Orman Bölge Müdürlüğü Sosyal Tesisi
- **100. Yıl Mah. No:44. Yahyalı – KAYSERİ** → Kayseri: Erciyes Üniversitesi Kızılay Konukevi ve Uygulama Oteli; Kayseri: Hunat Otel Kamu Misafirhanesi Konukevii; Kayseri: Kayseri Emniyet Müdürlüğü Eğitim Ve Sosyal Tesisleri; Kayseri: Kayseri Konuk Evleri; Kayseri: Kayseri Memurlar Konukevi; Kayseri: Kayseri Misafirhane TEİAŞ; Kayseri: Kayseri İl Tarım ve Orman Müdürlüğü Mera Eğitim Merkezi ve Konuk Evi; Kayseri: Türk Diyanet Vakıf Sen Misafirhanesi Kayseri Konukevi Kamu misafirhanesi; Kayseri: Yahyalı Öğretmenevi
- **Şerefiye Mah. Veteriner Sok. İpekyolu, Van** → Van: Gümrük Misafirhanesi Van; Van: Van Bölge Müdürlüğü 17. Bölge Müdürlüğü Edremit Tesisleri; Van: Van DSİ 17. Bölge Müdürlüğü Yeni Misafirhanesi; Van: Van Hekimevi; Van: Van PTT Misafirhane; Van: Van Refakatçi Misafirhanesi; Van: Van Tcdd Misafirhane; Van: Van Uygulama Oteli (Edremit-Evliya Çelebi MTAL); Van: Van Yol-İş Sendikası Misafirhanesi
- **Kargı Mahallesi. Banka Sokak. No: 1/3. Tosya – KASTAMONU** → Kastamonu: Bayram Yusuf Aslan Turizm Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli; Kastamonu: Kastamonu Orman Bölge Müdürlüğü Misafirhanesi; Kastamonu: Kastamonu Orman İşletme Müdürlüğü Ilgaz Dağı Yangın Eğitim Merkezi; Kastamonu: Kastamonu Üniversitesi Cide Konukevi; Kastamonu: Kastamonu İl Tarım Müdürlüğü Sosyal Tesisler Misafirhanesi; Kastamonu: Teiaş 22. Bölge Müdürlüğü Kastamonu; Kastamonu: Tosya Öğretmenevi; Kastamonu: İnebolu Belediye Osman Sungur Motel
- **Cumhuriyet Meydanı. Cumhuriyet Caddesi. No:1. Tire – İZMİR** → İzmir: Alsancak Uygulama Oteli; İzmir: Araştırma Görevlileri Konuk Evi; İzmir: Bornova İzmir Uygulama Oteli; İzmir: Konak Alsancak Uygulama Oteli; İzmir: Tire Öğretmenevi; İzmir: İzmir Polis Evi Düğün Salonu; İzmir: İzmir Tınaztepe Üniversitesi Konukevi
- **Horozluhan Mah. Ankara Cad. 151 Selçuklu, Konya** → Konya: Konya Karayolları Bölge Müdürlüğü Misafirhanesi; Konya: Konya Orduevi; Konya: Konya Uygulama Oteli; Konya: Konya İl Jandarma Komutanlığı Misafirhanesi; Konya: Selçuk Üniversitesi Konuk Evi; Konya: Tenzile Ana Hasta Konukevi
- **Çarşı Mahallesi. Gülbahar Hatun Caddesi. No. 67. Vakfıkebir –Trabzon** → Trabzon: TRT Trabzon Misafirhanesi; Trabzon: Trabzon Defterdarlığı Yıldızlı Misafirhane Ve Eğitim Tesisi; Trabzon: Trabzon KTÜ Sahil Tesisleri; Trabzon: Trabzon İller Bankası Misafirhanesi; Trabzon: Vakfıkebir Uygulama Oteli; Trabzon: Vakfıkebir Öğretmenevi ve Akşam Sanat Okulu
- **Menekşe-2 Sk. No:22, Kızılay, Ankara** → Ankara: DSİ 5. Bölge Kızılay Misafirhanesi; Ankara: DSİ 5. Bölge Misafirhanesi Eskişehir Yolu; Ankara: DSİ 5. Bölge Müdürlüğü Bahçelievler Misafirhanesi; Ankara: Sosyal Güvenlik Kurumu Fevzi Çakmak Eğitim Tesisi Misafirhanesi; Ankara: TEİAŞ Enerji Misafirhanesi
- **Atatürk Caddesi. Kavaslı Köprü Yanı. HATAY** → Hatay: Antakya Belediyesi Sosyal Tesisleri; Hatay: Hatay Jandarma Sosyal Tesis Müdürlüğü; Hatay: Hatay Polisevi; Hatay: Hatay Valiliği İskenderun Konuk Evi; Hatay: Maliye Bakanlığı Hatay İli Defterdarlığı Dinlenme Tesisi
- **Yeni Mahalle Çaycuma Belediyesi Sosyal Tesisleri Küme Evler No:1 Çaycuma/ZONGULDAK** → Kıbrıs: Gazimağusa Orduevi; Kıbrıs: Girne Yalı Orduevi; Kıbrıs: Güven Orduevi; Zonguldak: Zonguldak TTK Misafirhanesi; Zonguldak: Çaycuma Belediyesi SEKA Misafirhanesi
- **Çağlar, Diyarbakır Mardin Yolu, 47100 Artuklu/Mardin** → Mardin: Hava Radar Kıta Komutanlığı Misafirhanesi; Mardin: Mardin Hekimevi; Mardin: Mardin Karayolları Misafirhanesi; Mardin: Mardin Nahıl Misafirevi; Mardin: Şatana Konağı (Maü Uygulama Oteli)
- **Tuzla, Cahit Gündüz Cd. No:3, 48300 Fethiye/Muğla** → Muğla: DSİ 21. Bölge Eğitim Tesisleri Fethiye; Muğla: Dalaman Ceza infaz Kurumu Oteli; Muğla: Muğla Karayolları Misafirhanesi Fethiye; Muğla: Muğla Sıtkı Koçman Üniversitesi Sosyal Tesisler Konuk Evi; Muğla: Muğla Tarım İl Müdürlüğü Misafirhanesi Menteşe
- **Gelincik Mahallesi. Sinop Boyabat Şosesi. Yeni Emniyet Sarayı Arkası. SİNOP** → Sinop: Ahmet Muhip Dıranas Uygulama Oteli; Sinop: Sinop Devlet Konukevi; Sinop: Sinop Karayolları 79 Şubesi Şefliği; Sinop: Sinop Polisevi; Sinop: Sinop Prof. Dr. Necmettin Erbakan Mesleki ve Teknik Anadolu Lisesi Uygulama Oteli
- **Aziziye Mahallesi. Şehit Nazım Bey Caddesi. No:10 Karatay – Konya** → Konya: Dünya Mevlana Vakfı Derviş Misafirhanesi; Konya: Kadınhanı Belediyesi Oteli; Konya: Mevlana Öğretmenevi; Konya: İmkb Gmk Mtal Uygulama Oteli
- **Kemal Paşa Mahallesi.  Mimar Sinan Bulvarı. No:100. Şelale Yanı. Tarsus – Mersin** → Mersin: Mersin Yenişehir Belediyesi Misafirhanesi; Mersin: Mersin Yenişehir Devlet Su İşleri Misaifrhanesi; Mersin: Mersin Üniversitesi Konukevi; Mersin: Tarsus Otelcilik ve Turizm Meslek Lisesi Uygulama Oteli
- **Cumhuriyet Mahallesi. Cumhuriyet Caddesi. Hastane Tepesi. Turhal – Tokat** → Tokat: Tokat Devlet Su İşleri Misafirhanesi; Tokat: Tokat Osman Paşa Konağı Butik Uygulama Oteli; Tokat: Tokat İl Sağlık Müdürlüğü Misafirhanesi (75.Yıl Eğitim ve Sosyal Tesisi); Tokat: Turhal Polisevi
- **TCDD Misafirhanesi, 2. Bölge, Tren Garı, Ankara** → Ankara: Demiryol İş Misafirhanesi; Ankara: Devlet Malzeme Ofisi Misafirhanesi; Ankara: Deçev Misafirhanei
- **Tuğsavul Cad. 2.Kor.K.lığı karşısı** → Çanakkale: Gelibolu Hamzakoy Yerel Eğitim Kampı; Çanakkale: Gelibolu Orduevi Astsubay; Çanakkale: Gelibolu Orduevi Subay
- **Yalı Mah. Atatürk Cad. Akçakoca, Düzce** → Düzce: Akçakoca Karayolları Sosyal Tesisleri; Düzce: Ankara Büyükşehir Belediyesi Akçakoca Kampı; Düzce: Aķçakoca Orman İşletme Müdürlüğü Misafirhanesi
- **Azmimilli Mahallesi. Gazhane Caddesi. No: 70-1. Merkez-Düzce** → Düzce: Cumayeri Pakmaya Öğretmenevi ve ASO; Düzce: Düzce Öğretmenevi; Düzce: Yığılca Öğretmenevi
- **Mesherburnu Cd.No:43 Sarıyer / İSTANBUL** → İstanbul: Hazine ve Maliye Bakanlığı Beyazıt Eğitim Tesisi ve Konukevi; İstanbul: Sarıyer Öğretmenevi; İstanbul: İstanbul Defterdarlığı Misafirhanesi
- **Gaybiefendi, Atatürk Blv. No:93, 43020 Kütahya Merkez/Kütahya** → Kütahya: Kütahya Dumlupınar Üniversitesi Konukevi; Kütahya: Kütahya Uygulama Oteli; Kütahya: Kütahya Çevre ve Şehircilik İl Müdürlüğü Misafirhanesi
- **Perşembe Anadolu Otelcilik ve Turizm Meslek Lisesi. Eğitim Caddesi. No: 59. Perşembe – ORDU** → Ordu: Ordu Devlet Su İşleri Misafirhanesi; Ordu: Ordu Üniversitesi Misafirhanesi ve Konukevi; Ordu: Perşembe Turizm Otelcilik Uygulama Oteli
- **Fazıl Ahmet Paşa Mahallesi.121 Sokak. No:19. Vezirköprü-SAMSUN** → Samsun: Samsun Orman İşletme Müdürlüğü Misafirhanesi; Samsun: Samsun Uygulama Oteli; Samsun: Vezirköprü Öğretmenevi
- **Kızılırmak Mahallesi. Reşitpaşa Caddesi. Akın İş Merkezi Karşısı. Zara – SİVAS** → Sivas: Cumhuriyet Üniversitesi Konuk Evi 2; Sivas: Sivas Demir Çelik Fabrikası Konuk Evi; Sivas: Zara Öğretmenevi
- **Hürriyet, Çınarcık Yolu, 77340 Koruköy/Çınarcık/Yalova** → Yalova: Yalova Harb-iş Dinlenme Tesisleri; Yalova: Yalova Yalkim Osb Akmotel Sosyal Tesisleri; Yalova: Yalova Zirai Mücadele Yazlık Dinlenme Tesisleri
- **Erdogan akdag mh. Esentepe Mevkii** → Yozgat: DSİ Yozgat Misafirhanesi; Yozgat: Yozgat Bozok Konuk Evi; Yozgat: Yozgat Hekimevi
- **Çarkıpare Mahallesi. Mithat Özsan Bulvarı. No: 120 Sarıçam** → Adana: Adana Çukurova Üniversitesi 3 Nolu Konukevi; Adana: Adana Çukurova Üniversitesi Balcalı Konukevi
- **Anadolu Otelcilik ve Turizm Meslek Lisesi, Beşevler, Çankaya, Ankara** → Ankara: Ankara Yenimahalle Uygulama Oteli; Ankara: Mogan Mesleki Uygulama Oteli
- **Çankırı Caddesi No:36, Ulus, Ankara** → Ankara: Hazine ve Maliye Bakanlığı Personel Genel Müdürlüğü Misafirhanesi (PERGEN Misafirhanesi); Ankara: T.C. Maliye Bakanlığı Ankara Konukevi
- **SARIKIZ MAH.324.SK.NO:7 DAİRE:9 EDREMİT/BALIKESİR** → Balıkesir: Edremit Maliye Defterdarlık Misafirhanesi; Balıkesir: Eti Maden Şehir Misafirhanesi ve Lokali
- **Karşıyaka Mahallesi Biga Cad. No:4 Gönen-BALIKESİR** → Balıkesir: Gönen D.S.İ. Sosyal Tesisi; Balıkesir: Gönen Devlet Su İşleri Misafirhanesi
- **Zeytinlik Mah. Arif Kapuzoğlu Cad. No:8 Erdek** → Balıkesir: MSB Erdek Özel Eğitim Merkezi Komutanlığı; Balıkesir: TSK Özel Eğitim Merkez Komutanlığı
- **Barboros Mah. Şehit Gürol Cad.** → Çanakkale: Çanakkale Astsubay Orduevi; Çanakkale: Çanakkale Subay Orduevi
- **Dicle Üniversitesi Yerleşkesi. DİYARBAKIR** → Diyarbakır: Dicle Üniversitesi Misafirhane; Diyarbakır: Dicle Üniversitesi, Havuzbaşı Sosyal Tesisleri
- **Babademirtaş Mahallesi. Babatimurtaş Sokak. No: 5. EDİRNE** → Edirne: Edirne Polisevi; Edirne: Edirne Polisevi VIP
- **Atatürk Üniversitesi Kampüsü İçi  Aziziye, Erzurum** → Erzurum: Atatürk Üniversitesi Konuk Evi 2; Erzurum: Atatürk Üniversitesi Konuk Evi-1
- **Merkez Mahallesi. Cumhuriyet Caddesi. Uzundere – ERZURUM** → Erzurum: Erzurum Dsi Misafirhanesi; Erzurum: Uzundere Öğretmenevi
- **Sakarya Mahallesi. Girne Caddesi. No:10. Çifteler – ESKİŞEHİR** → Eskişehir: Tülomsaş Misafirhane Ve Sosyal Tesisi; Eskişehir: Çifteler Öğretmenevi
- **Cengiz Topel Caddesi No:2. ESKİŞEHİR** → Eskişehir: Eskişehir Astsubay Orduevi; Eskişehir: Eskişehir Subay Orduevi
- **Söğütlü Mahallesi. Işın Caddesi. No : 11. IĞDIR** → Iğdır: Iğdır Polisevi; Iğdır: Jandarma Sosyal Tesisleri
- **Libadiye Cad. 100. Yıl Durağı Küçükçamlıca, Üsküdar- İSTANBUL** → İstanbul: İstanbul Devlet Su İşleri Kartal Misafirhanesi; İstanbul: İstanbul Devlet Su İşleri Üsküdar Misafirhanesi
- **Cumhuriyet Cad. No: 1** → İstanbul: Selimiye Astsubay Orduevi; İstanbul: Şişli Harbiye Orduevi
- **Yunus Emre Yerleşkesi /KARAMAN** → Karabük: Karabük jandarma sosyal tesisleri; Karaman: Karamanoğlu Mehmetbey Üniversitesi Sosyal Bilimler Meslek Yüksekokulu Uygulama Oteli
- **Kazım Karabekir Mahallesi. Kazım Karabekir Caddesi. No:20. Susuz – KARS** → Kars: Devlet Su İşleri Misafirhanesi; Kars: Susuz Öğretmenevi Kazım Karabekir
- **İnönü Mahallesi Öğretmenevi Caddesi No:10 Kastamonu** → Kastamonu: Kastamonu Şerife Bacı Öğretmenevi; Kastamonu: Şerife Bacı Öğretmenevi Doğa Kültür Köyü
- **Serçeönü Mah. Savaş Bul. No: 7** → Kayseri: Erciyes Polisevi ve Kayak Merkezi; Kayseri: Kocasinan Kayseri Orduevi
- **Orta Mahalle. Vatan Sokak. Hükümet Caddesi. No:3/1. Tuzlukçu/KONYA** → Konya: Konya TCDD Misafirhanesi; Konya: Tuzlukçu Öğretmenevi
- **Akkent Mahallesi. GMK Bulvarı üzeri. No:555 Yenişehir – Mersin** → Mersin: Mersin Polisevi Mezitli; Mersin: Mersin İlce Emniyet Müdürlüğü Polis evi
- **Yeni mahalle. Niğde yolu üzeri. Adliye Karşısı. NEVŞEHİR** → Nevşehir: Nevşehir Jandarma Sosyal Tesisi; Nevşehir: Nevşehir Otelcilik ve Turizm Meslek Lisesi Uygulama Oteli
- **Semerciler, Çark Cd. No:151, 54100 Selahiye Köyü/Adapazarı/Sakarya** → Sakarya: Adapazarı Kışla Gazinosu; Sakarya: Kefken Özel Eğitim Merkezi K.lığı
- **Elperek Mahallesi. Ankara Caddesi. Pamukova – SAKARYA** → Sakarya: Pamukova Öğretmenevi; Sakarya: Sezginler MTAL Uygulama Oteli
- **Değirmenaltı mah. Şehit zülfikar tezcan sok. No:4/5 Süleymanpaşa – Tekirdağ** → Tekirdağ: Tekirdağ DSİ Misafirhanesi; Tekirdağ: Türkiye Diyanet Vakfı Tekirdağ Sosyal Tesisi
- **Merkez Mahallesi. Pülümür – TUNCELİ** → Tunceli: Pülümür Öğretmenevi; Tunceli: Tunceli Sağlık Müdürlüğü Dinlenme Tesisi
- **Atatürk Blv, No.: 56-Çankaya/ANKARA** → Ankara: Sıhhıye Orduevi Md.lüğü; Ankara: Sıhhıye Orduevi Md.lüğü Astsubay Misafirhanesi
- **Gölbaşı Mah., Hazar Gölü Yanı-Sivrice/ELAZIĞ** → Elazığ: Elazığ Karayolları 8. Bölge Dinlenme Tesisi ve Konukevi; Elazığ: Elazığ Meteoroloji 13. Bölge Md.lüğü Misafirhanesi
- **Van Ferit Melen Havaalanı Yerleşkesi-Edremit/VAN** → Van: Van DHMİ Misafirhanesi; Van: Van Hava Radar K.lığı Vardiya Yatakhanesi Md.lüğü

## Standart dışı tesis türü yazımları

Tür filtresi büyük/küçük harf ve Türkçe karakter duyarsız eşleştiği için veride değiştirilmedi.

- `orduevi`: 31
- `F`: 1
- `None`: 1
- `ORDUEVİ`: 1

## İl bazında tesis sayıları

| İl | Tesis | İlçe sayısı (tesisli) |
|---|---:|---:|
| Adana | 33 | 13 / 15 |
| Adıyaman | 12 | 6 / 9 |
| Afyonkarahisar | 17 | 8 / 18 |
| Ağrı | 17 | 7 / 8 |
| Aksaray | 10 | 5 / 8 |
| Amasya | 15 | 5 / 7 |
| Ankara | 99 | 17 / 25 |
| Antalya | 48 | 16 / 19 |
| Ardahan | 10 | 5 / 6 |
| Artvin | 13 | 7 / 9 |
| Aydın | 25 | 10 / 17 |
| Balıkesir | 44 | 11 / 20 |
| Bartın | 16 | 4 / 4 |
| Batman | 14 | 6 / 6 |
| Bayburt | 11 | 2 / 3 |
| Bilecik | 11 | 6 / 8 |
| Bingöl | 13 | 5 / 8 |
| Bitlis | 14 | 7 / 7 |
| Bolu | 14 | 5 / 9 |
| Burdur | 7 | 2 / 11 |
| Bursa | 37 | 11 / 17 |
| Çanakkale | 38 | 10 / 12 |
| Çankırı | 13 | 6 / 12 |
| Çorum | 14 | 7 / 14 |
| Denizli | 15 | 3 / 19 |
| Diyarbakır | 37 | 14 / 17 |
| Düzce | 12 | 5 / 8 |
| Edirne | 23 | 6 / 9 |
| Elazığ | 19 | 7 / 11 |
| Erzincan | 16 | 9 / 9 |
| Erzurum | 40 | 18 / 20 |
| Eskişehir | 24 | 4 / 14 |
| Gaziantep | 23 | 6 / 9 |
| Giresun | 22 | 13 / 16 |
| Gümüşhane | 11 | 5 / 6 |
| Hakkari | 15 | 5 / 5 |
| Hatay | 30 | 12 / 15 |
| Iğdır | 11 | 2 / 4 |
| Isparta | 22 | 7 / 13 |
| İstanbul | 132 | 31 / 39 |
| İzmir | 82 | 23 / 30 |
| Kahramanmaraş | 18 | 10 / 11 |
| Karabük | 11 | 3 / 6 |
| Karaman | 10 | 3 / 6 |
| Kars | 18 | 7 / 8 |
| Kastamonu | 31 | 13 / 20 |
| Kayseri | 34 | 8 / 16 |
| Kıbrıs | 15 | 4 / 6 |
| Kilis | 5 | 1 / 4 |
| Kırıkkale | 9 | 3 / 9 |
| Kırklareli | 12 | 4 / 8 |
| Kırşehir | 9 | 4 / 7 |
| Kocaeli | 26 | 10 / 12 |
| Konya | 42 | 19 / 31 |
| Kütahya | 18 | 7 / 13 |
| Malatya | 22 | 8 / 13 |
| Manisa | 19 | 9 / 17 |
| Mardin | 26 | 9 / 10 |
| Mersin | 31 | 12 / 13 |
| Muğla | 41 | 9 / 13 |
| Muş | 19 | 5 / 6 |
| Nevşehir | 13 | 5 / 8 |
| Niğde | 14 | 6 / 6 |
| Ordu | 20 | 7 / 19 |
| Osmaniye | 10 | 4 / 7 |
| Rize | 23 | 9 / 12 |
| Sakarya | 20 | 11 / 16 |
| Samsun | 33 | 13 / 17 |
| Şanlıurfa | 23 | 9 / 13 |
| Siirt | 15 | 6 / 7 |
| Sinop | 18 | 6 / 9 |
| Şırnak | 21 | 7 / 7 |
| Sivas | 28 | 13 / 17 |
| Tekirdağ | 25 | 8 / 11 |
| Tokat | 20 | 8 / 12 |
| Trabzon | 29 | 11 / 18 |
| Tunceli | 17 | 6 / 8 |
| Uşak | 10 | 2 / 6 |
| Van | 38 | 13 / 13 |
| Yalova | 10 | 4 / 6 |
| Yozgat | 22 | 13 / 14 |
| Zonguldak | 16 | 6 / 8 |

## İlçe bazında tesis sayıları

- **Adana** (33): Seyhan (7), Çukurova (6), Yüreğir (6), Sarıçam (3), — belirsiz — (2), Aladağ (1), Ceyhan (1), Feke (1), İmamoğlu (1), Karaisalı (1), Karataş (1), Kozan (1), Saimbeyli (1), Yumurtalık (1)
- **Adıyaman** (12): Merkez (7), Çelikhan (1), Gerger (1), Kahta (1), Sincik (1), Tut (1)
- **Afyonkarahisar** (17): Merkez (10), Bolvadin (1), Dazkırı (1), Dinar (1), Emirdağ (1), İscehisar (1), Sandıklı (1), Şuhut (1)
- **Ağrı** (17): Merkez (7), Doğubayazıt (2), Eleşkirt (2), Patnos (2), — belirsiz — (1), Hamur (1), Taşlıçay (1), Tutak (1)
- **Aksaray** (10): Merkez (5), Ağaçören (1), — belirsiz — (1), Eskil (1), Ortaköy (1), Sarıyahşi (1)
- **Amasya** (15): Merkez (9), Merzifon (3), Gümüşhacıköy (1), Suluova (1), Taşova (1)
- **Ankara** (99): Çankaya (46), Yenimahalle (10), Altındağ (8), — belirsiz — (5), Etimesgut (5), Gölbaşı (5), Keçiören (3), Mamak (3), Polatlı (3), Kızılcahamam (2), Sincan (2), Akyurt (1), Bala (1), Beypazarı (1), Çubuk (1), Haymana (1), Kahramankazan (1), Nallıhan (1)
- **Antalya** (48): Muratpaşa (13), Alanya (5), Manavgat (5), Kepez (4), — belirsiz — (3), Konyaaltı (3), Finike (2), Gazipaşa (2), Kaş (2), Kumluca (2), Akseki (1), Aksu (1), Demre (1), Elmalı (1), Kemer (1), Korkuteli (1), Serik (1)
- **Ardahan** (10): Merkez (5), Çıldır (2), Göle (1), Hanak (1), Posof (1)
- **Artvin** (13): Merkez (7), Ardanuç (1), Borçka (1), Hopa (1), Murgul (1), Şavşat (1), Yusufeli (1)
- **Aydın** (25): Didim (6), Efeler (6), Kuşadası (5), Söke (2), Bozdoğan (1), Germencik (1), Karacasu (1), Koçarlı (1), Kuyucak (1), Nazilli (1)
- **Balıkesir** (44): Karesi (8), Ayvalık (6), Edremit (6), Altıeylül (5), Bandırma (5), Burhaniye (4), Erdek (4), Gönen (3), Dursunbey (1), Manyas (1), Sındırgı (1)
- **Bartın** (16): Merkez (8), Amasra (5), Ulus (2), Kurucaşile (1)
- **Batman** (14): Merkez (9), Beşiri (1), Gercüş (1), Hasankeyf (1), Kozluk (1), Sason (1)
- **Bayburt** (11): Merkez (10), Demirözü (1)
- **Bilecik** (11): Merkez (4), Bozüyük (2), Söğüt (2), Gölpazarı (1), Pazaryeri (1), Yenipazar (1)
- **Bingöl** (13): Merkez (8), Kiğı (2), Adaklı (1), Genç (1), Karlıova (1)
- **Bitlis** (14): Merkez (6), Tatvan (3), Adilcevaz (1), Ahlat (1), Güroymak (1), Hizan (1), Mutki (1)
- **Bolu** (14): Merkez (9), — belirsiz — (1), Dörtdivan (1), Göynük (1), Seben (1), Yeniçağa (1)
- **Burdur** (7): Merkez (6), Bucak (1)
- **Bursa** (37): Osmangazi (19), Nilüfer (4), Mudanya (3), İznik (2), Yıldırım (2), — belirsiz — (1), Gemlik (1), İnegöl (1), Karacabey (1), Kestel (1), Mustafakemalpaşa (1), Orhangazi (1)
- **Çanakkale** (38): Merkez (15), Gelibolu (5), Gökçeada (5), — belirsiz — (3), Eceabat (3), Çan (2), Ayvacık (1), Bayramiç (1), Ezine (1), Lapseki (1), Yenice (1)
- **Çankırı** (13): Merkez (7), Ilgaz (2), Kızılırmak (1), Korgun (1), Orta (1), Şabanözü (1)
- **Çorum** (14): Merkez (8), Alaca (1), Bayat (1), İskilip (1), Mecitözü (1), Osmancık (1), Sungurlu (1)
- **Denizli** (15): Pamukkale (9), Merkezefendi (4), — belirsiz — (1), Çardak (1)
- **Diyarbakır** (37): Yenişehir (10), Sur (5), Bağlar (4), Kayapınar (4), Ergani (2), Lice (2), Silvan (2), — belirsiz — (1), Bismil (1), Çüngüş (1), Dicle (1), Eğil (1), Hani (1), Hazro (1), Kulp (1)
- **Düzce** (12): Merkez (5), Akçakoca (4), Cumayeri (1), Gölyaka (1), Yığılca (1)
- **Edirne** (23): Merkez (10), Keşan (4), Enez (3), İpsala (2), Süloğlu (2), Uzunköprü (2)
- **Elazığ** (19): Merkez (10), — belirsiz — (3), Ağın (1), Arıcak (1), Karakoçan (1), Kovancılar (1), Palu (1), Sivrice (1)
- **Erzincan** (16): Merkez (8), Çayırlı (1), İliç (1), Kemah (1), Kemaliye (1), Otlukbeli (1), Refahiye (1), Tercan (1), Üzümlü (1)
- **Erzurum** (40): Yakutiye (17), Palandöken (4), Aziziye (2), Oltu (2), Olur (2), Aşkale (1), Çat (1), Hınıs (1), Horasan (1), İspir (1), Karaçoban (1), Karayazı (1), Narman (1), Pazaryolu (1), Şenkaya (1), Tekman (1), Tortum (1), Uzundere (1)
- **Eskişehir** (24): Odunpazarı (12), Tepebaşı (9), — belirsiz — (1), Çifteler (1), Sivrihisar (1)
- **Gaziantep** (23): Şahinbey (10), Şehitkamil (5), Oğuzeli (3), İslahiye (2), — belirsiz — (1), Karkamış (1), Nizip (1)
- **Giresun** (22): Merkez (10), Alucra (1), Bulancak (1), Çamoluk (1), Dereli (1), Doğankent (1), Espiye (1), Eynesil (1), Görele (1), Keşap (1), Piraziz (1), Tirebolu (1), Yağlıdere (1)
- **Gümüşhane** (11): Merkez (7), Kelkit (1), Kürtün (1), Şiran (1), Torul (1)
- **Hakkari** (15): Merkez (7), Yüksekova (3), Çukurca (2), Şemdinli (2), Derecik (1)
- **Hatay** (30): Antakya (9), — belirsiz — (7), Arsuz (3), Dörtyol (2), Belen (1), Erzin (1), Hassa (1), İskenderun (1), Kırıkhan (1), Payas (1), Reyhanlı (1), Samandağ (1), Yayladağı (1)
- **Iğdır** (11): Merkez (10), Tuzluca (1)
- **Isparta** (22): Merkez (10), Eğirdir (3), — belirsiz — (2), Şarkikaraağaç (2), Yalvaç (2), Atabey (1), Keçiborlu (1), Yenişarbademli (1)
- **İstanbul** (132): Sarıyer (15), Beşiktaş (13), Üsküdar (11), — belirsiz — (9), Bakırköy (8), Kadıköy (7), Kartal (7), Beyoğlu (6), Fatih (6), Bahçelievler (4), Büyükçekmece (4), Şişli (4), Tuzla (4), Ümraniye (4), Avcılar (3), Çekmeköy (3), Maltepe (3), Adalar (2), Ataşehir (2), Beykoz (2), Beylikdüzü (2), Silivri (2), Zeytinburnu (2), Bağcılar (1), Çatalca (1), Esenyurt (1), Güngören (1), Küçükçekmece (1), Pendik (1), Sancaktepe (1), Şile (1), Sultangazi (1)
- **İzmir** (82): Konak (16), Foça (7), Karşıyaka (7), Bornova (6), Buca (6), — belirsiz — (5), Çeşme (5), Gaziemir (4), Narlıdere (3), Seferihisar (3), Balçova (2), Karaburun (2), Menderes (2), Selçuk (2), Tire (2), Urla (2), Bayındır (1), Bergama (1), Çiğli (1), Dikili (1), Kınık (1), Kiraz (1), Menemen (1), Ödemiş (1)
- **Kahramanmaraş** (18): Dulkadiroğlu (5), Onikişubat (5), Afşin (1), Andırın (1), Çağlayancerit (1), Ekinözü (1), Elbistan (1), Göksun (1), Nurhak (1), Türkoğlu (1)
- **Karabük** (11): Safranbolu (6), Merkez (4), Eflani (1)
- **Karaman** (10): Merkez (7), Başyayla (1), — belirsiz — (1), Ermenek (1)
- **Kars** (18): Merkez (11), Sarıkamış (2), Arpaçay (1), Digor (1), Kağızman (1), Selim (1), Susuz (1)
- **Kastamonu** (31): Merkez (16), Cide (2), İnebolu (2), Araç (1), Azdavay (1), — belirsiz — (1), Çatalzeytin (1), Daday (1), Doğanyurt (1), İhsangazi (1), Pınarbaşı (1), Şenpazar (1), Taşköprü (1), Tosya (1)
- **Kayseri** (34): Melikgazi (17), Kocasinan (10), Talas (2), Bünyan (1), Develi (1), Felahiye (1), Pınarbaşı (1), Yahyalı (1)
- **Kıbrıs** (15): Lefkoşa (4), — belirsiz — (3), Girne (3), Güzelyurt (3), Gazimağusa (2)
- **Kilis** (5): Merkez (5)
- **Kırıkkale** (9): Merkez (7), Keskin (1), Yahşihan (1)
- **Kırklareli** (12): Merkez (5), Lüleburgaz (3), Babaeski (2), — belirsiz — (1), Pınarhisar (1)
- **Kırşehir** (9): Merkez (6), Çiçekdağı (1), Kaman (1), Mucur (1)
- **Kocaeli** (26): İzmit (7), Gölcük (4), Kartepe (3), Başiskele (2), — belirsiz — (2), Gebze (2), Kandıra (2), Darıca (1), Derince (1), Karamürsel (1), Körfez (1)
- **Konya** (42): Karatay (7), Meram (7), Selçuklu (6), Çumra (2), Ereğli (2), Ilgın (2), Kadınhanı (2), Karapınar (2), Akşehir (1), — belirsiz — (1), Beyşehir (1), Bozkır (1), Cihanbeyli (1), Emirgazi (1), Hadim (1), Hüyük (1), Kulu (1), Seydişehir (1), Tuzlukçu (1), Yunak (1)
- **Kütahya** (18): Merkez (12), Emet (1), Gediz (1), Pazarlar (1), Şaphane (1), Simav (1), Tavşanlı (1)
- **Malatya** (22): Battalgazi (10), Yeşilyurt (6), Akçadağ (1), Arapgir (1), Darende (1), Doğanşehir (1), Doğanyol (1), Hekimhan (1)
- **Manisa** (19): Şehzadeler (4), Akhisar (3), Yunusemre (3), — belirsiz — (2), Soma (2), Demirci (1), Gördes (1), Kırkağaç (1), Salihli (1), Turgutlu (1)
- **Mardin** (26): Artuklu (13), Kızıltepe (3), Midyat (2), Nusaybin (2), — belirsiz — (1), Dargeçit (1), Derik (1), Mazıdağı (1), Ömerli (1), Savur (1)
- **Mersin** (31): Yenişehir (7), Silifke (5), Anamur (4), Tarsus (4), Akdeniz (2), — belirsiz — (2), Aydıncık (1), Bozyazı (1), Erdemli (1), Gülnar (1), Mezitli (1), Mut (1), Toroslar (1)
- **Muğla** (41): Menteşe (7), Marmaris (6), Bodrum (5), Dalaman (5), Fethiye (5), Datça (3), Köyceğiz (3), Milas (3), — belirsiz — (2), Ula (2)
- **Muş** (19): Merkez (15), Bulanık (1), Hasköy (1), Malazgirt (1), Varto (1)
- **Nevşehir** (13): Merkez (6), Ürgüp (4), Avanos (1), Gülşehir (1), Hacıbektaş (1)
- **Niğde** (14): Merkez (7), Bor (3), Altunhisar (1), Çamardı (1), Çiftlik (1), Ulukışla (1)
- **Ordu** (20): Altınordu (9), Perşembe (5), Ünye (2), Akkuş (1), Çaybaşı (1), Fatsa (1), Korgan (1)
- **Osmaniye** (10): Merkez (7), Düziçi (1), Kadirli (1), Toprakkale (1)
- **Rize** (23): Merkez (13), Pazar (3), Ardeşen (1), Çamlıhemşin (1), Çayeli (1), Fındıklı (1), Güneysu (1), İkizdere (1), Kalkandere (1)
- **Sakarya** (20): Adapazarı (7), — belirsiz — (2), Erenler (2), Akyazı (1), Geyve (1), Hendek (1), Karasu (1), Pamukova (1), Sapanca (1), Serdivan (1), Söğütlü (1), Taraklı (1)
- **Samsun** (33): İlkadım (9), Atakum (7), Tekkeköy (4), — belirsiz — (2), Canik (2), Alaçam (1), Ayvacık (1), Bafra (1), Çarşamba (1), Havza (1), Kavak (1), Ladik (1), Terme (1), Vezirköprü (1)
- **Şanlıurfa** (23): Haliliye (9), Karaköprü (4), Ceylanpınar (2), Eyyübiye (2), Akçakale (1), — belirsiz — (1), Birecik (1), Harran (1), Siverek (1), Suruç (1)
- **Siirt** (15): Merkez (10), Baykan (1), Eruh (1), Kurtalan (1), Pervari (1), Şirvan (1)
- **Sinop** (18): Merkez (11), Boyabat (2), Ayancık (1), — belirsiz — (1), Dikmen (1), Durağan (1), Türkeli (1)
- **Şırnak** (21): Merkez (7), Cizre (5), Silopi (3), İdil (2), Uludere (2), Beytüşşebap (1), Güçlükonak (1)
- **Sivas** (28): Merkez (16), Akıncılar (1), Divriği (1), Doğanşar (1), Gemerek (1), Gölova (1), Gürün (1), Kangal (1), Koyulhisar (1), Şarkışla (1), Suşehri (1), Yıldızeli (1), Zara (1)
- **Tekirdağ** (25): Süleymanpaşa (9), Çorlu (4), Şarköy (3), Çerkezköy (2), Hayrabolu (2), Malkara (2), Marmaraereğlisi (2), Saray (1)
- **Tokat** (20): Merkez (11), Turhal (2), Artova (1), Başçiftlik (1), — belirsiz — (1), Erbaa (1), Niksar (1), Reşadiye (1), Zile (1)
- **Trabzon** (29): Ortahisar (12), — belirsiz — (5), Akçaabat (2), Vakfıkebir (2), Araklı (1), Arsin (1), Beşikdüzü (1), Çarşıbaşı (1), Çaykara (1), Of (1), Sürmene (1), Tonya (1)
- **Tunceli** (17): Merkez (11), Hozat (2), Çemişgezek (1), Ovacık (1), Pertek (1), Pülümür (1)
- **Uşak** (10): Merkez (9), Eşme (1)
- **Van** (38): Edremit (8), İpekyolu (8), Tuşba (4), — belirsiz — (3), Erciş (3), Başkale (2), Çaldıran (2), Özalp (2), Bahçesaray (1), Çatak (1), Gevaş (1), Gürpınar (1), Muradiye (1), Saray (1)
- **Yalova** (10): Merkez (4), — belirsiz — (2), Çiftlikköy (2), Altınova (1), Çınarcık (1)
- **Yozgat** (22): Merkez (8), Yerköy (2), Akdağmadeni (1), Aydıncık (1), — belirsiz — (1), Boğazlıyan (1), Çayıralan (1), Çekerek (1), Kadışehri (1), Saraykent (1), Sarıkaya (1), Şefaatli (1), Sorgun (1), Yenifakılı (1)
- **Zonguldak** (16): Merkez (5), Çaycuma (3), Ereğli (3), Kozlu (3), Devrek (1), Kilimli (1)
