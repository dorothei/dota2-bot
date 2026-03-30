import aiosqlite
from datetime import datetime, timezone

from config.config import DATABASE_URL
from config.logger import logger


class Database:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url.replace("sqlite+aiosqlite:///", "")
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Установка соединения с базой данных."""
        try:
            self._connection = await aiosqlite.connect(self.database_url)
            await self._create_tables()
            logger.info(f"База данных подключена: {self.database_url}")
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            raise

    async def disconnect(self) -> None:
        """Закрытие соединения с базой данных."""
        if self._connection:
            await self._connection.close()
            logger.info("Соединение с базой данных закрыто")

    async def _create_tables(self) -> None:
        """Создание таблиц базы данных."""
        if not self._connection:
            raise RuntimeError("Нет соединения с базой данных")

        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            steam_id32 TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        try:
            await self._connection.execute(create_users_table)
            await self._connection.commit()
            logger.info("Таблицы созданы или уже существуют")
        except Exception as e:
            logger.error(f"Ошибка создания таблиц: {e}")
            raise

    async def add_user(self, tg_id: int, steam_id32: str) -> None:
        """Добавление нового пользователя."""
        if not self._connection:
            raise RuntimeError("Нет соединения с базой данных")

        query = """
        INSERT OR REPLACE INTO users (tg_id, steam_id32, updated_at)
        VALUES (?, ?, ?)
        """
        
        try:
            await self._connection.execute(
                query, 
                (tg_id, steam_id32, datetime.now(timezone.utc))
            )
            await self._connection.commit()
            logger.info(f"Пользователь {tg_id} добавлен/обновлен с Steam ID: {steam_id32}")
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя {tg_id}: {e}")
            raise

    async def get_user(self, tg_id: int) -> dict[str, str | int] | None:
        """Получение информации о пользователе."""
        if not self._connection:
            raise RuntimeError("Нет соединения с базой данных")

        query = "SELECT tg_id, steam_id32, created_at, updated_at FROM users WHERE tg_id = ?"
        
        try:
            cursor = await self._connection.execute(query, (tg_id,))
            row = await cursor.fetchone()
            
            if row:
                columns = ["tg_id", "steam_id32", "created_at", "updated_at"]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя {tg_id}: {e}")
            raise

    async def update_steam_id(self, tg_id: int, steam_id32: str) -> bool:
        """Обновление Steam ID пользователя."""
        if not self._connection:
            raise RuntimeError("Нет соединения с базой данных")

        query = """
        UPDATE users 
        SET steam_id32 = ?, updated_at = ?
        WHERE tg_id = ?
        """
        
        try:
            cursor = await self._connection.execute(
                query, 
                (steam_id32, datetime.now(timezone.utc), tg_id)
            )
            await self._connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка обновления Steam ID для пользователя {tg_id}: {e}")
            raise

    async def delete_user(self, tg_id: int) -> bool:
        """Удаление пользователя."""
        if not self._connection:
            raise RuntimeError("Нет соединения с базой данных")

        query = "DELETE FROM users WHERE tg_id = ?"
        
        try:
            cursor = await self._connection.execute(query, (tg_id,))
            await self._connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя {tg_id}: {e}")
            raise


# Глобальный экземпляр базы данных
db = Database(DATABASE_URL)
