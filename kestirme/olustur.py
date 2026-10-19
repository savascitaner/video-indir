"""'Video İndir' kestirmesinin (.shortcut) imzasız hâlini üretir.

iPhone yalnızca imzalı kestirmeleri içe aktarır. İmzalamak için bir Mac'te:

    python3 kestirme/olustur.py imzasiz.shortcut
    shortcuts sign --mode anyone --input imzasiz.shortcut --output "Video İndir.shortcut"

GitHub Actions bu iki adımı otomatik yapar (.github/workflows/kestirme.yml).
"""

import json
import pathlib
import plistlib
import sys
import uuid

# Kestirmenin sürümü kestirme/surum.json'dan gelir; GitHub'daki daha büyükse kestirme güncelleme önerir.
SURUM = json.loads((pathlib.Path(__file__).parent / "surum.json").read_text(encoding="utf-8"))["surum"]

YER = "\ufffc"  # Kestirmeler metinlerinde değişkenin yerini tutan karakter


def degisken(ad: str) -> dict:
    return {"Type": "Variable", "VariableName": ad}


def ek(deger: dict) -> dict:
    """Tek bir değişkeni eylem girdisi olarak verir."""
    return {"Value": deger, "WFSerializationType": "WFTextTokenAttachment"}


def metin(*parcalar) -> dict:
    """Düz metin ve değişkenlerden (dict) oluşan bir metin alanı."""
    yazi, ekler = "", {}
    for parca in parcalar:
        if isinstance(parca, str):
            yazi += parca
        else:
            # Konumlar UTF-16 birimiyle sayılır
            konum = len(yazi.encode("utf-16-le")) // 2
            ekler[f"{{{konum}, 1}}"] = parca
            yazi += YER
    return {"Value": {"string": yazi, "attachmentsByRange": ekler}, "WFSerializationType": "WFTextTokenString"}


def eylem(kimlik: str, **parametreler) -> dict:
    return {"WFWorkflowActionIdentifier": f"is.workflow.actions.{kimlik}", "WFWorkflowActionParameters": parametreler}


# Çıktısı başka bir eyleme bağlanabilen eylemlerin Kestirmeler'deki çıktı adları
CIKTI_ADLARI = {
    "gettext": "Text",
    "detect.link": "URLs",
    "getitemfromlist": "Item from List",
    "urlencode": "URL Encoded Text",
    "downloadurl": "Contents of URL",
    "getvalueforkey": "Dictionary Value",
    "choosefromlist": "Chosen Item",
}


def cikti(e: dict) -> dict:
    """Bir eylemin çıktısına (sihirli değişken) bağlantı; eyleme UUID verir."""
    parametreler = e["WFWorkflowActionParameters"]
    parametreler.setdefault("UUID", str(uuid.uuid4()).upper())
    kimlik = e["WFWorkflowActionIdentifier"].removeprefix("is.workflow.actions.")
    return ek({"Type": "ActionOutput", "OutputUUID": parametreler["UUID"], "OutputName": CIKTI_ADLARI[kimlik]})


def zincir(*adimlar) -> list[dict]:
    """Eylemleri sıraya koyar; ad (str) gelen adımda önceki eylemin çıktısını o adlı
    değişkene atar, girdisi boş bırakılan eylemlere de önceki eylemin çıktısını bağlar."""
    sonuc: list[dict] = []
    for adim in adimlar:
        if isinstance(adim, str):
            sonuc.append(eylem("setvariable", WFVariableName=adim, WFInput=cikti(sonuc[-1])))
            continue
        kimlik = adim["WFWorkflowActionIdentifier"].removeprefix("is.workflow.actions.")
        if kimlik in ("getitemfromlist", "choosefromlist") and "WFInput" not in adim["WFWorkflowActionParameters"]:
            adim["WFWorkflowActionParameters"]["WFInput"] = cikti(sonuc[-1])
        sonuc.append(adim)
    return sonuc


def istek(*url_parcalari) -> dict:
    return eylem(
        "downloadurl",
        WFURL=metin(*url_parcalari),
        WFHTTPMethod="GET",
        ShowHeaders=True,
        WFHTTPHeaders={
            "Value": {"WFDictionaryFieldValueItems": [
                {"WFItemType": 0, "WFKey": metin("X-API-Key"), "WFValue": metin(degisken("Anahtar"))},
            ]},
            "WFSerializationType": "WFDictionaryFieldValue",
        },
    )


