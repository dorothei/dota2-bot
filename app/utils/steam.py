import re
from typing import Final

from config.logger import logger

# Константы для конвертации Steam ID
STEAM_ID64_BASE: Final[int] = 76561197960265728


def extract_steam_id_from_url(url: str) -> str | None:
    # Прямая ссылка с ID64
    match = re.search(r'steamcommunity\.com/profiles/(\d+)', url)
    if match:
        return match.group(1)
    
    # Vanity URL (требует API запроса для разрешения)
    if 'steamcommunity.com/id/' in url:
        return None  # ← Возвращаем None для vanity URL
    
    return None

def steam64_to_steam32(steam_id64: str) -> str:

    try:
        steam_id64_int = int(steam_id64)
        steam_id32 = steam_id64_int - STEAM_ID64_BASE
        return str(steam_id32)
    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка конвертации Steam ID64 {steam_id64} в ID32: {e}")
        raise ValueError(f"Неверный формат Steam ID64: {steam_id64}")


def steam32_to_steam64(steam_id32: str) -> str:
    """Конвертирует Steam ID32 в Steam ID64."""
    try:
        steam_id32_int = int(steam_id32)
        steam_id64 = steam_id32_int + STEAM_ID64_BASE
        return str(steam_id64)
    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка конвертации Steam ID32 {steam_id32} в ID64: {e}")
        raise ValueError(f"Неверный формат Steam ID32: {steam_id32}")


def validate_steam_id(steam_id: str) -> bool:
    """Валидация Steam ID32 или ID64."""
    try:
        # Проверяем, что это число
        steam_id_int = int(steam_id)

        # Если это Steam ID64 (17+ цифр)
        if len(steam_id) >= 17:
            # Проверяем базовый диапазон Steam ID64 (без верхней границы)
            return steam_id_int >= 76561197960265728
        else:
            # Проверяем диапазон Steam ID32 (расширенный для новых аккаунтов)
            return 0 <= steam_id_int <= 4_000_000_000
    except (ValueError, TypeError):
        return False


def format_steam_profile_url(steam_id32: str) -> str:
    """Формирует прямую ссылку на профиль Steam."""
    try:
        steam_id64 = steam32_to_steam64(steam_id32)
        return f"https://steamcommunity.com/profiles/{steam_id64}"
    except ValueError:
        return f"https://steamcommunity.com/profiles/{steam_id32}"
