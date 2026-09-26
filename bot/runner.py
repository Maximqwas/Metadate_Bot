import asyncio
import os
import threading
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from bot.handlers import register_handlers

class BotRunner:
    def __init__(self, token: str, temp_dir: str, logger_callback, local_api_server: str = None):
        self.token = token
        self.temp_dir = temp_dir
        self.logger_callback = logger_callback
        self.local_api_server = local_api_server
        
        self.bot = None
        self.dp = None
        self._loop = None
        self._thread = None
        self.is_running = False

    def _run_bot(self):
        """Эта функция выполняется в отдельном потоке (Thread)"""
        # Создаем новый event_loop для этого потока
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        session = None
        if self.local_api_server:
            session = AiohttpSession(api=TelegramAPIServer.from_base(self.local_api_server))
            
        self.bot = Bot(token=self.token, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self.dp = Dispatcher()
        
        register_handlers(dp=self.dp, temp_dir=self.temp_dir, logger=self.logger_callback)
        
        self.logger_callback("[SYSTEM] Запуск Telegram-бота...")
        try:
            self._loop.run_until_complete(
                self.dp.start_polling(self.bot, allowed_updates=["message", "callback_query"])
            )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger_callback(f"[ERROR] Ошибка бота: {e}")
        finally:
            self.logger_callback("[SYSTEM] Закрытие сессии бота...")
            self._loop.run_until_complete(self.bot.session.close())
            self._loop.close()
            self.is_running = False
            self.logger_callback("[SYSTEM] Бот полностью остановлен.")

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run_bot, daemon=True)
        self._thread.start()

    def stop(self):
        if not self.is_running or self._loop is None:
            return
        self.logger_callback("[SYSTEM] Отправка сигнала на остановку бота...")
        # Безопасно завершаем polling из другого потока
        asyncio.run_coroutine_threadsafe(self.dp.stop_polling(), self._loop)
