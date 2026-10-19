# Video İndir

YouTube, Instagram, X (Twitter), TikTok ve yt-dlp'nin desteklediği diğer sitelerdeki videoları
iPhone'dan **tek dokunuşla Fotoğraflar galerisine** indiren bir Kestirmeler (Shortcuts) kestirmesi
ve onun konuştuğu küçük indirme sunucusu.

```
iPhone (Kestirme)  ── link ──▶  Sunucu (yt-dlp + ffmpeg)  ── MP4 ──▶  Fotoğraflar
```

## Neden bir sunucu gerekiyor?

iPhone'daki Kestirmeler uygulaması YouTube/Instagram/X videolarını kendi başına indiremez; bu siteler
videoyu doğrudan bir dosya linki olarak vermez. Bu işi [yt-dlp](https://github.com/yt-dlp/yt-dlp) yapar
ve yt-dlp iPhone'da çalışmaz. Bu yüzden yt-dlp'yi senin kontrolündeki bir bilgisayarda/sunucuda
çalıştırıyoruz, kestirme de ona "şu linki şu kalitede indir" diyor.

Sunucu ayrıca videoyu Fotoğraflar'ın açabileceği biçime (MP4, H.264/HEVC + AAC) çevirir; örneğin
YouTube'un VP9/AV1 videoları ya da Opus sesleri olduğu gibi kaydedilemez.

## Kurulum

### 1. Sunucuyu çalıştır

**Önerilen yol: kendi bilgisayarın + Tailscale.** Ev internetinden indirmek, YouTube'un
"bot olmadığını doğrula" ve Instagram'ın giriş engellerine bulut sunuculardan çok daha az takılır.
Bilgisayarın açıkken kestirme her yerden çalışır.

1. Bilgisayarına [Docker Desktop](https://www.docker.com/products/docker-desktop/) kur.
2. Bu repoyu indir ve klasörde `.env` dosyası oluştur:
   ```sh
   git clone https://github.com/savascitaner/video-indir.git
   cd video-indir
   cp .env.example .env
   ```
   `.env` içindeki `API_KEY` değerini uzun, rastgele bir şeyle değiştir (ör. `openssl rand -hex 24` çıktısı).
3. Başlat:
   ```sh
   docker compose up -d --build
   ```
   `http://localhost:8000/saglik` adresi `{"durum":"ok"}` göstermeli.
4. Bilgisayarına ve iPhone'una [Tailscale](https://tailscale.com/download) kur, ikisinde de aynı hesapla
   giriş yap. Tailscale uygulamasında bilgisayarının adını gör (ör. `evdeki-mac`).
   iPhone'dan sunucu adresin: `http://evdeki-mac:8000`
   (ya da Tailscale'in verdiği `100.x.y.z` IP'si ile `http://100.x.y.z:8000`).

**Docker olmadan:** Python 3.10+, `ffmpeg` gerekir.
```sh
cd sunucu
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
API_KEY=gizli-anahtar uvicorn app:app --host 0.0.0.0 --port 8000
```

**Bulut sunucu (VPS, Render, Railway vb.):** `sunucu/Dockerfile` her Docker destekleyen platformda çalışır.
`API_KEY` ortam değişkenini mutlaka ayarla. Veri merkezi IP'leri YouTube ve Instagram tarafından sık
engellendiği için çerez dosyası (aşağıda) gerekebilir.

### 2. Kestirmeyi iPhone'a ekle

Rehber: **[kestirme/KURULUM.md](kestirme/KURULUM.md)**. Mac'in varsa hazır `.shortcut` dosyasını tek komutla
üretip AirDrop ile gönderebilirsin; yoksa kestirmeyi adım adım bir kez elle kurarsın.

### 3. Kullan

- YouTube / Instagram / X uygulamasında videoda **Paylaş → Video İndir**, ya da
- linki **kopyala**, sonra Kestirmeler'den veya ana ekrandan **Video İndir**'i çalıştır.

Kestirme önce çözünürlüğü (`1080p`, `720p`, …, `Sadece ses`), sonra ses kalitesini sorar ve videoyu
Fotoğraflar'a kaydeder. `Sadece ses` seçilirse `.m4a` dosyası Dosyalar uygulamasına kaydedilir.

## Ayarlar (`.env`)

| Değişken | Açıklama |
|---|---|
| `API_KEY` | Kestirmenin `X-API-Key` başlığında göndereceği gizli anahtar. Boş bırakılırsa sunucu herkese açık olur, **önerilmez**. |
| `COOKIES_FILE` | İsteğe bağlı. Giriş gerektiren videolar (Instagram, gizli X hesapları, yaş sınırlı YouTube) için Netscape biçiminde çerez dosyası yolu. |
| `MAX_SURE` | İsteğe bağlı. Bu süreden (saniye) uzun videoları reddeder. `0` = sınırsız. |

### Çerez dosyası (Instagram / X giriş hatası)

1. Bilgisayardaki tarayıcında ilgili siteye giriş yap.
2. "Get cookies.txt LOCALLY" gibi bir eklentiyle çerezleri `cookies.txt` olarak dışa aktar, repo klasörüne koy.
3. `docker-compose.yml` içindeki `volumes` satırlarının başındaki `#` işaretlerini kaldır,
   `.env` içine `COOKIES_FILE=/cerez/cookies.txt` yaz ve `docker compose up -d` ile yeniden başlat.

Çerez dosyası hesabına erişim sağlar; kimseyle paylaşma (`.gitignore` onu repoya eklemez).

## Sunucu API'si

Tüm isteklerde `X-API-Key: <API_KEY>` başlığı (ya da `?anahtar=<API_KEY>` parametresi) gerekir.

| İstek | Ne yapar |
|---|---|
| `GET /saglik` | Sunucu ayakta mı? (`{"durum":"ok"}`) |
| `GET /secenekler?url=<link>` | `{"baslik", "sure", "cozunurlukler": ["1080p", …, "Sadece ses"], "ses_secenekleri": [...]}` |
| `GET /indir?url=<link>&kalite=720p&ses=Orta (128 kbps)` | Videoyu MP4 (ya da `kalite=Sadece ses` ise M4A) olarak döndürür. |

`kalite` için `720p` gibi bir çözünürlük, `En iyi` ya da `Sadece ses`; `ses` için `Yüksek`, `Orta` veya `Düşük` verilebilir.

## Bakım

Siteler sık değiştiği için yt-dlp de sık güncellenir. İndirmeler bir gün hata vermeye başlarsa
yeniden derlemek genelde yeterlidir:

```sh
docker compose build --no-cache && docker compose up -d
```

## Notlar

- 1080p üstü YouTube videoları yalnızca VP9/AV1 olarak sunulur; sunucu bunları Fotoğraflar için H.264'e
  çevirir. Bu, bilgisayarına göre uzun sürebilir ve Kestirmeler uzun bekleyişlerde zaman aşımına düşebilir.
  Uzun videolarda 1080p veya altını seç.
- Yalnızca hakkına sahip olduğun ya da indirmeye izin verilen içerikleri indir; sitelerin kullanım koşullarına uy.
