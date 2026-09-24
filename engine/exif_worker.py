"""
engine/exif_worker.py
Модуль для работы с EXIF-метаданными фотографий.
Не зависит от Telegram, UI или других модулей проекта.
"""

import math
import os
from datetime import datetime, timezone
from typing import Callable

import piexif
import pillow_heif
from PIL import Image

# Регистрируем HEIC/HEIF плагин в Pillow
pillow_heif.register_heif_opener()


# ---------------------------------------------------------------------------
# Теги ExifIFD, которые копируются с донора (отображаются в iOS «Фото»)
# ---------------------------------------------------------------------------

_EXIF_COPY_TAGS = (
    piexif.ExifIFD.FocalLength,            # Фокусное расстояние (мм)
    piexif.ExifIFD.FNumber,                # Диафрагма (f/...)
    piexif.ExifIFD.ISOSpeedRatings,        # ISO
    piexif.ExifIFD.ExposureTime,           # Выдержка
    piexif.ExifIFD.ExposureBiasValue,      # EV компенсация
    piexif.ExifIFD.ExposureMode,           # Режим экспозиции
    piexif.ExifIFD.MeteringMode,           # Замер
    piexif.ExifIFD.Flash,                  # Вспышка
    piexif.ExifIFD.FocalLengthIn35mmFilm,  # Эквивалент 35 мм
    piexif.ExifIFD.LensModel,              # Модель объектива
    piexif.ExifIFD.WhiteBalance,           # Баланс белого
    piexif.ExifIFD.SceneCaptureType,       # Тип сцены
    piexif.ExifIFD.BrightnessValue,        # Яркость
    piexif.ExifIFD.ApertureValue,          # APEX диафрагма
    piexif.ExifIFD.ShutterSpeedValue,      # APEX выдержка
    piexif.ExifIFD.SensingMethod,          # Тип сенсора
)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _to_rational(value: float) -> tuple[int, int]:
    """Конвертирует float в рациональную дробь (числитель, знаменатель)."""
    denominator = 1_000_000
    return (round(abs(value) * denominator), denominator)


