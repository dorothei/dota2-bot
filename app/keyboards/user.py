from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder




def settings_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔄 Сменить Steam ID", callback_data="change_steam_id"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Отвязать аккаунт", callback_data="unlink_account")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile"))

    return builder.as_markup()


def matches_navigation(
    current_page: int = 0, has_next: bool = False
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if current_page > 0:
        builder.add(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"matches_page_{current_page - 1}"
            )
        )

    if has_next:
        builder.add(
            InlineKeyboardButton(
                text="➡️ Вперед", callback_data=f"matches_page_{current_page + 1}"
            )
        )

    if current_page > 0 or has_next:
        builder.row()

    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile"))

    return builder.as_markup()


def confirm_action(action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))

    return builder.as_markup()


def back_button(callback_data: str = "back_to_profile") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data))

    return builder.as_markup()


def player_menu(account_id: str, show_back: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="⚔️ Последние матчи", callback_data=f"player_matches_{account_id}"))
    builder.row(InlineKeyboardButton(text="⭐ Любимые герои", callback_data=f"player_heroes_{account_id}"))
    if show_back:
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile"))

    return builder.as_markup()


def match_menu(match_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="📦 Предметы Radiant", callback_data=f"match_items_radiant_{match_id}"))
    builder.row(InlineKeyboardButton(text="📦 Предметы Dire", callback_data=f"match_items_dire_{match_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile"))

    return builder.as_markup()


# Для удаления клавиатуры
remove_keyboard = ReplyKeyboardRemove()
