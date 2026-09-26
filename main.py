"""
main.py
Точка входа для v1.0 (CLI-режим).
Читает токен из bot_config.json и запускает polling.
"""

import asyncio
import json
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

from bot.handlers import register_handlers

# ---------------------------------------------------------------------------
# Настройка логирования
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# Дополнительно подавляем избыточные логи aiogram
logging.getLogger("aiogram").setLevel(logging.WARNING)


def load_config() -> dict:
    """
    Читает конфигурацию из bot_config.json.
    Файл должен содержать {"token": "YOUR_BOT_TOKEN", "local_api_server": "http://localhost:8081"}

    Raises:
        SystemExit: Если файл не найден или токен отсутствует.
    """
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_config.json")

    if not os.path.isfile(config_path):
        print(
            f"[ERROR] Файл конфигурации не найден: {config_path}\n"
            f"Создайте файл bot_config.json с содержимым:\n"
            f'{{"token": "YOUR_TELEGRAM_BOT_TOKEN"}}'
        )
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as exc:
            print(f"[ERROR] Ошибка разбора bot_config.json: {exc}")
            sys.exit(1)

    token = config.get("token", "").strip()
    if not token:
        print("[ERROR] Поле 'token' в bot_config.json пустое или отсутствует.")
        sys.exit(1)

    return config


async def main() -> None:
    """Основная функция запуска бота."""
    config = load_config()
    token = config.get("token")
    local_api_server = config.get("local_api_server")

    # Директория для временных файлов
    base_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(base_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    session = None
    if local_api_server:
        session = AiohttpSession(api=TelegramAPIServer.from_base(local_api_server))

    bot = Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Регистрируем хэндлеры с логированием через стандартный logging
    register_handlers(
        dp=dp,
        temp_dir=temp_dir,
        logger=lambda msg: logging.info(msg),
    )

    print("=" * 50)
    print("  Telegram Metadata Bot v1.0 запущен")
    print("  Нажмите Ctrl+C для остановки")
    print("=" * 50)

    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await bot.session.close()
        print("\n[INFO] Бот остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
