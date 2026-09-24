"""
engine/video_worker.py
Модуль для работы с видеофайлами через ffprobe и ffmpeg.
Не зависит от Telegram, UI или других модулей проекта.
Все вызовы внешних утилит — асинхронные (asyncio.create_subprocess_exec).
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Callable


# Максимально допустимая длительность видео в секундах
MAX_DURATION_SEC: float = 16.0


def _get_ffmpeg_path() -> tuple[str, str]:
    """
    Возвращает пути к ffmpeg и ffprobe.
    В замороженном (PyInstaller) окружении — рядом с .exe,
    иначе — ожидает наличия в PATH.
    """
    import sys

    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    ffmpeg_candidate = os.path.join(base, "ffmpeg.exe")
    ffprobe_candidate = os.path.join(base, "ffprobe.exe")

    ffmpeg = ffmpeg_candidate if os.path.isfile(ffmpeg_candidate) else "ffmpeg"
    ffprobe = ffprobe_candidate if os.path.isfile(ffprobe_candidate) else "ffprobe"

    return ffmpeg, ffprobe


async def get_video_duration(
    video_path: str,
    logger: Callable[[str], None] | None = None,
) -> float:
    """
    Определяет длительность видео с помощью ffprobe.

    Args:
        video_path: Путь к видеофайлу.
        logger:     Опциональный коллбэк для логирования.

    Returns:
        Длительность в секундах (float).

    Raises:
        RuntimeError: Если ffprobe вернул ошибку или не удалось прочитать данные.
    """
    if logger is None:
        logger = lambda msg: None  # noqa: E731

    _, ffprobe = _get_ffmpeg_path()

    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        video_path,
    ]

    logger(f"[VIDEO] Проверяю длительность: {os.path.basename(video_path)}")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffprobe завершился с ошибкой: {err}")

    try:
        info = json.loads(stdout.decode("utf-8"))
        duration = float(info["format"]["duration"])
        logger(f"[VIDEO] Длительность: {duration:.2f} сек")
        return duration
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Не удалось разобрать вывод ffprobe: {exc}") from exc


async def inject_video_metadata(
    input_path: str,
    output_path: str,
    iso6709: str,
    make: str,
    model: str,
    logger: Callable[[str], None] | None = None,
) -> str:
    """
    Инжектирует метаданные в видеофайл через ffmpeg (stream copy, без перекодирования).

    Args:
        input_path:  Путь к исходному видеофайлу.
        output_path: Путь для сохранения результата.
        iso6709:     Строка координат в формате ISO 6709, например "+63.4305+010.3951/".
        make:        Производитель устройства.
        model:       Модель устройства.
        logger:      Опциональный коллбэк для логирования.

    Returns:
        Путь к сохранённому файлу (output_path).

    Raises:
        RuntimeError: Если ffmpeg вернул ошибку.
    """
    if logger is None:
        logger = lambda msg: None  # noqa: E731

    ffmpeg, _ = _get_ffmpeg_path()

    creation_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000000Z")

    cmd = [
        ffmpeg,
        "-y",                       # Перезапись выходного файла без подтверждения
        "-i", input_path,
        "-map_metadata", "-1",      # Очистка всех старых метаданных контейнера
        "-metadata", f"location={iso6709}",
        "-metadata", f"location-eng={iso6709}",
        "-metadata", f"make={make}",
        "-metadata", f"model={model}",
        "-metadata", f"creation_time={creation_time}",
        "-c:v", "copy",             # Без перекодирования видео
        "-c:a", "copy",             # Без перекодирования аудио
        output_path,
    ]

    logger(f"[VIDEO] Инжектирую метаданные: location={iso6709}, "
           f"make={make}, model={model}")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg завершился с ошибкой (код {proc.returncode}): {err}")

    logger(f"[VIDEO] Файл сохранён: {os.path.basename(output_path)}")
    return output_path
