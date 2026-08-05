import logging
import asyncio
import pandas as pd
from typing import Dict, Any
from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database import AsyncSessionLocal
from backend.models import KMCode

logger = logging.getLogger(__name__)

def normalize_gs(text: str) -> str:
    """Приводит все текстовые вариации спецсимвола GS к нативному ASCII 29 (\x1d)"""
    if not text:
        return ""
    t = str(text)
    t = t.replace('_x001D_', chr(29))
    t = t.replace('_x001d_', chr(29))
    t = t.replace('<GS>', chr(29))
    t = t.replace('\\x1D', chr(29))
    t = t.replace('\\x1d', chr(29))
    return t.strip()

async def process_excel_import(file_path: str, mode: str = "replace") -> Dict[str, Any]:
    logger.info(f"Начало чтения файла {file_path}")
    try:
        df = await asyncio.to_thread(pd.read_excel, file_path, dtype=str)
    except Exception as e:
        logger.error(f"Ошибка чтения Excel: {e}")
        raise ValueError(f"Не удалось прочитать файл Excel: {str(e)}")

    df = df.fillna("")
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    COLUMN_MAPPING = {
        "gtin": "gtin", "км": "km", "km": "km",                 
        "штрихкод": "barcode", "barcode": "barcode",       
        "артикул": "article", "article": "article",
        "размер": "size", "size": "size",
        "цвет": "color", "color": "color",
        "тип": "product_type", "тип товара": "product_type", "product_type": "product_type"
    }

    df = df.rename(columns=COLUMN_MAPPING)
    expected_columns = set(COLUMN_MAPPING.values())
    
    records = df.to_dict(orient="records")
    valid_records = []
    
    for row in records:
        valid_row = {k: v for k, v in row.items() if k in expected_columns}
        if "km" in valid_row:
            valid_row["km"] = normalize_gs(valid_row["km"])
        if "barcode" in valid_row:
            valid_row["barcode"] = normalize_gs(valid_row["barcode"])
            
        if "km" in valid_row and valid_row["km"]:
            valid_records.append(valid_row)

    total_records = len(valid_records)
    if total_records == 0:
        return {"status": "error", "message": "В файле не найдено валидных кодов."}

    async with AsyncSessionLocal() as session:
        try:
            if mode == "replace":
                await session.execute(delete(KMCode))
                await session.commit()

            chunk_size = 1000
            for i in range(0, total_records, chunk_size):
                chunk = valid_records[i:i + chunk_size]
                stmt = sqlite_insert(KMCode).values(chunk)
                
                if mode == "append":
                    update_dict = {
                        c.name: c for c in stmt.excluded 
                        if c.name not in ['id', 'km', 'printed', 'reserved', 'reserved_at', 'printed_at', 'operator', 'workstation']
                    }
                    if update_dict:
                        stmt = stmt.on_conflict_do_update(index_elements=['km'], set_=update_dict)
                    else:
                        stmt = stmt.on_conflict_do_nothing(index_elements=['km'])
                
                await session.execute(stmt)
                await session.commit()

            return {"status": "success", "imported_rows": total_records, "mode": mode}
        except Exception as e:
            await session.rollback()
            raise e