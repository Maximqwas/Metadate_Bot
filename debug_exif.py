"""
Тест: проверяем что именно piexif пишет в JPEG и читает ли iOS-совместимый ридер.
"""
import piexif
from PIL import Image
from datetime import datetime, timezone

# --- Создаём тестовое изображение ---
img = Image.new("RGB", (200, 200), color=(0, 128, 255))
img.save("test_out.jpg", format="JPEG", quality=95, subsampling=0)

# --- Строим EXIF ---
make  = "Apple"
model = "iPhone 17"
now   = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
now_utc = datetime.now(timezone.utc)

zeroth_ifd = {
    piexif.ImageIFD.Make:           make.encode("utf-8"),
    piexif.ImageIFD.Model:          model.encode("utf-8"),
    piexif.ImageIFD.DateTime:       now.encode("utf-8"),
    piexif.ImageIFD.Orientation:    1,
    piexif.ImageIFD.XResolution:    (72, 1),
    piexif.ImageIFD.YResolution:    (72, 1),
    piexif.ImageIFD.ResolutionUnit: 2,
}

gps_ifd = {
    piexif.GPSIFD.GPSVersionID:    b"\x02\x02\x00\x00",
    piexif.GPSIFD.GPSLatitudeRef:  b"N",
    piexif.GPSIFD.GPSLatitude:     ((63, 1), (25, 1), (13800000, 1000000)),
    piexif.GPSIFD.GPSLongitudeRef: b"E",
    piexif.GPSIFD.GPSLongitude:    ((10, 1), (23, 1), (42600000, 1000000)),
    piexif.GPSIFD.GPSAltitudeRef:  0,
    piexif.GPSIFD.GPSAltitude:     (0, 1),
    piexif.GPSIFD.GPSDateStamp:    now_utc.strftime("%Y:%m:%d").encode("utf-8"),
    piexif.GPSIFD.GPSTimeStamp:    (
        (now_utc.hour, 1), (now_utc.minute, 1), (now_utc.second, 1)
    ),
}

exif_ifd = {
    piexif.ExifIFD.DateTimeOriginal:  now.encode("utf-8"),
    piexif.ExifIFD.DateTimeDigitized: now.encode("utf-8"),
    piexif.ExifIFD.ColorSpace:        1,
    piexif.ExifIFD.PixelXDimension:   200,
    piexif.ExifIFD.PixelYDimension:   200,
    piexif.ExifIFD.FocalLength:       (26, 1),
    piexif.ExifIFD.FNumber:           (8, 5),
    piexif.ExifIFD.ISOSpeedRatings:   3200,
}

exif_dict  = {"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": gps_ifd, "1st": {}}

# --- dump ---
print("[1] Дампим exif_dict...")
try:
    exif_bytes = piexif.dump(exif_dict)
    print(f"    OK, длина: {len(exif_bytes)} байт")
    print(f"    Начало: {exif_bytes[:10]}")
except Exception as e:
    print(f"    ОШИБКА dump: {e}")
    raise

# --- insert ---
print("[2] Вставляем через piexif.insert()...")
try:
    piexif.insert(exif_bytes, "test_out.jpg")
    print("    OK")
except Exception as e:
    print(f"    ОШИБКА insert: {e}")
    raise

# --- читаем обратно ---
print("[3] Читаем обратно через piexif.load()...")
result = piexif.load("test_out.jpg")
zeroth = result.get("0th", {})
gps    = result.get("GPS", {})
exif   = result.get("Exif", {})

make_r  = zeroth.get(piexif.ImageIFD.Make, b"").decode(errors="ignore").strip("\x00")
model_r = zeroth.get(piexif.ImageIFD.Model, b"").decode(errors="ignore").strip("\x00")
lat     = gps.get(piexif.GPSIFD.GPSLatitude, None)
iso     = exif.get(piexif.ExifIFD.ISOSpeedRatings, None)

print(f"    Make  = {make_r!r}")
print(f"    Model = {model_r!r}")
print(f"    GPS Latitude = {lat}")
print(f"    ISO = {iso}")

if make_r == make and model_r == model:
    print("\n✅ EXIF записан и прочитан корректно!")
else:
    print("\n❌ Make/Model НЕ совпадают — проблема в записи!")

# --- проверка JFIF маркера ---
print("\n[4] Проверяем маркеры в JPEG...")
with open("test_out.jpg", "rb") as f:
    data = f.read(64)
    
print(f"    Первые байты: {data[:4].hex()}")
# FFD8 = SOI, FFE0 = APP0 (JFIF), FFE1 = APP1 (EXIF)
if data[2:4] == b"\xff\xe0":
    print("    ⚠️  APP0 (JFIF) идёт ДО EXIF — может конфликтовать с iOS!")
elif data[2:4] == b"\xff\xe1":
    print("    ✅ APP1 (EXIF) стоит первым — правильно!")
else:
    print(f"    Маркер: {data[2:4].hex()}")
