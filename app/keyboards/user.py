from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="📊 Мой профиль", callback_data="profile"))
    builder.row(InlineKeyboardButton(text="⚔️ Последние матчи", callback_data="matches"))
    builder.row(InlineKeyboardButton(text="⭐ Любимые герои", callback_data="heroes"))
    builder.row(InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"))

    return builder.as_markup()


def settings_menu() -> InlineKeyboardMarkup:
    """Меню настроек."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔄 Сменить Steam ID", callback_data="change_steam_id"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Отвязать аккаунт", callback_data="unlink_account")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))

    return builder.as_markup()


def matches_navigation(
    current_page: int = 0, has_next: bool = False
) -> InlineKeyboardMarkup:
    """Навигация по матчам."""
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

    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))

    return builder.as_markup()


def confirm_action(action: str) -> InlineKeyboardMarkup:
    """Подтверждение действия."""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))

    return builder.as_markup()


def back_button() -> InlineKeyboardMarkup:
    """Кнопка возврата."""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))

    return builder.as_markup()


# Для удаления клавиатуры
remove_keyboard = ReplyKeyboardRemove()
