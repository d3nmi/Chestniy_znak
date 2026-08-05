import logging
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import KMCode, PrintHistory
from backend.utils import get_moscow_time

logger = logging.getLogger(__name__)

async def get_and_reserve_code(
    session: AsyncSession, gtin: str = None, article: str = None, 
    operator: str = "Unknown", workstation: str = "Unknown"
) -> dict:
    moscow_now = get_moscow_time()
    
    subq = select(KMCode.km).where(KMCode.reserved == False, KMCode.printed == False)
    if gtin: subq = subq.where(KMCode.gtin == gtin)
    elif article: subq = subq.where(KMCode.article == article)
    subq = subq.limit(1).scalar_subquery()
    
    stmt = update(KMCode).where(KMCode.km == subq).values(
        reserved=True, reserved_at=moscow_now, operator=operator, workstation=workstation
    ).returning(KMCode)
    
    result = await session.execute(stmt)
    c = result.scalar_one_or_none()
    await session.commit()
    
    if not c: 
        return None
        
    return {
        "km": c.km, "barcode": c.barcode, "gtin": c.gtin,
        "article": c.article, "size": c.size, "color": c.color, "product_type": c.product_type
    }

async def get_and_reserve_codes_bulk(
    session: AsyncSession, qty: int, gtin: str = None, article: str = None, 
    operator: str = "Unknown", workstation: str = "Unknown"
) -> list[dict]:
    moscow_now = get_moscow_time()
    
    subq = select(KMCode.km).where(KMCode.reserved == False, KMCode.printed == False)
    if gtin: subq = subq.where(KMCode.gtin == gtin)
    elif article: subq = subq.where(KMCode.article == article)
    subq = subq.limit(qty).scalar_subquery()

    stmt = update(KMCode).where(KMCode.km.in_(subq)).values(
        reserved=True, reserved_at=moscow_now, operator=operator, workstation=workstation
    ).returning(KMCode)
    
    result = await session.execute(stmt)
    codes = result.scalars().all()
    await session.commit()
    
    if not codes: 
        return []
        
    return [{
        "km": c.km, "barcode": c.barcode, "gtin": c.gtin,
        "article": c.article, "size": c.size, "color": c.color, "product_type": c.product_type
    } for c in codes]

async def reset_stuck_reservations(session: AsyncSession) -> int:
    stmt = update(KMCode).where(KMCode.reserved == True, KMCode.printed == False).values(reserved=False, reserved_at=None)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount

async def confirm_print_status(session: AsyncSession, km: str, operator: str, workstation: str) -> bool:
    moscow_now = get_moscow_time()
    
    stmt = update(KMCode).where(KMCode.km == km).values(printed=True, reserved=False, printed_at=moscow_now)
    result = await session.execute(stmt)
    
    # Если база не обновила ни одной строки — код не найден
    if result.rowcount == 0:
        await session.rollback()
        return False
        
    code_result = await session.execute(select(KMCode).where(KMCode.km == km))
    code_data = code_result.scalar_one_or_none()
    
    if code_data:
        history_entry = PrintHistory(
            gtin=code_data.gtin, 
            km=km, 
            article=code_data.article, 
            workstation=workstation, 
            operator=operator,
            datetime=moscow_now
        )
        session.add(history_entry)
    await session.commit()
    return True

async def get_print_history(session: AsyncSession, limit: int, offset: int, gtin: str = None, km: str = None, operator: str = None) -> dict:
    query = select(PrintHistory).order_by(PrintHistory.datetime.desc())
    count_query = select(func.count(PrintHistory.id))
    
    if gtin:
        query = query.where(PrintHistory.gtin == gtin)
        count_query = count_query.where(PrintHistory.gtin == gtin)
    if km:
        query = query.where(PrintHistory.km.contains(km))
        count_query = count_query.where(PrintHistory.km.contains(km))
    if operator:
        query = query.where(PrintHistory.operator == operator)
        count_query = count_query.where(PrintHistory.operator == operator)
        
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    items = result.scalars().all()
    return {"total": total, "items": items}

async def get_warehouse_stats(session: AsyncSession) -> dict:
    total = await session.scalar(select(func.count(KMCode.id)))
    printed = await session.scalar(select(func.count(KMCode.id)).where(KMCode.printed == True))
    reserved = await session.scalar(select(func.count(KMCode.id)).where(KMCode.reserved == True))
    return {
        "total_imported": total or 0, "printed": printed or 0, "reserved": reserved or 0,
        "free": (total or 0) - (printed or 0) - (reserved or 0)
    }

async def get_available_count(session: AsyncSession, gtin: str = None, article: str = None) -> int:
    query = select(func.count(KMCode.id)).where(KMCode.reserved == False, KMCode.printed == False)
    if gtin: query = query.where(KMCode.gtin == gtin)
    elif article: query = query.where(KMCode.article == article)
    result = await session.execute(query)
    return result.scalar() or 0