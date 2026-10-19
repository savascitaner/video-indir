"""Video İndir sunucusu.

iPhone'daki "Video İndir" kestirmesinin konuştuğu küçük bir HTTP servisi.
YouTube, Instagram, X (Twitter), TikTok vb. linkleri yt-dlp ile indirir ve
iPhone Fotoğraflar uygulamasının kabul ettiği MP4 (H.264/HEVC + AAC) olarak döndürür.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
import urllib.request

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

API_KEY = os.environ.get("API_KEY", "")
COOKIES_FILE = os.environ.get("COOKIES_FILE", "")
# Bu sürenin (saniye) üzerindeki videolar reddedilir; 0 = sınırsız.
MAX_SURE = int(os.environ.get("MAX_SURE", "0"))
# Kestirmenin güncel sürüm bilgisi. Repo gizliyse okuma izni olan bir GITHUB_TOKEN gerekir.
GUNCELLEME_URL = os.environ.get(
    "GUNCELLEME_URL",
    "https://api.github.com/repos/savascitaner/video-indir/contents/kestirme/surum.json?ref=main",
)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

SADECE_SES = "Sadece ses"
EN_IYI = "En iyi"
SES_SECENEKLERI = ["Yüksek", "Orta (128 kbps)", "Düşük (64 kbps)"]
STANDART_YUKSEKLIKLER = [2160, 1440, 1080, 720, 480, 360, 240, 144]
FOTOGRAFLAR_VIDEO_KODEKLERI = {"h264", "hevc"}

app = FastAPI(title="Video İndir")


def _yetki(x_api_key: str | None, anahtar: str | None) -> None:
    if API_KEY and API_KEY not in (x_api_key, anahtar):
        raise HTTPException(401, "API anahtarı hatalı veya eksik.")


def _link_kontrol(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        raise HTTPException(400, "Geçerli bir http(s) linki gönderin.")
    return url


def _ydl_ayarlari(**ek) -> dict:
    ayarlar = {"quiet": True, "no_warnings": True, "noprogress": True, "noplaylist": True}
    if COOKIES_FILE:
        ayarlar["cookiefile"] = COOKIES_FILE
    ayarlar.update(ek)
    return ayarlar


def _bilgi(url: str) -> dict:
    try:
        with YoutubeDL(_ydl_ayarlari()) as ydl:
            bilgi = ydl.extract_info(url, download=False)
    except DownloadError as hata:
        raise HTTPException(422, f"Video bilgisi alınamadı: {hata}") from hata
    if bilgi.get("_type") == "playlist":
        girdiler = [g for g in bilgi.get("entries") or [] if g]
        if not girdiler:
            raise HTTPException(422, "Bu linkte video bulunamadı.")
        bilgi = girdiler[0]
    if MAX_SURE and (bilgi.get("duration") or 0) > MAX_SURE:
        raise HTTPException(413, f"Video çok uzun (en fazla {MAX_SURE} saniye).")
    return bilgi


def _ses_abr(ses: str) -> int | None:
    """'Orta (128 kbps)' -> 128, 'Düşük' -> 64, 'Yüksek' -> None (en iyisi)."""
    duz = unicodedata.normalize("NFKD", ses).encode("ascii", "ignore").decode().lower()
    if duz.startswith("o"):
        return 128
    if duz.startswith("d"):
        return 64
    return None


def _kodekler(dosya: str) -> tuple[str, str]:
    cikti = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name", "-of", "json", dosya],
        capture_output=True, text=True, check=True,
    ).stdout
    video = ses = ""
    for akis in json.loads(cikti).get("streams", []):
        if akis.get("codec_type") == "video" and not video:
            video = akis.get("codec_name", "")
        elif akis.get("codec_type") == "audio" and not ses:
            ses = akis.get("codec_name", "")
    return video, ses


def _ffmpeg(*argumanlar: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *argumanlar], check=True)


def _fotograflara_uygun_mp4(girdi: str, klasor: str, abr: int | None) -> str:
    """Fotoğraflar'ın açamadığı kodekleri (VP9, AV1, Opus...) H.264/AAC'ye çevirir."""
    video, ses = _kodekler(girdi)
    cikti = os.path.join(klasor, "video.mp4")
    v_arg = ["-c:v", "copy"] if video in FOTOGRAFLAR_VIDEO_KODEKLERI else [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p"]
    if video == "hevc":
        v_arg += ["-tag:v", "hvc1"]  # iOS HEVC'yi yalnızca hvc1 etiketiyle oynatır
    if not ses:
        a_arg = ["-an"]
    elif ses == "aac" and abr is None:
        a_arg = ["-c:a", "copy"]
    else:
        a_arg = ["-c:a", "aac", "-b:a", f"{abr or 192}k"]
    _ffmpeg("-i", girdi, "-map", "0:v:0", "-map", "0:a:0?", *v_arg, *a_arg,
            "-movflags", "+faststart", cikti)
    return cikti


def _dosya_adi(baslik: str, uzanti: str) -> str:
    temiz = re.sub(r'[\\/:*?"<>|\r\n]+', " ", baslik or "video").strip()[:80] or "video"
    return f"{temiz}.{uzanti}"


@app.get("/saglik")
def saglik() -> dict:
    return {"durum": "ok"}


@app.get("/surum")
def surum() -> dict:
    """Kestirmenin GitHub'daki son sürümü: {"surum": 2, "link": "...", "notlar": "..."}.
    Okunamazsa {"surum": 0} döner ve kestirme güncelleme önermez."""
    istek = urllib.request.Request(GUNCELLEME_URL, headers={"Accept": "application/vnd.github.raw+json"})
    if GITHUB_TOKEN:
        istek.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    try:
        with urllib.request.urlopen(istek, timeout=5) as yanit:
            bilgi = json.loads(yanit.read())
        return {"surum": int(bilgi.get("surum", 0)), "link": bilgi.get("link", ""), "notlar": bilgi.get("notlar", "")}
    except (OSError, ValueError, AttributeError):
        return {"surum": 0, "link": "", "notlar": ""}


@app.get("/secenekler")
def secenekler(
    url: str = Query(..., description="Video linki"),
    x_api_key: str | None = Header(None),
    anahtar: str | None = Query(None),
) -> dict:
    """Kestirmenin soracağı çözünürlük ve ses seçeneklerini döndürür."""
    _yetki(x_api_key, anahtar)
    bilgi = _bilgi(_link_kontrol(url))
    yukseklikler = {
        f["height"] for f in bilgi.get("formats") or []
        if f.get("height") and f.get("vcodec") not in (None, "none")
    }
    if not yukseklikler and bilgi.get("height"):
        yukseklikler = {bilgi["height"]}
    # Standart değerler varsa yalnızca onları göster; yoksa (ör. dikey videolar) olduğu gibi listele.
    listede = sorted({h for h in yukseklikler if h in STANDART_YUKSEKLIKLER} or yukseklikler, reverse=True)
    return {
        "baslik": bilgi.get("title") or "video",
        "sure": bilgi.get("duration"),
        "cozunurlukler": ([f"{h}p" for h in listede] or [EN_IYI]) + [SADECE_SES],
        "ses_secenekleri": SES_SECENEKLERI,
    }


@app.get("/indir")
def indir(
    arka_plan: BackgroundTasks,
    url: str = Query(..., description="Video linki"),
    kalite: str = Query("en iyi", description="'720p' gibi bir çözünürlük ya da 'Sadece ses'"),
    ses: str = Query("Yüksek", description="Yüksek / Orta / Düşük"),
    x_api_key: str | None = Header(None),
    anahtar: str | None = Query(None),
):
    """Videoyu seçilen kalitede indirip MP4 (veya sadece ses için M4A) olarak döndürür."""
    _yetki(x_api_key, anahtar)
    url = _link_kontrol(url)
    abr = _ses_abr(ses)
    sadece_ses = "ses" in kalite.lower() or "audio" in kalite.lower()
    yukseklik = re.search(r"\d+", kalite)

    if sadece_ses:
        bicim, siralama = "ba/b", ["acodec:aac"]
    else:
        bicim = "bv*+ba/b"
        siralama = [f"res:{yukseklik.group()}" if yukseklik else "res", "vcodec:h264", "acodec:aac"]
    if abr:
        siralama.append(f"abr:{abr}")

    klasor = tempfile.mkdtemp(prefix="video-indir-")
    arka_plan.add_task(shutil.rmtree, klasor, ignore_errors=True)
    try:
        with YoutubeDL(_ydl_ayarlari(
            format=bicim,
            format_sort=siralama,
            outtmpl=os.path.join(klasor, "kaynak.%(ext)s"),
            merge_output_format="mp4" if not sadece_ses else None,
            match_filter=(lambda b, **_: "Video çok uzun" if MAX_SURE and (b.get("duration") or 0) > MAX_SURE else None),
        )) as ydl:
            bilgi = ydl.extract_info(url, download=True)
    except DownloadError as hata:
        shutil.rmtree(klasor, ignore_errors=True)
        raise HTTPException(422, f"Video indirilemedi: {hata}") from hata
    if bilgi.get("_type") == "playlist":
        bilgi = next((g for g in bilgi.get("entries") or [] if g), bilgi)

    kaynaklar = [f for f in os.listdir(klasor) if f.startswith("kaynak.")]
    if not kaynaklar:
        raise HTTPException(422, "Video indirilemedi (dosya oluşmadı).")
    kaynak = os.path.join(klasor, kaynaklar[0])

    try:
        if sadece_ses:
            cikti = os.path.join(klasor, "ses.m4a")
            _, a_kodek = _kodekler(kaynak)
            a_arg = ["-c:a", "copy"] if a_kodek == "aac" and abr is None else ["-c:a", "aac", "-b:a", f"{abr or 192}k"]
            _ffmpeg("-i", kaynak, "-vn", *a_arg, "-movflags", "+faststart", cikti)
            return FileResponse(cikti, media_type="audio/mp4", filename=_dosya_adi(bilgi.get("title"), "m4a"))
        cikti = _fotograflara_uygun_mp4(kaynak, klasor, abr)
    except subprocess.CalledProcessError as hata:
        raise HTTPException(500, f"Dönüştürme başarısız: {hata}") from hata
    return FileResponse(cikti, media_type="video/mp4", filename=_dosya_adi(bilgi.get("title"), "mp4"))
