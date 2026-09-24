"""
bot/handlers.py
Telegram-хэндлеры с полноценным меню на inline-кнопках.
"""

import os
import uuid
from typing import Callable

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Document,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from engine.exif_worker import extract_full_camera_info, inject_metadata
from engine.geo_data import (
    DEFAULT_CITY,
    DEFAULT_COUNTRY,
    GEO_DATA,
    get_city,
    get_city_list,
    get_country_list,
)
from engine.video_worker import (
    MAX_DURATION_SEC,
    get_video_duration,
    inject_video_metadata,
)

# ---------------------------------------------------------------------------
# Дефолты и хранилище настроек (in-memory)
# ---------------------------------------------------------------------------

DEFAULT_MAKE  = "Apple"
DEFAULT_MODEL = "iPhone 15 Pro"

user_settings: dict[int, dict] = {}


def _get_user_settings(user_id: int) -> dict:
    """Возвращает настройки пользователя с дефолтными значениями."""
    if user_id not in user_settings:
        user_settings[user_id] = {
            "make":                 DEFAULT_MAKE,
            "model":                DEFAULT_MODEL,
            "country":              DEFAULT_COUNTRY,
            "city":                 DEFAULT_CITY,
            "camera_exif":          {},
            "awaiting_calibration": False,  # True = ждём донор-фото
        }
    return user_settings[user_id]


# ---------------------------------------------------------------------------
# Вспомогательные: текстовые блоки и клавиатуры
# ---------------------------------------------------------------------------

def _device_display(s: dict) -> str:
    return f"{s['make']} {s['model']}"


def _city_display(s: dict) -> str:
    city_data    = GEO_DATA[s["country"]]["cities"][s["city"]]
    country_data = GEO_DATA[s["country"]]
    return f"{country_data['flag']} {city_data['name']}"


def _text_main(s: dict) -> str:
    return (
        "🔧 <b>Метадата-бот</b>\n"
        "<i>Меняю метаданные фото и видео под iPhone.</i>\n\n"
        f"📱 Устройство: <b>{_device_display(s)}</b>\n"
        f"📍 Гео: <b>{_city_display(s)}</b>\n\n"
        "Выбери раздел ниже."
    )


def _kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼  Обработать фото/видео",  callback_data="menu:process")],
        [
            InlineKeyboardButton(text="👤 Профили",    callback_data="menu:profiles"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
        ],
        [InlineKeyboardButton(text="❓ Помощь",        callback_data="menu:help")],
    ])


def _kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu:main")],
    ])


def _kb_profiles(s: dict) -> InlineKeyboardMarkup:
    tags = len(s.get("camera_exif", {}))
    label = f"📷 Считать устройство с фото" + (f"  ({tags} тегов ✓)" if tags else "")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label,                          callback_data="profile:calibrate")],
        [InlineKeyboardButton(text="🔄 Сбросить устройство",       callback_data="profile:reset")],
        [InlineKeyboardButton(text="◀️ Назад",                     callback_data="menu:main")],
    ])


def _kb_settings() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Изменить геолокацию",       callback_data="settings:geo")],
        [InlineKeyboardButton(text="◀️ Назад",                     callback_data="menu:main")],
    ])


def _kb_country(back_cb: str = "menu:settings") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"{flag} {name}", callback_data=f"country:{key}")]
        for key, flag, name in get_country_list()
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _kb_city(country_key: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=city_name, callback_data=f"city:{country_key}:{city_key}")]
        for city_key, city_name in get_city_list(country_key)
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="geo_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------------------------------------------------------------------------
# Фабрика роутера
# ---------------------------------------------------------------------------

