from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, Message
from aiogram.utils.formatting import Bold, Text

from app.database.db import db
from app.keyboards.user import main_menu, match_menu, player_menu
from app.services.opendota import opendota_client
from app.states.user import RegistrationStates, SettingsStates, NavigationStates
from app.utils.formatters import format_match_details
from app.utils.steam import (
    extract_steam_id_from_url,
    resolve_vanity_url,
    steam64_to_steam32,
    validate_steam_id,
)
from config.logger import logger

router = Router()


async def render_profile_message(message: Message, steam_id32: str, show_back: bool = False) -> None:
    stats_data = await opendota_client.get_formatted_player_stats(steam_id32)
    profile_text = Text(
        Bold("📊 Статистика игрока"),
        "\n\n",
        Bold("🆔 Steam ID:"),
        " ",
        Code(steam_id32),
        "\n\n",
        stats_data["text"],
    ).as_html()

    reply_markup = None
    if stats_data.get("profile_found"):
        reply_markup = player_menu(steam_id32, show_back=show_back)

    if stats_data["avatar_url"]:
        await message.answer_photo(
            photo=stats_data["avatar_url"],
            caption=profile_text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    else:
        await message.answer(
            profile_text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )


@router.message(Command("match"))
async def handle_match_command(message: Message) -> None:
    match_id = message.text.split()[1] if len(message.text.split()) > 1 else None

    if not match_id:
        await message.answer(
            "❌ Укажи ID матча после команды.\n\n📝 <b>Пример:</b>\n<code>/match 123456789</code>",
            parse_mode="HTML",
        )
        return

    try:
        match_id_int = int(match_id)
    except ValueError:
        await message.answer(
            "❌ ID матча должен быть числом.\n\n📝 <b>Пример:</b>\n<code>/match 123456789</code>",
            parse_mode="HTML",
        )
        return

    loading_msg = await message.answer("🔄 Загружаю информацию о матче...")

    await state.set_state(NavigationStates.viewing_match)
    await state.update_data(match_id=match_id_int)

    try:
        match_url = f"https://api.opendota.com/api/matches/{match_id_int}"

        session = await opendota_client.get_session()
        async with session.get(match_url) as response:
            if response.status == 200:
                match_data = await response.json()

                # Формируем детальную информацию о матче
                match_text = format_match_details(match_data)

                # Конвертируем Text объект в строку HTML
                match_html = (
                    match_text.as_html()
                    if hasattr(match_text, "as_html")
                    else str(match_text)
                )

                await loading_msg.edit_text(match_html, parse_mode="HTML", reply_markup=match_menu(str(match_id_int)))

            elif response.status == 404:
                await loading_msg.edit_text(
                    "❌ Матч не найден.\n\n"
                    "🔍 Убедись, что ID матча правильный и матч публичный."
                )
            else:
                await loading_msg.edit_text(
                    f"❌ Ошибка API: {response.status}\n\nПопробуй позже."
                )

    except Exception as e:
        logger.error(f"Ошибка получения матча {match_id}: {e}")
        await loading_msg.edit_text(
            "❌ Произошла ошибка при загрузке матча.\n\nПопробуй позже."
        )


@router.message(Command("player"))
async def handle_player_command(message: Message) -> None:
    account_id = message.text.split()[1] if len(message.text.split()) > 1 else None

    if not account_input:
        await message.answer(
            "❌ Укажи ID аккаунта после команды.\n\n"
            "📝 <b>Примеры:</b>\n"
            "<code>/player 123456789</code> (Steam ID32)\n"
            "<code>/player 76561198012345678</code> (Steam ID64)",
            parse_mode="HTML",
        )
        return

    if not validate_steam_id(account_id):
        await message.answer(
            "❌ Неверный формат ID аккаунта.\n\n"
            "📝 <b>Примеры:</b>\n"
            "<code>/player 123456789</code> (Steam ID32)\n"
            "<code>/player 76561198012345678</code> (Steam ID64)",
            parse_mode="HTML",
        )
        return

    if len(account_id) >= 17:
        try:
            account_id = steam64_to_steam32(account_id)
        except ValueError:
            await message.answer(
                "❌ Ошибка конвертации Steam ID64.\n\n"
                "Проверь правильность ID и попробуй снова."
            )
            return

    loading_msg = await message.answer("🔄 Загружаю статистику игрока...")

    try:
        stats_data = await opendota_client.get_formatted_player_stats(account_id)

        await loading_msg.delete()

        if "❌" in str(stats_data["text"]) or "🚷" in str(stats_data["text"]):
            await message.answer(str(stats_data["text"]))
        else:
            prev_state = await state.get_state()
            prev_data = await state.get_data()
            if prev_state:
                await state.update_data(
                    previous_view=prev_state,
                    previous_account_id=prev_data.get("account_id"),
                    previous_page=prev_data.get("current_page"),
                )
            await state.set_state(NavigationStates.viewing_profile)
            await state.update_data(account_id=account_id)

            full_text = Text(
                Bold("📊 Статистика игрока"),
                "\n",
                f"🆔 Steam ID32: {account_id}\n\n",
                stats_data["text"],
            )

            if stats_data["avatar_url"]:
                await message.answer_photo(
                    photo=stats_data["avatar_url"],
                    caption=full_text.as_html(),
                    parse_mode="HTML",
                    reply_markup=player_menu(account_id)
                )
            else:
                await message.answer(
                    full_text.as_html(), 
                    parse_mode="HTML",
                    reply_markup=player_menu(account_id)
                )

    except Exception as e:
        logger.error(f"Ошибка получения статистики игрока {account_id}: {e}")
        await loading_msg.edit_text(
            "❌ Произошла ошибка при загрузке статистики.\n\nПопробуй позже."
        )


@router.message(Command("settings"))
async def handle_settings_command(message: Message) -> None:
    await message.answer(
        Text(
            Bold("⚙️ Настройки профиля:"),
            "\n\n",
            "Здесь ты можешь изменить свой Steam ID или отвязать аккаунт.",
        ).as_html(),
        parse_mode="HTML",
        reply_markup=settings_menu(),
    )


@router.message(Command("help"))
async def handle_help_command(message: Message) -> None:
    help_text = (
        "📖 <b>Справка по боту</b>\n\n"
        "🎮 <b>Основные команды:</b>\n"
        "<code>/start</code> - Регистрация и показ профиля\n"
        "<code>/help</code> - Показать это сообщение\n\n"
        "🔍 <b>Команды поиска:</b>\n"
        "<code>/me</code>; - Показать свой профиль\n"
        "<code>/match match_id</code>; - Информация о матче\n"
        "<code>/player account_id</code>; - Статистика игрока\n"
        "<code>/settings</code>; - Открыть настройки\n\n"
        "💡<b>Частые вопросы:</b>\n"
        "• ID матча можно найти в истории игр Dota 2\n"
        "• Account ID (Steam ID32/64) можно найти в профиле Steam\n"
        "• Все данные загружаются из OpenDota API"
    )

    await message.answer(help_text, parse_mode="HTML")


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    tg_id = message.from_user.id

    try:
        # Проверяем, есть ли пользователь в базе
        user_data = await db.get_user(tg_id)

        if user_data:
            # Пользователь уже зарегистрирован
            await state.clear()
            await message.answer(
                f"👋 С возвращением, {message.from_user.first_name}!"
            )
            await render_profile_message(message, user_data['steam_id32'])

        else:
            await message.answer(
                "👋 Привет! Я <b>DotaBot</b> - твой персональный помощник по статистике Dota 2.\n\n"
                "Для начала работы мне нужен твой <b>Steam ID</b> или <b>ссылка на твой профиль.</b>\n\n"
                "📝 Как получить <b>Steam ID</b>:\n"
                "1. Открой сайт https://steamid.io/\n"
                "2. Введи ссылку на свой профиль\n"
                "3. Скопируй <b>Steam ID32</b> либо <b>Steam ID64</b>\n"
                "🔗 <b>Примеры:</b>\n"
                "• <code>123456789</code> <b>(Steam ID32)</b>\n"
                "• <code>76561198801039962</code> <b>(Steam ID64)</b>\n"
                "• <code>https://steamcommunity.com/profiles/76561198012345678</code> <b>(Steam ID64 URL)</b>\n"
                "• <code>https://steamcommunity.com/id/vanityname</code> <b>(Steam Vanity URL)</b>\n\n",
                parse_mode="HTML",
            )

            # Устанавливаем состояние ожидания Steam ID
            await state.set_state(RegistrationStates.waiting_steam_id)
            await message.answer(
                "📍 Отправь мне свой Steam ID или ссылку на профиль:",
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"Ошибка в обработчике /start для пользователя {tg_id}: {e}")
        await message.answer("❌ Произошла ошибка. Попробуй еще раз.")


@router.message(Command("me"))
async def handle_my_profile(message: Message, state: FSMContext) -> None:
    tg_id = message.from_user.id
    user_data = await db.get_user(tg_id)
    if not user_data:
        await message.answer("❌ Сначала зарегистрируйся через /start.")
        return

    await state.clear()
    await render_profile_message(message, user_data["steam_id32"])


@router.message(RegistrationStates.waiting_steam_id, F.text)
async def handle_steam_id_input(message: Message, state: FSMContext) -> None:
    """Обработчик ввода Steam ID."""
    tg_id = message.from_user.id
    steam_input = message.text.strip()

    try:
        # Извлекаем Steam ID из ввода
        steam_id32 = None
        if steam_input.startswith("http"):
            steam_query = extract_steam_id_from_url(steam_input)
            if not steam_query:
                await message.answer(
                    "❌ Неверная ссылка на профиль Steam.\n"
                    "Используй ссылку вида https://steamcommunity.com/profiles/<id> или https://steamcommunity.com/id/<vanity>."
                )
                return

            if steam_query.isdigit():
                steam_id32 = steam_query
                if len(steam_id32) >= 17:
                    try:
                        steam_id32 = steam64_to_steam32(steam_id32)
                    except ValueError as e:
                        await message.answer(
                            f"❌ {str(e)}.\n"
                            "Проверь правильность ID и попробуй еще раз."
                        )
                        return
            else:
                steam_id64 = await resolve_vanity_url(steam_query)
                if not steam_id64:
                    await message.answer(
                        "❌ Не удалось разрешить vanity-ссылку Steam.\n"
                        "Проверь ссылку или используй прямой Steam ID."
                    )
                    return
                try:
                    steam_id32 = steam64_to_steam32(steam_id64)
                except ValueError as e:
                    await message.answer(
                        f"❌ {str(e)}.\n"
                        "Проверь правильность ID и попробуй еще раз."
                    )
                    return
        else:
            # Если это просто ID, проверяем и конвертируем при необходимости
            if steam_input.isdigit() and len(steam_input) >= 17:
                # Это Steam ID64, конвертируем в ID32
                try:
                    steam_id32 = steam64_to_steam32(steam_input)
                except ValueError as e:
                    await message.answer(
                        f"❌ {str(e)}.\n"
                        "Проверь правильность ID и попробуй еще раз."
                    )
                    return
            else:
                # Это уже Steam ID32
                steam_id32 = steam_input

        if not steam_id32:
            await message.answer(
                "❌ Не удалось извлечь Steam ID из ссылки.\n\n"
                "⚠️ Ссылки вида /id/username/ не поддерживаются.\n"
                "Используй ссылку с цифрами: /profiles/76561198012345678\n\n"
                "📍 Отправь мне свой Steam ID или ссылку на профиль: ",
                parse_mode="HTML",
            )
            return

        # Валидация Steam ID32
        if not validate_steam_id(steam_id32):
            await message.answer(
                "❌ Неверный формат Steam ID.\n"
                "Steam ID должен быть валидным Steam ID32 или Steam ID64.\n\n"
                "Попробуй еще раз или отправь ссылку на профиль:",
                parse_mode="HTML",
            )
            return

        # Сохраняем пользователя в базу
        await db.add_user(tg_id, steam_id32)

        # Очищаем состояние
        await state.clear()

        # Получаем ссылку на профиль
        from app.utils.steam import format_steam_profile_url

        profile_url = format_steam_profile_url(steam_id32)

        await render_profile_message(message, steam_id32)

        logger.info(f"Пользователь {tg_id} зарегистрирован с Steam ID: {steam_id32}")

    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя {tg_id}: {e}")
        await message.answer("❌ Произошла ошибка при регистрации. Попробуй еще раз.")


@router.message(RegistrationStates.waiting_steam_id)
async def handle_invalid_input(message: Message) -> None:
    """Обработчик некорректного ввода в состоянии регистрации."""
    await message.answer(
        "❌ Я ожидаю текстовое сообщение с Steam ID или ссылкой на профиль.\n\n"
        "📍 Отправь мне свой Steam ID или ссылку на профиль:",
        parse_mode="HTML",
    )


@router.message(SettingsStates.changing_steam_id, F.text)
async def handle_steam_id_change(message: Message, state: FSMContext) -> None:
    """Обработчик изменения Steam ID."""
    tg_id = message.from_user.id
    steam_input = message.text.strip()

    try:
        # Извлекаем Steam ID из ввода
        steam_id32 = None
        if steam_input.startswith("http"):
            steam_query = extract_steam_id_from_url(steam_input)
            if not steam_query:
                await message.answer(
                    "❌ Неверная ссылка на профиль Steam.\n"
                    "Используй ссылку вида https://steamcommunity.com/profiles/<id> или https://steamcommunity.com/id/<vanity>."
                )
                return

            if steam_query.isdigit():
                steam_id32 = steam_query
                if len(steam_id32) >= 17:
                    try:
                        steam_id32 = steam64_to_steam32(steam_id32)
                    except ValueError as e:
                        await message.answer(
                            f"❌ {str(e)}.\n"
                            "Проверь правильность ID и попробуй еще раз."
                        )
                        return
            else:
                steam_id64 = await resolve_vanity_url(steam_query)
                if not steam_id64:
                    await message.answer(
                        "❌ Не удалось разрешить vanity-ссылку Steam.\n"
                        "Проверь ссылку или используй прямой Steam ID."
                    )
                    return
                try:
                    steam_id32 = steam64_to_steam32(steam_id64)
                except ValueError as e:
                    await message.answer(
                        f"❌ {str(e)}.\n"
                        "Проверь правильность ID и попробуй еще раз."
                    )
                    return
        else:
            steam_id32 = steam_input

        if not steam_id32:
            await message.answer(
                "❌ Не удалось извлечь Steam ID из ссылки.\n"
                "Проверь правильность ссылки и попробуй еще раз."
            )
            return

        # Валидация Steam ID
        if not validate_steam_id(steam_id32):
            await message.answer(
                "❌ Неверный формат Steam ID.\n"
                "Steam ID32 должен быть числом от 0 до 1,000,000,000.\n\n"
                "Попробуй еще раз или отправь ссылку на профиль:",
                parse_mode="HTML",
            )
            return

        # Обновляем Steam ID в базе
        success = await db.update_steam_id(tg_id, steam_id32)

        if success:
            # Очищаем состояние
            await state.clear()

            # Получаем ссылку на профиль
            from app.utils.steam import format_steam_profile_url

            profile_url = format_steam_profile_url(steam_id32)

            await message.answer(
                f"✅ Steam ID успешно изменен!\n\n"
                f"🎮 Твой новый Steam ID: <code>{steam_id32}</code>\n"
                f"🔗 Профиль Steam: <a href=\"{profile_url}\">ссылка</a>",
                parse_mode="HTML",
            )

            await message.answer("🎮 Твой профиль:", reply_markup=player_menu(steam_id32))

            logger.info(f"Пользователь {tg_id} изменил Steam ID на: {steam_id32}")
        else:
            await message.answer("❌ Ошибка обновления Steam ID. Попробуй еще раз.")

    except Exception as e:
        logger.error(f"Ошибка при изменении Steam ID для пользователя {tg_id}: {e}")
        await message.answer("❌ Произошла ошибка. Попробуй еще раз.")