def eylemler() -> list[dict]:
    kosul, surum_kosulu, menu = (str(uuid.uuid4()).upper() for _ in range(3))
    return zincir(
        # 0-3: Ayarlar (içe aktarırken sorulur)
        eylem("gettext", WFTextActionText="http://"),
        "Sunucu",
        eylem("gettext", WFTextActionText=""),
        "Anahtar",
        # Güncelleme kontrolü: GitHub'daki surum.json bu kestirmeden yeniyse güncellemeyi öner
        istek(degisken("Sunucu"), "/surum"),
        "SurumBilgi",
        eylem("getvalueforkey", WFInput=ek(degisken("SurumBilgi")), WFGetDictionaryValueType="Value",
              WFDictionaryKey="surum"),
        "SonSurum",
        eylem("conditional", GroupingIdentifier=surum_kosulu, WFControlFlowMode=0, WFCondition=2,
              WFInput={"Type": "Variable", "Variable": ek(degisken("SonSurum"))}, WFNumberValue=str(SURUM)),
        eylem("choosefrommenu", GroupingIdentifier=menu, WFControlFlowMode=0,
              WFMenuPrompt="Video İndir'in yeni sürümü var. Güncellensin mi?", WFMenuItems=["Güncelle", "Şimdi değil"]),
        eylem("choosefrommenu", GroupingIdentifier=menu, WFControlFlowMode=1, WFMenuItemTitle="Güncelle"),
        eylem("getvalueforkey", WFInput=ek(degisken("SurumBilgi")), WFGetDictionaryValueType="Value",
              WFDictionaryKey="link"),
        "GuncellemeLinki",
        eylem("openurl", WFInput=ek(degisken("GuncellemeLinki"))),
        eylem("exit"),
        eylem("choosefrommenu", GroupingIdentifier=menu, WFControlFlowMode=1, WFMenuItemTitle="Şimdi değil"),
        eylem("choosefrommenu", GroupingIdentifier=menu, WFControlFlowMode=2),
        eylem("conditional", GroupingIdentifier=surum_kosulu, WFControlFlowMode=2),
        # Link (paylaş menüsü; yoksa pano)
        eylem("detect.link", WFInput=ek({"Type": "ExtensionInput"})),
        eylem("getitemfromlist", WFItemSpecifier="First Item"),
        "HamLink",
        eylem("urlencode", WFInput=metin(degisken("HamLink")), WFEncodeMode="Encode"),
        "Link",
        # Seçenekleri sor
        istek(degisken("Sunucu"), "/secenekler?url=", degisken("Link")),
        "Bilgi",
        eylem("getvalueforkey", WFInput=ek(degisken("Bilgi")), WFGetDictionaryValueType="Value",
              WFDictionaryKey="cozunurlukler"),
        eylem("choosefromlist", WFChooseFromListActionPrompt="Hangi çözünürlük?"),
        "Kalite",
        eylem("getvalueforkey", WFInput=ek(degisken("Bilgi")), WFGetDictionaryValueType="Value",
              WFDictionaryKey="ses_secenekleri"),
        eylem("choosefromlist", WFChooseFromListActionPrompt="Ses kalitesi?"),
        "Ses",
        # İndir
        eylem("notification", WFNotificationActionBody="İndiriliyor, biraz bekle…",
              WFNotificationActionSound=False),
        eylem("urlencode", WFInput=metin(degisken("Kalite")), WFEncodeMode="Encode"),
        "KodluKalite",
        eylem("urlencode", WFInput=metin(degisken("Ses")), WFEncodeMode="Encode"),
        "KodluSes",
        istek(degisken("Sunucu"), "/indir?url=", degisken("Link"),
              "&kalite=", degisken("KodluKalite"), "&ses=", degisken("KodluSes")),
        "Dosya",
        # Kaydet: ses → Dosyalar, video → Fotoğraflar
        eylem("conditional", GroupingIdentifier=kosul, WFControlFlowMode=0, WFCondition=4,
              WFInput={"Type": "Variable", "Variable": ek(degisken("Kalite"))},
              WFConditionalActionString="Sadece ses"),
        eylem("documentpicker.save", WFInput=ek(degisken("Dosya")), WFAskWhereToSave=True),
        eylem("conditional", GroupingIdentifier=kosul, WFControlFlowMode=1),
        eylem("savetocameraroll", WFInput=ek(degisken("Dosya"))),
        eylem("conditional", GroupingIdentifier=kosul, WFControlFlowMode=2),
        eylem("notification", WFNotificationActionBody="Kaydedildi ✅", WFNotificationActionSound=False),
    )


def kestirme() -> dict:
    return {
        "WFWorkflowClientVersion": "2302.0.4",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": 4282601983, "WFWorkflowIconGlyphNumber": 61440},
        "WFWorkflowTypes": ["ActionExtension"],
        "WFWorkflowInputContentItemClasses": ["WFURLContentItem", "WFSafariWebPageContentItem", "WFStringContentItem"],
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowHasShortcutInputVariables": True,
        "WFWorkflowNoInputBehavior": {"Name": "WFWorkflowNoInputBehaviorGetClipboard", "Parameters": {}},
        "WFWorkflowImportQuestions": [
            {"ActionIndex": 0, "Category": "Parameter", "ParameterKey": "WFTextActionText",
             "DefaultValue": "http://", "Text": "Sunucu adresin (ör. http://evdeki-mac:8000, sonunda / olmadan)"},
            {"ActionIndex": 2, "Category": "Parameter", "ParameterKey": "WFTextActionText",
             "DefaultValue": "", "Text": "Sunucudaki API_KEY değeri"},
        ],
        "WFWorkflowActions": eylemler(),
    }


if __name__ == "__main__":
    hedef = sys.argv[1] if len(sys.argv) > 1 else "imzasiz.shortcut"
    with open(hedef, "wb") as dosya:
        plistlib.dump(kestirme(), dosya, fmt=plistlib.FMT_BINARY)
    print(f"Yazıldı: {hedef}")
