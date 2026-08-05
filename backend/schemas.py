from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class NextCodeResponse(BaseModel):
    """Модель ответа при выдаче нового КМ."""
    km: str
    barcode: str
    gtin: Optional[str]
    article: Optional[str]
    size: Optional[str]
    color: Optional[str]
    product_type: Optional[str]

class ConfirmPrintRequest(BaseModel):
    """Модель запроса на подтверждение печати."""
    km: str
    operator: str
    workstation: str

class GenericResponse(BaseModel):
    status: str
    message: str

# --- НОВЫЕ СХЕМЫ ДЛЯ ИСТОРИИ И СТАТИСТИКИ ---

class HistoryItem(BaseModel):
    """Модель одной записи из истории печати."""
    id: int
    datetime: datetime
    gtin: Optional[str]
    km: str
    article: Optional[str]
    workstation: Optional[str]
    operator: Optional[str]

class HistoryResponse(BaseModel):
    """Пагинированный ответ для таблицы истории."""
    total: int
    items: List[HistoryItem]

class StatsResponse(BaseModel):
    """Модель ответа со статистикой по складу."""
    total_imported: int
    printed: int
    reserved: int
    free: int