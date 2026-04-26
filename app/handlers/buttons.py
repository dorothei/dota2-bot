from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.formatting import Bold, Code, Text
from app.database.db import db
from app.keyboards.user import (
    back_button,
    confirm_action,
    match_menu,
    matches_navigation,
    player_menu,
    settings_menu,
)
from app.services.opendota import opendota_client
from app.states.user import NavigationStates, SettingsStates
from app.utils.formatters import format_match_details
from app.utils.steam import extract_steam_id_from_url, validate_steam_id
from config.logger import logger

router = Router()


async def safe_edit_text(message, text, parse_mode="HTML", reply_markup=None):
    try:
        if getattr(message, "photo", None):
            await message.edit_caption(
                caption=text, parse_mode=parse_mode, reply_markup=reply_markup
            )
        else:
            await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        error_text = str(e).lower()
        if "message is not modified" in error_text:
            return
        # Если не можем редактировать, отправляем новое сообщение
        if any(
            needle in error_text
            for needle in [
                "there is no text in the message to edit",
                "message to edit not found",
                "message can't be edited",
                "message is not modified",
            ]
        ):
            await message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)
            return
        raise


async def safe_send_or_edit(callback, text, parse_mode="HTML", reply_markup=None):
    """Безопасно отправляет или редактирует сообщение"""
    try:
        await safe_edit_text(callback.message, text, parse_mode=parse_mode, reply_markup=reply_markup)
    except TelegramBadRequest:
        # Если не получилось отредактировать, отправляем новое сообщение
        await callback.message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)


