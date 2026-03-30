from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.formatting import Bold, Text

from app.database.db import db
from app.keyboards.user import (
    back_button,
    confirm_action,
    main_menu,
    matches_navigation,
    settings_menu,
)
from app.services.opendota import opendota_client
from app.states.user import NavigationStates, SettingsStates
from app.utils.steam import extract_steam_id_from_url, validate_steam_id
from config.logger import logger

router = Router()


@router.callback_query(F.data == "profile")
async def handle_profile(callback: CallbackQuery) -> None:
    tg_id = callback.from_user.id
    try:
        user_data = await db.get_user(tg_id)
        if not user_data:
            await callback.answer("❌ Сначала зарегистрируйся!", show_alert=True)
            return

        steam_id32 = user_data["steam_id32"]
        stats_text = await opendota_client.get_formatted_player_stats(steam_id32)

        await callback.message.answer(
            Text(Bold("📊 Твоя статистика Dota 2"), "\n\n", stats_text).as_html()
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
        matches = await opendota_client.get_recent_matches(steam_id32, limit=5)

        if not matches:
            await callback.message.answer(
                "📭 У тебя пока нет матчей или данные недоступны."
            )
            await callback.answer()
            return

        matches_text = Text(Bold("⚔️ Последние матчи:"), "\n\n")

        for i, match in enumerate(matches[:5], 1):
            from app.utils.formatters import format_match_result

            match_text = format_match_result(match)
            matches_text += Text(f"{i}. ", match_text, "\n\n")

        await state.set_data({"current_page": 0, "has_next": len(matches) > 5})
        await state.set_state(NavigationStates.viewing_matches)

        await callback.message.answer(
            matches_text.as_html(),
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

        matches_text = Text(Bold(f"⚔️ Последние матчи (страница {page + 1}):"), "\n\n")

        for i, match in enumerate(page_matches, start_idx + 1):
            from app.utils.formatters import format_match_result

            match_text = format_match_result(match)
            matches_text += Text(f"{i}. ", match_text, "\n\n")

        has_next = end_idx < len(matches)
        await state.set_data({"current_page": page, "has_next": has_next})

        await callback.message.edit_text(
            matches_text.as_html(),
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
        heroes_stats = await opendota_client.get_hero_stats(steam_id32)

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

        await callback.message.answer(heroes_text.as_html(), reply_markup=back_button())
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
        ).as_html()
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
                    ).as_html()
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
    await callback.message.edit_text("❌ Действие отменено.", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        Text(Bold("🎮 Главное меню:")).as_html(), reply_markup=main_menu()
    )
    await callback.answer()
