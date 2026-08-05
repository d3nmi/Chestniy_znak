import asyncio
from backend.database import engine, Base
# Обязательно импортируем модели, чтобы SQLAlchemy "увидел" их структуру перед созданием
from backend.models import KMCode, PrintHistory

async def init_models():
    """Асинхронное создание всех таблиц в базе данных SQLite."""
    print("Начало создания таблиц...")
    async with engine.begin() as conn:
        # Создаем таблицы, если их еще нет
        await conn.run_sync(Base.metadata.create_all)
    print("Успех! База данных и таблицы успешно созданы.")

if __name__ == "__main__":
    # Запускаем асинхронную функцию
    asyncio.run(init_models())