@router.callback_query(F.data == "profile")
async def handle_profile(callback: CallbackQuery, state: FSMContext, account_id: str | None = None) -> None:
    tg_id = callback.from_user.id
    try:
        if account_id is None:
            user_data = await db.get_user(tg_id)
            if not user_data:
                await callback.answer("❌ Сначала зарегистрируйся!", show_alert=True)
                return
            account_id = user_data["steam_id32"]

        stats_data = await opendota_client.get_formatted_player_stats(account_id)

        full_text = Text(
            Bold("📊 Статистика игрока"),
            "\n\n",
            Bold("🆔 Steam ID:"),
            " ",
            Code(account_id),
            "\n\n",
            stats_data["text"],
        )

        await state.set_state(NavigationStates.viewing_profile)
        await state.update_data(account_id=account_id)

        reply_markup = None
        if stats_data.get("profile_found"):
            reply_markup = player_menu(account_id)

        if stats_data["avatar_url"] and getattr(callback.message, "photo", None):
            await safe_edit_text(
                callback.message,
                full_text.as_html(),
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        elif stats_data["avatar_url"]:
            await callback.message.answer_photo(
                photo=stats_data["avatar_url"],
                caption=full_text.as_html(),
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        else:
            await safe_send_or_edit(
                callback,
                full_text.as_html(),
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка получения профиля для пользователя {tg_id}: {e}")
        await callback.answer("❌ Ошибка загрузки профиля", show_alert=True)


@router.callback_query(F.data == "matches")
async def handle_matches(callback: CallbackQuery, state: FSMContext) -> None:
    tg_id = callback.from_user.id
    try:
        user_data = await db.get_user(tg_id)
        if not user_data:
            await callback.answer("❌ Сначала зарегистрируйся!", show_alert=True)
            return

        steam_id32 = user_data["steam_id32"]
        
        # Проверить доступность профиля
        profile = await opendota_client.get_player_profile(steam_id32)
        if not profile:
            await safe_send_or_edit(
                callback,
                "🚷 Профиль скрыт. Матчи недоступны.",
                reply_markup=back_button()
            )
            await callback.answer()
            return
        
        matches = await opendota_client.get_recent_matches(steam_id32, limit=5)

        if not matches:
            await safe_send_or_edit(
                callback,
                "📭 У тебя пока нет матчей или данные недоступны.",
                reply_markup=back_button()
            )
            await callback.answer()
            return

        matches_text = "<b>⚔️ Последние матчи:</b>\n\n"

        from app.utils.formatters import format_match_result

        for i, match in enumerate(matches[:5], 1):
            match_text = format_match_result(match)
            matches_text += f"{i}. {match_text}\n\n"

        await state.set_data({"current_page": 0, "has_next": len(matches) > 5, "account_id": steam_id32})
        await state.set_state(NavigationStates.viewing_matches)

        await safe_send_or_edit(
            callback,
            matches_text,
            parse_mode="HTML",
            reply_markup=matches_navigation(0, len(matches) > 5),
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка получения матчей для пользователя {tg_id}: {e}")
        await callback.answer("❌ Ошибка загрузки матчей", show_alert=True)


@router.callback_query(F.data.startswith("matches_page_"))
async def handle_matches_pagination(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split("_")[-1])
    tg_id = callback.from_user.id
    try:
        user_data = await db.get_user(tg_id)
        if not user_data:
            await callback.answer("❌ Сначала зарегистрируйся!", show_alert=True)
            return

        steam_id32 = user_data["steam_id32"]
        matches = await opendota_client.get_recent_matches(steam_id32, limit=20)

        if not matches:
            await callback.answer("❌ Матчи не найдены", show_alert=True)
            return

        start_idx = page * 5
        end_idx = start_idx + 5
        page_matches = matches[start_idx:end_idx]

        matches_text = f"<b>⚔️ Последние матчи (страница {page + 1}):</b>\n\n"

        from app.utils.formatters import format_match_result

        for i, match in enumerate(page_matches, start_idx + 1):
            match_text = format_match_result(match)
            matches_text += f"{i}. {match_text}\n\n"

        has_next = end_idx < len(matches)
        await state.set_data({"current_page": page, "has_next": has_next})

        await callback.message.edit_text(
            matches_text,
            parse_mode="HTML",
            reply_markup=matches_navigation(page, has_next),
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка пагинации матчей для пользователя {tg_id}: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)


@router.callback_query(F.data == "heroes")
async def handle_heroes(callback: CallbackQuery) -> None:
    tg_id = callback.from_user.id
    try:
        user_data = await db.get_user(tg_id)
        if not user_data:
            await callback.answer("❌ Сначала зарегистрируйся!", show_alert=True)
            return

        steam_id32 = user_data["steam_id32"]
        heroes_stats = await opendota_client.get_player_heroes(steam_id32)

        if not heroes_stats:
            await safe_send_or_edit(
                callback,
                "📭 Статистика по героям недоступна.",
                reply_markup=back_button()
            )
            await callback.answer()
            return

        heroes_stats.sort(key=lambda x: x.get("games", 0), reverse=True)

        heroes_text = Text(Bold("⭐ Твои любимые герои:"), "\n\n")

        from app.utils.formatters import get_hero_name

        for i, hero in enumerate(heroes_stats[:10], 1):
            hero_id = hero.get("hero_id", 0)
            hero_name = get_hero_name(hero_id)
            games = hero.get("games", 0)
            wins = hero.get("win", 0)
            winrate = (wins / games * 100) if games > 0 else 0

            heroes_text += Text(
                f"{i}. {hero_name}\n",
                f"   🎮 Игр: {games} | ✅ Побед: {wins}\n",
                f"   📈 Винрейт: {winrate:.1f}%\n\n",
            )

        await safe_send_or_edit(
            callback,
            heroes_text.as_html(),
            parse_mode="HTML",
            reply_markup=back_button(),
        )
        await callback.answer()

    except Exception as e:
        logger.error(
            f"Ошибка получения статистики героев для пользователя {tg_id}: {e}"
        )
        await callback.answer("❌ Ошибка загрузки статистики", show_alert=True)


@router.callback_query(F.data == "settings")
async def handle_settings(callback: CallbackQuery) -> None:
    await safe_send_or_edit(
        callback,
        Text(
            Bold("⚙️ Настройки профиля:"),
            "\n\n",
            "Здесь ты можешь изменить свой Steam ID или отвязать аккаунт.",
        ).as_html(),
        parse_mode="HTML",
        reply_markup=settings_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "change_steam_id")
async def handle_change_steam_id(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.changing_steam_id)
    await safe_send_or_edit(
        callback,
        Text(
            Bold("🔄 Смена Steam ID"),
            "\n\nОтправь мне новый Steam ID или ссылку на профиль:",
        ).as_html(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "unlink_account")
async def handle_unlink_account(callback: CallbackQuery) -> None:
    await safe_send_or_edit(
        callback,
        Text(
            Bold("🗑️ Отвязка аккаунта"),
            "\n\n",
            "⚠️ Внимание! Это удалит все твои данные из бота.\n",
            "Тебе придется заново регистрироваться.\n\n",
            "Ты уверен?",
        ).as_html(),
        parse_mode="HTML",
        reply_markup=confirm_action("unlink"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_"))
async def handle_confirm_action(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.split("_", 1)[1]
    tg_id = callback.from_user.id
    try:
        if action == "unlink":
            success = await db.delete_user(tg_id)
            if success:
                await state.clear()
                await callback.message.edit_text(
                    Text(
                        Bold("✅ Твой аккаунт успешно отвязан."),
                        "\n",
                        "Используй /start для новой регистрации.",
                    ).as_html(),
                    parse_mode="HTML",
                )
                logger.info(f"Пользователь {tg_id} отвязал аккаунт")
            else:
                await callback.answer("❌ Ошибка удаления аккаунта", show_alert=True)
                return
        await callback.answer()
    except Exception as e:
        logger.error(
            f"Ошибка при подтверждении действия {action} для пользователя {tg_id}: {e}"
        )
        await callback.answer("❌ Ошибка выполнения действия", show_alert=True)


@router.callback_query(F.data == "cancel")
async def handle_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await handle_profile(callback, state)




@router.callback_query(F.data == "back_to_match")
async def handle_back_to_match(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    match_id = data.get("match_id")
    if not match_id:
        await callback.answer("❌ Не удалось вернуться к матчу.", show_alert=True)
        return

    try:
        session = await opendota_client.get_session()
        async with session.get(f"https://api.opendota.com/api/matches/{match_id}") as response:
            if response.status != 200:
                await callback.answer("❌ Не удалось загрузить матч.", show_alert=True)
                return
            match_data = await response.json()

        match_text = format_match_details(match_data)
        await safe_send_or_edit(
            callback,
            match_text.as_html(),
            parse_mode="HTML",
            reply_markup=match_menu(str(match_id)),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка возврата к матчу {match_id}: {e}")
        await callback.answer("❌ Ошибка при возврате к матчу.", show_alert=True)


@router.callback_query(F.data == "back_to_profile")
async def handle_back_to_profile(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    account_id = data.get("account_id")
    if account_id:
        await handle_profile(callback, state, account_id=account_id)
    else:
        await handle_profile(callback, state)


@router.callback_query(F.data.startswith("player_matches_"))
async def handle_player_matches(callback: CallbackQuery) -> None:
    account_id = callback.data.split("_", 2)[2]
    try:
        recent_matches = await opendota_client.get_recent_matches(account_id, limit=5)

        if not recent_matches:
            await safe_send_or_edit(
                callback,
                "❌ Не удалось загрузить последние матчи.",
                reply_markup=back_button(),
            )
            await callback.answer()
            return

        matches_text = "<b>⚔️ Последние матчи игрока:</b>\n\n"

        from app.utils.formatters import format_match_result

        for i, match in enumerate(recent_matches, 1):
            match_text = format_match_result(match)
            matches_text += f"{i}. {match_text}\n\n"

        await safe_send_or_edit(
            callback,
            matches_text,
            parse_mode="HTML",
            reply_markup=back_button(),
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка получения матчей для игрока {account_id}: {e}")
        await callback.answer("❌ Ошибка загрузки матчей", show_alert=True)


@router.callback_query(F.data.startswith("player_heroes_"))
async def handle_player_heroes(callback: CallbackQuery) -> None:
    account_id = callback.data.split("_", 2)[2]
    try:
        heroes_stats = await opendota_client.get_player_heroes(account_id)

        if not heroes_stats:
            await safe_send_or_edit(
                callback,
                "❌ Не удалось загрузить статистику героев.",
                reply_markup=back_button(),
            )
            await callback.answer()
            return

        # Сортируем по количеству игр
        heroes_stats.sort(key=lambda x: x.get("games", 0), reverse=True)

        heroes_text = Text(Bold("⭐ Любимые герои игрока:"), "\n\n")

        from app.utils.formatters import get_hero_name

        for i, hero in enumerate(heroes_stats[:10], 1):
            hero_id = hero.get("hero_id", 0)
            hero_name = get_hero_name(hero_id)
            games = hero.get("games", 0)
            wins = hero.get("win", 0)
            winrate = (wins / games * 100) if games > 0 else 0

            heroes_text += Text(
                f"{i}. {hero_name}\n",
                f"   🎮 Игр: {games} | ✅ Побед: {wins}\n",
                f"   📈 Винрейт: {winrate:.1f}%\n\n",
            )

        await safe_send_or_edit(
            callback,
            heroes_text.as_html(),
            parse_mode="HTML",
            reply_markup=back_button(),
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка получения героев для игрока {account_id}: {e}")
        await callback.answer("❌ Ошибка загрузки героев", show_alert=True)


@router.callback_query(F.data.startswith("match_items_radiant_"))
async def handle_match_items_radiant(callback: CallbackQuery, state: FSMContext) -> None:
    match_id = callback.data.split("_", 3)[3]
    try:
        session = await opendota_client.get_session()
        async with session.get(f"https://api.opendota.com/api/matches/{match_id}") as response:
            if response.status == 200:
                match_data = await response.json()
                players = match_data.get("players", [])
                radiant_players = [p for p in players if p.get("player_slot", 0) < 128]

                items_text = Text(Bold("📦 Предметы Radiant команды:"), "\n\n")

                from app.utils.formatters import format_player_items, get_hero_name

                for player in radiant_players:
                    hero_id = player.get("hero_id", 0)
                    hero_name = get_hero_name(hero_id)
                    items = await format_player_items(player)
                    items_text += Text(f"🦸 {hero_name}\n{items}\n\n")

                await safe_send_or_edit(
                    callback,
                    items_text.as_html(),
                    parse_mode="HTML",
                    reply_markup=back_button("back_to_match"),
                )
            else:
                await safe_send_or_edit(
                    callback,
                    "❌ Ошибка загрузки данных матча.",
                    reply_markup=back_button("back_to_match")
                )
        
        await state.set_state(NavigationStates.viewing_match)
        await state.update_data(match_id=match_id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка получения предметов для матча {match_id}: {e}")
        await callback.answer("❌ Ошибка загрузки предметов", show_alert=True)


@router.callback_query(F.data.startswith("match_items_dire_"))
async def handle_match_items_dire(callback: CallbackQuery, state: FSMContext) -> None:
    match_id = callback.data.split("_", 3)[3]
    try:
        session = await opendota_client.get_session()
        async with session.get(f"https://api.opendota.com/api/matches/{match_id}") as response:
            if response.status == 200:
                match_data = await response.json()
                players = match_data.get("players", [])
                dire_players = [p for p in players if p.get("player_slot", 0) >= 128]

                items_text = Text(Bold("📦 Предметы Dire команды:"), "\n\n")

                from app.utils.formatters import format_player_items, get_hero_name

                for player in dire_players:
                    hero_id = player.get("hero_id", 0)
                    hero_name = get_hero_name(hero_id)
                    items = await format_player_items(player)
                    items_text += Text(f"🦸 {hero_name}\n{items}\n\n")

                await safe_send_or_edit(
                    callback,
                    items_text.as_html(),
                    parse_mode="HTML",
                    reply_markup=back_button("back_to_match"),
                )
            else:
                await safe_send_or_edit(
                    callback,
                    "❌ Ошибка загрузки данных матча.",
                    reply_markup=back_button("back_to_match")
                )
        
        await state.set_state(NavigationStates.viewing_match)
        await state.update_data(match_id=match_id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка получения предметов для матча {match_id}: {e}")
        await callback.answer("❌ Ошибка загрузки предметов", show_alert=True)