def _decimal_to_dms(
    decimal: float,
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    """
    Конвертирует десятичные градусы в формат DMS (Degrees, Minutes, Seconds).
    Возвращает кортеж из трёх рациональных дробей для EXIF.
    """
    decimal = abs(decimal)
    degrees = int(decimal)
    minutes_full = (decimal - degrees) * 60
    minutes = int(minutes_full)
    seconds = (minutes_full - minutes) * 60
    return (
        (degrees, 1),
        (minutes, 1),
        _to_rational(seconds),
    )


def _piexif_from_heic(image_path: str) -> dict | None:
    """Загружает EXIF из HEIC-файла через pillow_heif → piexif."""
    try:
        heif_file = pillow_heif.open_heif(image_path)
        raw_exif = heif_file.info.get("exif")
        if raw_exif:
            return piexif.load(raw_exif)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Основные публичные функции
# ---------------------------------------------------------------------------

def extract_full_camera_info(
    image_path: str,
) -> tuple[str, str, dict] | None:
    """
    Считывает Make, Model и все теги камеры из EXIF донора.
    Поддерживает JPEG (piexif) и HEIC/HEIF (pillow_heif + piexif).

    Returns:
        (make, model, camera_exif_ifd) или None, если Make/Model не найдены.
    """
    make: str | None = None
    model: str | None = None
    camera_exif: dict = {}

    def _parse(exif_data: dict) -> None:
        nonlocal make, model
        zeroth   = exif_data.get("0th", {})
        exif_ifd = exif_data.get("Exif", {})

        make_b  = zeroth.get(piexif.ImageIFD.Make)
        model_b = zeroth.get(piexif.ImageIFD.Model)
        if make_b and model_b:
            make  = make_b.decode("utf-8",  errors="ignore").strip("\x00").strip()
            model = model_b.decode("utf-8", errors="ignore").strip("\x00").strip()

        for tag in _EXIF_COPY_TAGS:
            if tag in exif_ifd:
                camera_exif[tag] = exif_ifd[tag]

    # --- Попытка 1: piexif (JPEG/PNG/WEBP) ---
    try:
        _parse(piexif.load(image_path))
    except Exception:
        pass

    # --- Попытка 2: pillow_heif → piexif (HEIC/HEIF) ---
    if not make or not model:
        exif_data = _piexif_from_heic(image_path)
        if exif_data:
            try:
                _parse(exif_data)
            except Exception:
                pass

    # --- Попытка 3: PIL.getexif() (запасной вариант) ---
    if not make or not model:
        try:
            img  = Image.open(image_path)
            exif = img.getexif()
            make  = exif.get(0x010F, "").strip("\x00").strip() or make
            model = exif.get(0x0110, "").strip("\x00").strip() or model
        except Exception:
            pass

    if not make or not model:
        return None

    return (make, model, camera_exif)


def extract_device_info(image_path: str) -> tuple[str, str] | None:
    """Обратная совместимость: возвращает только (make, model)."""
    result = extract_full_camera_info(image_path)
    return (result[0], result[1]) if result else None


def inject_metadata(
    input_path: str,
    output_path: str,
    lat: float,
    lon: float,
    make: str,
    model: str,
    camera_exif: dict | None = None,
    logger: Callable[[str], None] | None = None,
) -> str:
    """
    Инжектирует GPS-координаты, данные устройства и теги камеры в изображение.

    Поддерживаемые форматы входного файла: JPEG, PNG, WEBP, HEIC/HEIF.
    Результат сохраняется как HEIC с сохранением оригинального разрешения.

    Args:
        input_path:   Путь к исходному файлу.
        output_path:  Путь для сохранения результата (.heic).
        lat:          Широта в десятичных градусах.
        lon:          Долгота в десятичных градусах.
        make:         Производитель (например, «Apple»).
        model:        Модель (например, «iPhone 17»).
        camera_exif:  Теги ExifIFD с донора (фокус, диафрагма, ISO и т.д.).
        logger:       Коллбэк для логирования.

    Returns:
        Путь к сохранённому файлу.
    """
    if logger is None:
        logger = lambda msg: None  # noqa: E731

    logger(f"[EXIF] Открываю файл: {os.path.basename(input_path)}")

    ext = os.path.splitext(input_path)[1].lower()
    if ext in (".heic", ".heif"):
        # Для HEIC используем прямой API — гарантирует первичное изображение полного разрешения
        _heif   = pillow_heif.open_heif(input_path, convert_hdr_to_8bit=True)
        _src    = _heif.to_pillow()
        src_dpi = _src.info.get("dpi", (72, 72))
    else:
        _src    = Image.open(input_path)
        src_dpi = _src.info.get("dpi", (72, 72))

    dpi_x = int(round(src_dpi[0])) or 72
    dpi_y = int(round(src_dpi[1])) or 72
    image = _src.convert("RGB")
    logger(f"[EXIF] Размер входного файла: {image.width}x{image.height}")

    # Масштабирование до 10MP (~10 000 000 пикселей)
    target_pixels = 10_000_000
    current_pixels = image.width * image.height
    if current_pixels > 0 and current_pixels != target_pixels:
        scale_factor = math.sqrt(target_pixels / current_pixels)
        new_w = int(round(image.width * scale_factor))
        new_h = int(round(image.height * scale_factor))
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        logger(f"[EXIF] Изображение масштабировано до 10MP: {new_w}x{new_h}")

    # --- GPS-блок (полный, для iOS) ---
    lat_dms  = _decimal_to_dms(lat)
    lon_dms  = _decimal_to_dms(lon)
    lat_ref  = b"N" if lat >= 0 else b"S"
    lon_ref  = b"E" if lon >= 0 else b"W"

    now_utc  = datetime.now(timezone.utc)
    gps_date = now_utc.strftime("%Y:%m:%d").encode("utf-8")
    gps_time = (
        (now_utc.hour,   1),
        (now_utc.minute, 1),
        (now_utc.second, 1),
    )

    gps_ifd = {
        piexif.GPSIFD.GPSVersionID:    b"\x02\x02\x00\x00",  # EXIF GPS v2.2
        piexif.GPSIFD.GPSLatitudeRef:  lat_ref,
        piexif.GPSIFD.GPSLatitude:     lat_dms,
        piexif.GPSIFD.GPSLongitudeRef: lon_ref,
        piexif.GPSIFD.GPSLongitude:    lon_dms,
        piexif.GPSIFD.GPSAltitudeRef:  0,       # 0 = над уровнем моря
        piexif.GPSIFD.GPSAltitude:     (0, 1),  # нейтральное значение
        piexif.GPSIFD.GPSTimeStamp:    gps_time,
        piexif.GPSIFD.GPSDateStamp:    gps_date,
    }

    # --- Основной IFD (0th) ---
    now_str = datetime.now().strftime("%Y:%m:%d %H:%M:%S")

    zeroth_ifd = {
        piexif.ImageIFD.Make:           make.encode("utf-8"),
        piexif.ImageIFD.Model:          model.encode("utf-8"),
        piexif.ImageIFD.DateTime:       now_str.encode("utf-8"),
        piexif.ImageIFD.Software:       b"Camera",
        piexif.ImageIFD.Orientation:    1,
        piexif.ImageIFD.XResolution:    (dpi_x, 1),
        piexif.ImageIFD.YResolution:    (dpi_y, 1),
        piexif.ImageIFD.ResolutionUnit: 2,  # дюймы
    }

    # --- ExifIFD: базовые теги + теги камеры с донора ---
    exif_ifd: dict = {
        piexif.ExifIFD.DateTimeOriginal:  now_str.encode("utf-8"),
        piexif.ExifIFD.DateTimeDigitized: now_str.encode("utf-8"),
        piexif.ExifIFD.ColorSpace:        1,              # sRGB
        piexif.ExifIFD.PixelXDimension:   image.width,
        piexif.ExifIFD.PixelYDimension:   image.height,
    }

    # Копируем теги камеры с донора (ISO, фокус, диафрагма и т.д.)
    if camera_exif:
        for tag, value in camera_exif.items():
            exif_ifd[tag] = value

    exif_dict = {
        "0th":  zeroth_ifd,
        "Exif": exif_ifd,
        "GPS":  gps_ifd,
        "1st":  {},
    }

    exif_bytes = piexif.dump(exif_dict)

    logger(f"[EXIF] Записываю метаданные: Make={make}, Model={model}, "
           f"lat={lat:.4f}, lon={lon:.4f}")

    # Сохраняем как HEIC — iOS Photos корректно читает все теги из HEIC
    # pillow_heif принимает exif= как raw bytes (формат piexif.dump())
    # Убираем префикс "Exif\x00\x00" если он есть — HEIC контейнер не нуждается в нём
    _EXIF_HEADER = b"Exif\x00\x00"
    heif_exif = exif_bytes[len(_EXIF_HEADER):] if exif_bytes.startswith(_EXIF_HEADER) else exif_bytes
    image.save(output_path, format="HEIF", quality=100, exif=heif_exif)

    # Проверяем что размер не изменился
    out_check = Image.open(output_path)
    logger(f"[EXIF] Размер выходного файла: {out_check.width}x{out_check.height} "
           f"(вход: {image.width}x{image.height})")
    if out_check.size != image.size:
        logger(f"[EXIF] ВНИМАНИЕ: размер изменился! "
               f"{image.width}x{image.height} -> {out_check.width}x{out_check.height}")

    logger(f"[EXIF] Файл сохранён: {os.path.basename(output_path)}")
    return output_path

