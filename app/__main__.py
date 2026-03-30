import asyncio

from app.bot import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Программа прервана пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
