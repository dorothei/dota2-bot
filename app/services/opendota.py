import asyncio
from typing import Any, Final
import aiohttp
from aiogram.utils.formatting import Bold, Text
from config.logger import logger

BASE_URL: Final[str] = "https://api.opendota.com/api"

class OpenDotaClient:
    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _make_request(self, url: str) -> dict[str, Any] | None:
        session = await self.get_session()
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                logger.warning(f"Ошибка API: {response.status}")
                return None
        except Exception as e:
            logger.error(f"Ошибка запроса {url}: {e}")
            return None

    async def get_player_profile(self, account_id: str) -> dict[str, Any] | None:
        return await self._make_request(f"{BASE_URL}/players/{account_id}")

    async def get_player_wl(self, account_id: str) -> dict[str, Any] | None:
        return await self._make_request(f"{BASE_URL}/players/{account_id}/wl")

    async def get_recent_matches(self, account_id: str, limit: int = 20) -> list | None:
        data = await self._make_request(f"{BASE_URL}/players/{account_id}/recentMatches")
        return data[:limit] if data else None

    async def get_formatted_player_stats(self, account_id: str) -> Text:
        try:
            profile_data, wl_data = await asyncio.gather(
                self.get_player_profile(account_id),
                self.get_player_wl(account_id),
                return_exceptions=True
            )
            
            if isinstance(profile_data, Exception) or not profile_data:
                return Text("🚷 Профиль не найден или скрыт.")
            
            profile = profile_data.get("profile", {})
            name = profile.get("personaname", "Неизвестно")
            rank_tier = profile_data.get("rank_tier", 0)
            
            wins = wl_data.get("win", 0) if wl_data else 0
            losses = wl_data.get("lose", 0) if wl_data else 0
            
            from app.utils.formatters import format_winrate, get_rank_name
            
            return Text(
                Bold("🎮 Игрок:"), f" {name}\n",
                Bold("🏆 Ранг:"), f" {get_rank_name(rank_tier)}\n",
                Bold("⚔️ Игр:"), f" {wins + losses}\n",
                Bold("✅ Побед:"), f" {wins} | ",
                Bold("❌ Поражений:"), f" {losses}\n",
                Bold("📈 Винрейт:"), f" {format_winrate(wins, losses)}"
            )
        except Exception as e:
            logger.error(f"Ошибка статистики: {e}")
            return Text("❌ Ошибка при получении данных.")

    async def get_hero_stats(self, account_id: str) -> list[dict[str, Any]] | None:
        url = f"{BASE_URL}/players/{account_id}/heroes"
        session = await self.get_session()
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Ошибка получения героев: {e}")
            return None

opendota_client = OpenDotaClient()