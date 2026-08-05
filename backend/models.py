from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Index, text
from sqlalchemy.orm import Mapped, mapped_column

# Импортируем базовый класс из нашего модуля БД
from backend.database import Base

class KMCode(Base):
    """
    Модель таблицы кодов маркировки.
    Хранит всю информацию о КМ, их статусах и кем они забронированы/распечатаны.
    """
    __tablename__ = "km_codes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # GTIN обычно 14 символов
    gtin: Mapped[Optional[str]] = mapped_column(String(14), index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String)
    
    # Сам код маркировки должен быть уникальным
    km: Mapped[str] = mapped_column(String, unique=True, index=True)
    
    article: Mapped[Optional[str]] = mapped_column(String, index=True)
    size: Mapped[Optional[str]] = mapped_column(String)
    color: Mapped[Optional[str]] = mapped_column(String)
    product_type: Mapped[Optional[str]] = mapped_column(String)
    
    # Статусы. server_default=text("0") гарантирует, что БД сама ставит False (0 в SQLite)
    printed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    reserved: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    
    # Даты устанавливаем с учетом временных зон (timezone=True)
    reserved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    printed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    operator: Mapped[Optional[str]] = mapped_column(String)
    workstation: Mapped[Optional[str]] = mapped_column(String)

    # Композитные индексы — это ключ к мгновенной выдаче свободных КМ.
    # База сразу найдет блок свободных кодов по конкретному GTIN или Артикулу.
    __table_args__ = (
        Index('ix_km_search_gtin', 'gtin', 'reserved', 'printed'),
        Index('ix_km_search_article', 'article', 'reserved', 'printed'),
    )


class PrintHistory(Base):
    """
    Модель таблицы истории печати.
    Используется исключительно для логирования и статистики (заменяет старый CSV).
    """
    __tablename__ = "print_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    gtin: Mapped[Optional[str]] = mapped_column(String(14), index=True)
    km: Mapped[str] = mapped_column(String, index=True)
    article: Mapped[Optional[str]] = mapped_column(String, index=True)
    
    workstation: Mapped[Optional[str]] = mapped_column(String)
    operator: Mapped[Optional[str]] = mapped_column(String)