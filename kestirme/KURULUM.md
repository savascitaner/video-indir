# "Video İndir" kestirmesini iPhone'da kurma

Bu rehber, Kestirmeler (Shortcuts) uygulamasında kestirmeyi adım adım oluşturmanı anlatır.
Başlamadan önce [sunucunun](../README.md#1-sunucuyu-çalıştır) çalışıyor olması ve iPhone'dan
erişilebilmesi gerekir (tarayıcıda `https://SUNUCU-ADRESİN/saglik` açınca `{"durum":"ok"}` görmelisin).

> Eylem adları iOS 17/18 Türkçe arayüzüne göre yazıldı; parantez içinde İngilizce karşılıkları var.
> Eylem eklemek için kestirme düzenleyicide alttaki arama kutusuna adını yazman yeterli.

## Kestirme nasıl çalışacak?

1. YouTube / Instagram / X uygulamasında **Paylaş → Video İndir**'e dokunursun
   (ya da linki kopyalayıp kestirmeyi Kestirmeler uygulamasından / ana ekrandan çalıştırırsın, link panodan alınır).
2. Kestirme sunucuya videonun hangi çözünürlüklerde olduğunu sorar ve sana bir liste gösterir
   (ör. `1080p`, `720p`, `480p`, `Sadece ses`).
3. Ses kalitesini sorar: `Yüksek`, `Orta (128 kbps)`, `Düşük (64 kbps)`.
4. Video indirilir ve doğrudan **Fotoğraflar** galerine kaydedilir.
   `Sadece ses` seçersen `.m4a` dosyası **Dosyalar** uygulamasına kaydedilir (Fotoğraflar ses dosyası tutamaz).

## Adımlar

Kestirmeler uygulamasını aç → sağ üstteki **+** → üstteki adı **Video İndir** yap.

### 1. Ayarlar

1. **Metin** (Text) eylemi ekle, içine sunucu adresini yaz, sonunda `/` olmasın:
   `https://SUNUCU-ADRESİN`
2. Bu eylemin altına **Değişken Ayarla** (Set Variable) ekle, adını `Sunucu` yap.
3. Bir **Metin** eylemi daha ekle, içine `.env` dosyasındaki `API_KEY` değerini yaz.
4. Altına **Değişken Ayarla** ekle, adını `Anahtar` yap.

### 2. Linki al (paylaş menüsü veya pano)

1. Düzenleyicinin altındaki **ⓘ** (Ayrıntılar) düğmesine dokun ve **Paylaşım Sayfasında Göster**'i
   (Show in Share Sheet) aç. Kapat.
2. Kestirmenin en üstünde artık *"Paylaşım Sayfasından ... girdisi al"* satırı belirdi:
   - Girdi türü olarak **URL'ler**, **Safari web sayfaları** ve **Metin** dışındakileri kapat.
   - **Girdi yoksa** (If there's no input) seçeneğini **Panoyu Al** (Get Clipboard) yap.
     Böylece kestirmeyi paylaş menüsü dışında çalıştırınca kopyaladığın link kullanılır.
3. Ayarlar bölümünün sonuna (Değişken Ayarla `Anahtar`'ın altına) **Girdiden URL'leri Al** (Get URLs from Input)
   ekle; girdisi **Kestirme Girdisi** (Shortcut Input) olsun.
4. **Listeden Öğe Al** (Get Item from List) ekle → **İlk Öğe**.
5. **URL Kodla** (URL Encode) ekle → **Kodla**. Altına **Değişken Ayarla** → `Link`.

### 3. Çözünürlük ve ses seçeneklerini sor

1. **URL'nin İçeriklerini Al** (Get Contents of URL) ekle. URL kısmına şunu yaz
   (mavi kutucuklar değişkendir; klavyenin üstündeki değişken çubuğundan seç):

   `[Sunucu]/secenekler?url=[Link]`

   **Diğer Seçenekleri Göster** → **Başlıklar** (Headers) → **Yeni başlık ekle**:
   - Anahtar: `X-API-Key`
   - Metin: `[Anahtar]`
2. Altına **Değişken Ayarla** → `Bilgi`.
3. **Sözlük Değerini Al** (Get Dictionary Value) ekle: **`cozunurlukler`** anahtarının **Değeri**, kaynak `Bilgi`.
4. **Listeden Seç** (Choose from List) ekle. **Başlık** (Prompt): `Hangi çözünürlük?`
5. Altına **Değişken Ayarla** → `Kalite`.
6. **Sözlük Değerini Al** ekle: **`ses_secenekleri`** anahtarının **Değeri**, kaynak `Bilgi`.
7. **Listeden Seç** ekle. Başlık: `Ses kalitesi?`
8. Altına **Değişken Ayarla** → `Ses`.

### 4. İndir ve kaydet

1. **Bildirim Göster** (Show Notification) ekle: `İndiriliyor, biraz bekle…`
2. **Metin** ekle, içine `[Kalite]` yaz, altına **URL Kodla** → **Değişken Ayarla** `KodluKalite`.
3. **Metin** ekle, içine `[Ses]` yaz, altına **URL Kodla** → **Değişken Ayarla** `KodluSes`.
4. **URL'nin İçeriklerini Al** ekle:

   `[Sunucu]/indir?url=[Link]&kalite=[KodluKalite]&ses=[KodluSes]`

   Başlıklar: `X-API-Key` = `[Anahtar]` (1. adımdaki gibi). Altına **Değişken Ayarla** → `Dosya`.
5. **Eğer** (If) ekle: `Kalite` **şudur** (is) `Sadece ses`.
   - **Eğer** bloğunun içine: **Dosyayı Kaydet** (Save File) → girdi `Dosya`
     (**Nereye Kaydedileceğini Sor** açık kalırsa her seferinde klasör sorar; kapatıp bir klasör seçebilirsin).
   - **Değilse** (Otherwise) bloğunun içine: **Fotoğraf Albümüne Kaydet** (Save to Photo Album) → girdi `Dosya`,
     albüm **Son Öğeler** (Recents).
6. **Eğer Sonu**'nun altına **Bildirim Göster**: `Kaydedildi ✅`

Bitti. İlk çalıştırmada iOS, sunucuya bağlanmak ve Fotoğraflar'a kaydetmek için izin isteyecek;
**Her Zaman İzin Ver** de.

## Akış özeti

```
Metin (sunucu adresi)            → Sunucu
Metin (API anahtarı)             → Anahtar
Kestirme Girdisi (yoksa: Pano)
Girdiden URL'leri Al → İlk Öğe → URL Kodla → Link
URL'nin İçeriklerini Al  GET [Sunucu]/secenekler?url=[Link]   (X-API-Key)   → Bilgi
Sözlük Değeri "cozunurlukler" → Listeden Seç                 → Kalite
Sözlük Değeri "ses_secenekleri" → Listeden Seç               → Ses
URL'nin İçeriklerini Al  GET [Sunucu]/indir?url=[Link]&kalite=[Kalite]&ses=[Ses]  → Dosya
Eğer Kalite = "Sadece ses":  Dosyayı Kaydet
Değilse:                     Fotoğraf Albümüne Kaydet
```

## Sorun giderme

- **"Fotoğraf Albümüne Kaydet" hata veriyor:** Sunucu video yerine hata mesajı döndürmüştür.
  Geçici olarak Fotoğraf Albümüne Kaydet'ten önce **Hızlı Bakış** (Quick Look) ekleyip `Dosya`'ya bak;
  mesaj neyin yanlış gittiğini söyler (ör. API anahtarı hatalı, video özel/gizli, site girişi istiyor).
- **Link bulunamadı / boş liste:** Paylaş menüsünde bazı uygulamalar link yerine metin gönderir;
  `Girdiden URL'leri Al` bunu çözer. Yine olmazsa linki kopyalayıp kestirmeyi Kestirmeler uygulamasından çalıştır.
- **Uzun videolar zaman aşımına uğruyor:** Kestirmeler bir isteği sınırsız beklemez. Uzun videolarda düşük
  çözünürlük seç. 1080p üstü YouTube videoları VP9/AV1 olduğundan sunucu bunları Fotoğraflar için yeniden
  kodlar; bu yavaştır.
- **Instagram / X "giriş yapın" hatası:** Ana README'deki çerez (cookies) bölümüne bak.
