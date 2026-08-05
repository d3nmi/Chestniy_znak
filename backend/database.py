import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event

# === УМНОЕ ОПРЕДЕЛЕНИЕ ПУТИ (ДЛЯ PYINSTALLER) ===
if getattr(sys, 'frozen', False):
    # Если запущено как скомпилированный .exe, берем папку, где лежит сам .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Если запущено как обычный скрипт, берем корень проекта
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Создаем папку DATABASE прямо рядом с exe (если её нет)
DB_FOLDER = os.path.join(BASE_DIR, "DATABASE")
os.makedirs(DB_FOLDER, exist_ok=True)

# Формируем путь к файлу базы данных и меняем слеши \ на / для SQLAlchemy
db_path = os.path.join(DB_FOLDER, "km.db").replace('\\', '/')
DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"

# Настройка движка БД
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={
        "timeout": 20,
        "check_same_thread": False
    }
)

# Оптимизация SQLite (режим WAL для скорости и защиты от блокировок)
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-64000")
    cursor.close()

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session