def create_router(
    temp_dir: str,
    logger: Callable[[str], None] | None = None,
) -> Router:
    if logger is None:
        logger = print
    os.makedirs(temp_dir, exist_ok=True)
    router = Router()

    # ───────────────────────────────────────────────────────────────────────
    # Команды
    # ───────────────────────────────────────────────────────────────────────

    @router.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        uid = message.from_user.id
        logger(f"[BOT] /start от user_id={uid}")
        await message.answer(
            _text_main(_get_user_settings(uid)),
            parse_mode="HTML",
            reply_markup=_kb_main(),
        )

    @router.message(Command("status"))
    async def cmd_status(message: Message) -> None:
        uid = message.from_user.id
        logger(f"[BOT] /status от user_id={uid}")
        await message.answer(
            _text_main(_get_user_settings(uid)),
            parse_mode="HTML",
            reply_markup=_kb_main(),
        )

    @router.message(Command("geo"))
    async def cmd_geo(message: Message) -> None:
        uid = message.from_user.id
        logger(f"[BOT] /geo от user_id={uid}")
        await message.answer(
            "🌍 <b>Выберите страну:</b>",
            parse_mode="HTML",
            reply_markup=_kb_country(),
        )

    # ───────────────────────────────────────────────────────────────────────
    # Главное меню
    # ───────────────────────────────────────────────────────────────────────

    @router.callback_query(F.data == "menu:main")
    async def cb_main(callback: CallbackQuery) -> None:
        uid = callback.from_user.id
        await callback.message.edit_text(
            _text_main(_get_user_settings(uid)),
            parse_mode="HTML",
            reply_markup=_kb_main(),
        )
        await callback.answer()

    # ───────────────────────────────────────────────────────────────────────
    # Раздел: Обработать фото/видео
    # ───────────────────────────────────────────────────────────────────────

    @router.callback_query(F.data == "menu:process")
    async def cb_process(callback: CallbackQuery) -> None:
        await callback.message.edit_text(
            "🖼 <b>Обработка фото и видео</b>\n\n"
            "Отправь файл прямо в этот чат — я подменю метаданные.\n\n"
            "<b>Поддерживаемые форматы:</b>\n"
            "• 🖼 Фото: <code>HEIC, JPEG, PNG, WEBP</code>\n"
            "• 🎬 Видео: <code>MP4, MOV</code>\n\n"
            "⚠️ Отправляй <b>как файл</b> (скрепка → Файл), не через галерею!\n\n"
            "Готовый файл придёт в формате <b>.heic</b> с метаданными под iPhone.",
            parse_mode="HTML",
            reply_markup=_kb_back(),
        )
        await callback.answer()

    # ───────────────────────────────────────────────────────────────────────
    # Раздел: Профили
    # ───────────────────────────────────────────────────────────────────────

    @router.callback_query(F.data == "menu:profiles")
    async def cb_profiles(callback: CallbackQuery) -> None:
        uid = callback.from_user.id
        s   = _get_user_settings(uid)
        tags = len(s.get("camera_exif", {}))
        await callback.message.edit_text(
            "👤 <b>Профили устройств</b>\n\n"
            f"📱 Устройство: <b>{_device_display(s)}</b>\n"
            f"🔧 Тегов камеры: <b>{tags}</b> "
            + ("(ISO, фокус, диафрагма...)" if tags else "(нет — отправь донорское фото)") + "\n\n"
            "Для смены устройства отправь <b>HEIC с нужного iPhone как файл</b>.\n"
            "Бот автоматически считает модель и все теги камеры.",
            parse_mode="HTML",
            reply_markup=_kb_profiles(s),
        )
        await callback.answer()

    @router.callback_query(F.data == "profile:calibrate")
    async def cb_calibrate(callback: CallbackQuery) -> None:
        uid = callback.from_user.id
        s   = _get_user_settings(uid)
        s["awaiting_calibration"] = True  # включаем режим калибровки
        logger(f"[BOT] user_id={uid} — режим калибровки активирован")
        await callback.message.edit_text(
            "📷 <b>Считывание устройства</b>\n\n"
            "Отправь <b>HEIC-фото с нужного iPhone как файл</b>.\n\n"
            "Бот считает:\n"
            "• Модель iPhone\n"
            "• Параметры камеры (фокус, диафрагма, ISO, выдержка)\n\n"
            "После этого все обрабатываемые фото получат эти метаданные.",
            parse_mode="HTML",
            reply_markup=_kb_back(),
        )
        await callback.answer()

    @router.callback_query(F.data == "profile:reset")
    async def cb_reset(callback: CallbackQuery) -> None:
        uid = callback.from_user.id
        s   = _get_user_settings(uid)
        s["make"]        = DEFAULT_MAKE
        s["model"]       = DEFAULT_MODEL
        s["camera_exif"] = {}
        logger(f"[BOT] user_id={uid} — устройство сброшено")
        await callback.message.edit_text(
            f"🔄 Устройство сброшено до <b>{DEFAULT_MAKE} {DEFAULT_MODEL}</b>.",
            parse_mode="HTML",
            reply_markup=_kb_back(),
        )
        await callback.answer("Устройство сброшено!")

    # ───────────────────────────────────────────────────────────────────────
    # Раздел: Настройки
    # ───────────────────────────────────────────────────────────────────────

    @router.callback_query(F.data == "menu:settings")
    async def cb_settings(callback: CallbackQuery) -> None:
        uid = callback.from_user.id
        s   = _get_user_settings(uid)
        city_data = GEO_DATA[s["country"]]["cities"][s["city"]]
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>\n\n"
            f"📍 Геолокация: <b>{_city_display(s)}</b>\n"
            f"🌐 Координаты: <code>{city_data['lat']}, {city_data['lon']}</code>",
            parse_mode="HTML",
            reply_markup=_kb_settings(),
        )
        await callback.answer()

    @router.callback_query(F.data == "settings:geo")
    async def cb_settings_geo(callback: CallbackQuery) -> None:
        await callback.message.edit_text(
            "🌍 <b>Выберите страну:</b>",
            parse_mode="HTML",
            reply_markup=_kb_country(back_cb="menu:settings"),
        )
        await callback.answer()

    # ───────────────────────────────────────────────────────────────────────
    # Раздел: Помощь
    # ───────────────────────────────────────────────────────────────────────

    @router.callback_query(F.data == "menu:help")
    async def cb_help(callback: CallbackQuery) -> None:
        await callback.message.edit_text(
            "❓ <b>Как пользоваться ботом</b>\n\n"
            "<b>1. Установи устройство</b>\n"
            "    👤 Профили → Считать устройство с фото\n"
            "    Отправь HEIC с нужного iPhone как файл\n\n"
            "<b>2. Выбери геолокацию</b>\n"
            "    ⚙️ Настройки → Изменить геолокацию\n"
            "    Выбери страну и город\n\n"
            "<b>3. Отправь файл для обработки</b>\n"
            "    Фото или видео <b>как файл</b> (скрепка → Файл)\n"
            "    Получишь файл с подменёнными метаданными\n\n"
            "<b>Команды:</b>\n"
            "• /start — главное меню\n"
            "• /geo — смена геолокации\n"
            "• /status — текущие настройки",
            parse_mode="HTML",
            reply_markup=_kb_back(),
        )
        await callback.answer()

    # ───────────────────────────────────────────────────────────────────────
    # Выбор геолокации: страна → город
    # ───────────────────────────────────────────────────────────────────────

    @router.callback_query(F.data.startswith("country:"))
    async def cb_country(callback: CallbackQuery) -> None:
        country_key = callback.data.split(":", 1)[1]
        country     = GEO_DATA.get(country_key)
        if country is None:
            await callback.answer("Страна не найдена.", show_alert=True)
            return
        await callback.message.edit_text(
            f"{country['flag']} <b>{country['name']} — выберите город:</b>",
            parse_mode="HTML",
            reply_markup=_kb_city(country_key),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("city:"))
    async def cb_city(callback: CallbackQuery) -> None:
        _, country_key, city_key = callback.data.split(":", 2)
        city_data = get_city(country_key, city_key)
        if city_data is None:
            await callback.answer("Город не найден.", show_alert=True)
            return

        uid      = callback.from_user.id
        settings = _get_user_settings(uid)
        settings["country"] = country_key
        settings["city"]    = city_key
        country_data        = GEO_DATA[country_key]
        logger(f"[BOT] user_id={uid} выбрал город: {city_data['name']}")

        await callback.message.edit_text(
            f"✅ <b>Геолокация установлена:</b>\n\n"
            f"{country_data['flag']} <b>{country_data['name']}</b> — "
            f"<b>{city_data['name']}</b>\n"
            f"🌐 Координаты: <code>{city_data['lat']}, {city_data['lon']}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu:main")],
            ]),
        )
        await callback.answer("Город сохранён!")

    @router.callback_query(F.data == "geo_back")
    async def cb_geo_back(callback: CallbackQuery) -> None:
        await callback.answer()
        await callback.message.edit_text(
            "🌍 <b>Выберите страну:</b>",
            parse_mode="HTML",
            reply_markup=_kb_country(back_cb="menu:settings"),
        )

    # ───────────────────────────────────────────────────────────────────────
    # Обработка документов (фото и видео)
    # ───────────────────────────────────────────────────────────────────────

    @router.message(F.document)
    async def handle_document(message: Message, bot: Bot) -> None:
        uid           = message.from_user.id
        doc: Document = message.document
        mime          = doc.mime_type or ""
        original_name = doc.file_name or "file"

        logger(f"[BOT] Документ от user_id={uid}: {original_name} [{mime}]")

        is_image = mime in (
            "image/jpeg", "image/jpg", "image/png", "image/webp",
            "image/heic", "image/heif",
        )
        is_video = mime in ("video/mp4", "video/quicktime", "video/x-msvideo")

        if not is_image and not is_video:
            await message.reply(
                "⚠️ Поддерживаются только файлы:\n"
                "🖼 <b>Изображения:</b> HEIC, JPEG, PNG, WEBP\n"
                "🎬 <b>Видео:</b> MP4, MOV",
                parse_mode="HTML",
            )
            return

        settings    = _get_user_settings(uid)
        make        = settings["make"]
        model       = settings["model"]
        country_key = settings["country"]
        city_key    = settings["city"]
        city_data   = GEO_DATA[country_key]["cities"][city_key]

        uid_str    = str(uuid.uuid4())[:8]
        ext        = os.path.splitext(original_name)[1].lower() or (
            ".jpg" if is_image else ".mp4"
        )
        input_tmp  = os.path.join(temp_dir, f"in_{uid_str}{ext}")
        output_ext = ".heic" if is_image else ext
        output_tmp = os.path.join(temp_dir, f"out_{uid_str}{output_ext}")

        status_msg = await message.reply("⏳ Обрабатываю файл...", parse_mode="HTML")

        try:
            # Скачиваем файл
            await bot.download(doc, destination=input_tmp)
            logger(f"[BOT] Файл скачан: {input_tmp}")

            # ── Фото ──────────────────────────────────────────────────────
            if is_image:
                # Калибровка ТОЛЬКО если пользователь явно нажал «Считать устройство»
                if settings.get("awaiting_calibration"):
                    device = extract_full_camera_info(input_tmp)
                    settings["awaiting_calibration"] = False  # сбрасываем флаг
                    if device is not None:
                        extracted_make, extracted_model, extracted_exif = device
                        settings["make"]        = extracted_make
                        settings["model"]       = extracted_model
                        settings["camera_exif"] = extracted_exif
                        logger(
                            f"[BOT] user_id={uid} — донор: "
                            f"{extracted_make} {extracted_model}, "
                            f"тегов: {len(extracted_exif)}"
                        )
                        await status_msg.edit_text(
                            f"✅ <b>Устройство считано и зафиксировано:</b>\n"
                            f"📱 <b>{extracted_make} {extracted_model}</b>\n"
                            f"🔧 Тегов камеры: <b>{len(extracted_exif)}</b>\n\n"
                            "Теперь отправь файл для обработки.",
                            parse_mode="HTML",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(
                                    text="◀️ Главное меню",
                                    callback_data="menu:main",
                                )],
                            ]),
                        )
                    else:
                        await status_msg.edit_text(
                            "⚠️ <b>EXIF не найден.</b>\n"
                            "Убедись, что отправляешь оригинальное фото с iPhone (не скриншот).",
                            parse_mode="HTML",
                            reply_markup=_kb_back(),
                        )
                    return

                inject_metadata(
                    input_path=input_tmp,
                    output_path=output_tmp,
                    lat=city_data["lat"],
                    lon=city_data["lon"],
                    make=make,
                    model=model,
                    camera_exif=settings.get("camera_exif"),
                    logger=logger,
                )

                caption = (
                    f"✅ <b>Готово!</b>\n"
                    f"📍 {GEO_DATA[country_key]['flag']} "
                    f"<b>{city_data['name']}</b> "
                    f"(<code>{city_data['lat']}, {city_data['lon']}</code>)\n"
                    f"📱 <b>{make} {model}</b>"
                )
                await message.reply_document(
                    document=FSInputFile(output_tmp),
                    caption=caption,
                    parse_mode="HTML",
                )
                await status_msg.delete()
                logger(f"[BOT] Изображение отправлено user_id={uid}")

            # ── Видео ──────────────────────────────────────────────────────
            elif is_video:
                duration = await get_video_duration(input_tmp, logger=logger)
                if duration > MAX_DURATION_SEC:
                    await status_msg.edit_text(
                        f"❌ <b>Видео слишком длинное ({duration:.1f} сек).</b>\n"
                        f"Лимит: до {int(MAX_DURATION_SEC)} секунд.",
                        parse_mode="HTML",
                    )
                    logger(f"[BOT] user_id={uid} — видео отклонено: {duration:.1f} сек")
                    return

                await inject_video_metadata(
                    input_path=input_tmp,
                    output_path=output_tmp,
                    iso6709=city_data["iso6709"],
                    make=make,
                    model=model,
                    logger=logger,
                )
                caption = (
                    f"✅ <b>Готово!</b>\n"
                    f"📍 {GEO_DATA[country_key]['flag']} "
                    f"<b>{city_data['name']}</b> "
                    f"(<code>{city_data['lat']}, {city_data['lon']}</code>)\n"
                    f"📱 <b>{make} {model}</b>"
                )
                await message.reply_document(
                    document=FSInputFile(output_tmp),
                    caption=caption,
                    parse_mode="HTML",
                )
                await status_msg.delete()
                logger(f"[BOT] Видео отправлено user_id={uid}")

        except Exception as exc:
            logger(f"[BOT] ОШИБКА для user_id={uid}: {exc}")
            await status_msg.edit_text(
                f"❌ <b>Ошибка при обработке:</b>\n<code>{exc}</code>",
                parse_mode="HTML",
            )

        finally:
            for tmp in (input_tmp, output_tmp):
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except OSError:
                    pass

    return router


def register_handlers(
    dp: Dispatcher,
    temp_dir: str,
    logger: Callable[[str], None] | None = None,
) -> None:
    """Регистрирует все хэндлеры в диспетчере."""
    router = create_router(temp_dir=temp_dir, logger=logger)
    dp.include_router(router)
