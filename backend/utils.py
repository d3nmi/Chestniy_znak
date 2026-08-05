from datetime import datetime
from zoneinfo import ZoneInfo

def get_moscow_time() -> datetime:
    """
    Возвращает текущее время по Москве. 
    Убираем tzinfo, чтобы SQLite корректно сохранял его как текст без конфликтов форматов.
    """
    return datetime.now(ZoneInfo("Europe/Moscow")).replace(tzinfo=None)