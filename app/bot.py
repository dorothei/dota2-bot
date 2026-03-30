import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config.config import BOT_TOKEN
from config.logger import logger
from app.database.db import db
from app.handlers.main import router as main_router
from app.handlers.buttons import router as buttons_router
from app.services.opendota import opendota_client

async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    dp.include_router(main_router)
    dp.include_router(buttons_router)
    
    try:
        await db.connect()
        logger.info("Запуск бота...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
    finally:
        await db.disconnect()
        await opendota_client.close()
        await bot.session.close()
        logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())