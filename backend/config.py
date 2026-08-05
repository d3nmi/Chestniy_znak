import os
import sys
import json
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# === УМНОЕ ОПРЕДЕЛЕНИЕ ПУТИ (ДЛЯ PYINSTALLER) ===
if getattr(sys, 'frozen', False):
    # Если запущено как скомпилированный .exe, берем папку, где лежит сам .exe
    BASE_DIR = Path(sys.executable).parent
else:
    # Если запущено как обычный скрипт, берем корень проекта (на 2 уровня выше этого файла)
    BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_PATH = BASE_DIR / "config.json"
ENV_PATH = BASE_DIR / ".env"

class AppConfig(BaseSettings):
    """Модель конфигурации приложения."""
    port: int
    db_path: str
    reservation_timeout_minutes: int
    max_history_records: int
    log_level: str
    
    # СЕКРЕТЫ: Этот параметр Pydantic автоматически возьмет из файла .env
    admin_token: str

    # Указываем Pydantic, где искать переменные окружения
    model_config = SettingsConfigDict(env_file=str(ENV_PATH), env_file_encoding="utf-8", extra="ignore")

def load_config() -> AppConfig:
    """
    Чтение и валидация конфигурации из JSON + Секретов из .env.
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Файл конфигурации не найден по пути: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Распаковываем JSON в модель. 
    return AppConfig(**data)

# Создаем глобальный объект настроек
settings = load_config()