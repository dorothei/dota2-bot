from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Состояния для регистрации пользователя."""
    waiting_steam_id = State()


class SettingsStates(StatesGroup):
    """Состояния для настроек пользователя."""
    changing_steam_id = State()


class NavigationStates(StatesGroup):
    """Состояния для навигации по меню."""
    viewing_matches = State()
    viewing_heroes = State()
