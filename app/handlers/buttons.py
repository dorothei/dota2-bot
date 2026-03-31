from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.formatting import Bold, Text

from app.database.db import db
from app.keyboards.user import (
    back_button,
    confirm_action,
    main_menu,
    matches_navigation,
    match_menu,
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
        await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            return
        raise


@router.callback_query(F.data == "profile")
async def handle_profile(callback: CallbackQuery, state: FSMContext) -> None:
    tg_id = callback.from_user.id
    try:
        user_data = await db.get_user(tg_id)
        if not user_data:
            await callback.answer("❌ Сначала зарегистрируйся!", show_alert=True)
            return

        steam_id32 = user_data["steam_id32"]
        stats_data = await opendota_client.get_formatted_player_stats(steam_id32)

        full_text = Text(Bold("📊 Твоя статистика Dota 2"), "\n\n", stats_data["text"])

        if stats_data["avatar_url"]:
            await callback.message.answer_photo(
                photo=stats_data["avatar_url"],
                caption=full_text.as_html(),
                parse_mode="HTML",
            )
        else:
            await callback.message.answer(
                full_text.as_html(),
                parse_mode="HTML",
            )
        
        await state.set_state(NavigationStates.viewing_profile)
        await state.update_data(account_id=steam_id32)
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
            await callback.message.answer(
                "🚷 Профиль скрыт. Матчи недоступны."
            )
            await callback.answer()
            return
        
        matches = await opendota_client.get_recent_matches(steam_id32, limit=5)

        if not matches:
            await callback.message.answer(
                "📭 У тебя пока нет матчей или данные недоступны."
            )
            await callback.answer()
            return

        matches_text = "<b>⚔️ Последние матчи:</b>\n\n"

        from app.utils.formatters import format_match_result

        for i, match in enumerate(matches[:5], 1):
            match_text = format_match_result(match)
            matches_text += f"{i}. {match_text}\n\n"

        await state.set_data({"current_page": 0, "has_next": len(matches) > 5})
        await state.set_state(NavigationStates.viewing_matches)
        await state.update_data(account_id=steam_id32)

        await callback.message.answer(
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
            await callback.message.answer("📭 Статистика по героям недоступна.")
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

        await callback.message.answer(
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
    await callback.message.answer(
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
    await callback.message.answer(
        Text(
            Bold("🔄 Смена Steam ID"),
            "\n\nОтправь мне новый Steam ID или ссылку на профиль:",
        ).as_html(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "unlink_account")
async def handle_unlink_account(callback: CallbackQuery) -> None:
    await callback.message.answer(
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
    await callback.message.edit_text(
        "❌ Действие отменено.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_last")
async def handle_back_to_last(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    data = await state.get_data()
    
    if current_state == NavigationStates.viewing_profile:
        account_id = data.get("account_id")
        if account_id:
            # Показать профиль
            stats_data = await opendota_client.get_formatted_player_stats(account_id)
            full_text = Text(Bold("📊 Статистика игрока"), "\n", f"🆔 Steam ID32: {account_id}\n\n", stats_data["text"])
            if stats_data["avatar_url"]:
                await callback.message.answer_photo(
                    photo=stats_data["avatar_url"],
                    caption=full_text.as_html(),
                    parse_mode="HTML",
                    reply_markup=player_menu(account_id)
                )
            else:
                await callback.message.answer(
                    full_text.as_html(),
                    parse_mode="HTML",
                    reply_markup=player_menu(account_id)
                )
        else:
            await callback.message.edit_text(
                Text(Bold("🎮 Главное меню:")).as_html(),
                parse_mode="HTML",
                reply_markup=main_menu(),
            )
    elif current_state == NavigationStates.viewing_matches:
        account_id = data.get("account_id")
        if account_id:
            # Показать матчи
            profile = await opendota_client.get_player_profile(account_id)
            if not profile:
                await callback.message.answer("🚷 Профиль скрыт. Матчи недоступны.")
            else:
                matches = await opendota_client.get_recent_matches(account_id, limit=5)
                if not matches:
                    await callback.message.answer("📭 Матчи недоступны.")
                else:
                    matches_text = "<b>⚔️ Последние матчи:</b>\n\n"
                    from app.utils.formatters import format_match_result
                    for i, match in enumerate(matches[:5], 1):
                        match_text = format_match_result(match)
                        matches_text += f"{i}. {match_text}\n\n"
                    await callback.message.answer(
                        matches_text,
                        parse_mode="HTML",
                        reply_markup=back_button(),
                    )
        else:
            await callback.message.edit_text(
                Text(Bold("🎮 Главное меню:")).as_html(),
                parse_mode="HTML",
                reply_markup=main_menu(),
            )
    elif current_state == NavigationStates.viewing_match:
        match_id = data.get("match_id")
        if match_id:
            # Показать матч
            session = await opendota_client.get_session()
            async with session.get(f"https://api.opendota.com/api/matches/{match_id}") as response:
                if response.status == 200:
                    match_data = await response.json()
                    match_text = format_match_details(match_data)
                    match_html = match_text.as_html() if hasattr(match_text, "as_html") else str(match_text)
                    await callback.message.answer(
                        match_html,
                        parse_mode="HTML",
                        reply_markup=match_menu(str(match_id))
                    )
                else:
                    await callback.message.answer("❌ Матч не найден.")
        else:
            await safe_edit_text(
                callback.message,
                Text(Bold("🎮 Главное меню:")).as_html(),
                parse_mode="HTML",
                reply_markup=main_menu(),
            )
    else:
        await safe_edit_text(
            callback.message,
            Text(Bold("🎮 Главное меню:")).as_html(),
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
    
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    data = await state.get_data()
    
    if current_state == NavigationStates.viewing_profile:
        account_id = data.get("account_id")
        if account_id:
            # Показать профиль
            stats_data = await opendota_client.get_formatted_player_stats(account_id)
            full_text = Text(Bold("📊 Статистика игрока"), "\n", f"🆔 Steam ID32: {account_id}\n\n", stats_data["text"])
            if stats_data["avatar_url"]:
                await callback.message.answer_photo(
                    photo=stats_data["avatar_url"],
                    caption=full_text.as_html(),
                    parse_mode="HTML",
                    reply_markup=player_menu(account_id)
                )
            else:
                await callback.message.answer(
                    full_text.as_html(),
                    parse_mode="HTML",
                    reply_markup=player_menu(account_id)
                )
        else:
            await callback.message.edit_text(
                Text(Bold("🎮 Главное меню:")).as_html(),
                parse_mode="HTML",
                reply_markup=main_menu(),
            )
    elif current_state == NavigationStates.viewing_matches:
        account_id = data.get("account_id")
        if account_id:
            # Показать матчи
            profile = await opendota_client.get_player_profile(account_id)
            if not profile:
                await callback.message.answer("🚷 Профиль скрыт. Матчи недоступны.")
            else:
                matches = await opendota_client.get_recent_matches(account_id, limit=5)
                if not matches:
                    await callback.message.answer("📭 Матчи недоступны.")
                else:
                    matches_text = "<b>⚔️ Последние матчи:</b>\n\n"
                    from app.utils.formatters import format_match_result
                    for i, match in enumerate(matches[:5], 1):
                        match_text = format_match_result(match)
                        matches_text += f"{i}. {match_text}\n\n"
                    await callback.message.answer(
                        matches_text,
                        parse_mode="HTML",
                        reply_markup=back_button(),
                    )
        else:
            await callback.message.edit_text(
                Text(Bold("🎮 Главное меню:")).as_html(),
                parse_mode="HTML",
                reply_markup=main_menu(),
            )
    elif current_state == NavigationStates.viewing_match:
        match_id = data.get("match_id")
        if match_id:
            # Показать матч
            session = await opendota_client.get_session()
            async with session.get(f"https://api.opendota.com/api/matches/{match_id}") as response:
                if response.status == 200:
                    match_data = await response.json()
                    match_text = format_match_details(match_data)
                    match_html = match_text.as_html() if hasattr(match_text, "as_html") else str(match_text)
                    await callback.message.answer(
                        match_html,
                        parse_mode="HTML",
                        reply_markup=match_menu(str(match_id))
                    )
                else:
                    await callback.message.answer("❌ Матч не найден.")
        else:
            await callback.message.edit_text(
                Text(Bold("🎮 Главное меню:")).as_html(),
                parse_mode="HTML",
                reply_markup=main_menu(),
            )
    else:
        await callback.message.edit_text(
            Text(Bold("🎮 Главное меню:")).as_html(),
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("player_matches_"))
async def handle_player_matches(callback: CallbackQuery) -> None:
    account_id = callback.data.split("_", 2)[2]
    try:
        recent_matches = await opendota_client.get_recent_matches(account_id, limit=5)

        if not recent_matches:
            await callback.message.answer(
                "❌ Не удалось загрузить последние матчи.",
                reply_markup=back_button(),
            )
            await callback.answer()
            return

        matches_text = Text(Bold("⚔️ Последние матчи игрока:"), "\n\n")

        from app.utils.formatters import format_match_result

        for match in recent_matches:
            match_text = format_match_result(match)
            matches_text += match_text + "\n\n"

        await callback.message.answer(
            matches_text.as_html(),
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
            await callback.message.answer(
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

        await callback.message.answer(
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

                from app.utils.formatters import get_hero_name, format_player_items

                for player in radiant_players:
                    hero_id = player.get("hero_id", 0)
                    hero_name = get_hero_name(hero_id)
                    items = await format_player_items(player)
                    items_text += Text(f"🦸 {hero_name}\n{items}\n\n")

                await callback.message.answer(
                    items_text.as_html(),
                    parse_mode="HTML",
                    reply_markup=back_button(),
                )
            else:
                await callback.message.answer("❌ Ошибка загрузки данных матча.", reply_markup=back_button())
        
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

                from app.utils.formatters import get_hero_name, format_player_items

                for player in dire_players:
                    hero_id = player.get("hero_id", 0)
                    hero_name = get_hero_name(hero_id)
                    items = await format_player_items(player)
                    items_text += Text(f"🦸 {hero_name}\n{items}\n\n")

                await callback.message.answer(
                    items_text.as_html(),
                    parse_mode="HTML",
                    reply_markup=back_button(),
                )
            else:
                await callback.message.answer("❌ Ошибка загрузки данных матча.", reply_markup=back_button())
        
        await state.set_state(NavigationStates.viewing_match)
        await state.update_data(match_id=match_id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка получения предметов для матча {match_id}: {e}")
        await callback.answer("❌ Ошибка загрузки предметов", show_alert=True)
