import os
import sys
import shutil
import csv
import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from backend.config import settings
from backend.database import get_db
from backend.models import PrintHistory
from backend.schemas import NextCodeResponse, ConfirmPrintRequest, GenericResponse, HistoryResponse, StatsResponse
from backend.services import (
    get_and_reserve_code, get_and_reserve_codes_bulk, confirm_print_status,
    reset_stuck_reservations, get_print_history, get_warehouse_stats, get_available_count
)
from backend.importer import process_excel_import

router = APIRouter()

# === УМНОЕ ОПРЕДЕЛЕНИЕ ПУТИ (ДЛЯ PYINSTALLER) ===
if getattr(sys, 'frozen', False):
    # Если запущено как скомпилированный .exe, берем папку, где лежит сам .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Если запущено как обычный скрипт, берем корень проекта
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Базовая директория для данных теперь всегда будет рядом с программой
DATA_DIR = os.path.join(BASE_DIR, "DATABASE")

def verify_admin(x_admin_token: Optional[str] = Header(None)):
    if not secrets.compare_digest(x_admin_token or "", settings.admin_token):
        raise HTTPException(status_code=403, detail="Доступ запрещен. Неверный пароль.")

# --- ОТКРЫТЫЕ МАРШРУТЫ ДЛЯ РАБОЧИХ ТЕРМИНАЛОВ ---
@router.get("/health", response_model=GenericResponse)
async def health_check():
    return {"status": "ok", "message": "Сервер маркировки работает штатно"}

@router.get("/next-code", response_model=NextCodeResponse)
async def get_next_code(gtin: Optional[str] = None, article: Optional[str] = None, operator: str = "HTML_Client", workstation: str = "PC-1", session: AsyncSession = Depends(get_db)):
    if not gtin and not article: raise HTTPException(status_code=400, detail="Укажите GTIN или Артикул")
    code = await get_and_reserve_code(session, gtin, article, operator, workstation)
    if not code: raise HTTPException(status_code=404, detail="Свободных кодов не найдено")
    return code

@router.get("/next-codes-bulk", response_model=List[NextCodeResponse])
async def next_codes_bulk(qty: int = Query(..., gt=0, le=500), gtin: Optional[str] = None, article: Optional[str] = None, operator: str = "HTML_Client", workstation: str = "PC-1", session: AsyncSession = Depends(get_db)):
    if not gtin and not article: raise HTTPException(status_code=400, detail="Укажите GTIN или Артикул")
    codes = await get_and_reserve_codes_bulk(session, qty, gtin, article, operator, workstation)
    if not codes: raise HTTPException(status_code=404, detail="Свободных кодов нет")
    return codes

@router.post("/printed", response_model=GenericResponse)
async def confirm_print(req: ConfirmPrintRequest, session: AsyncSession = Depends(get_db)):
    ok = await confirm_print_status(session, req.km, req.operator, req.workstation)
    if not ok:
        raise HTTPException(status_code=404, detail="Код не найден в базе данных")
    return {"status": "success", "message": "Печать подтверждена"}

@router.get("/history", response_model=HistoryResponse)
async def history(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), gtin: Optional[str] = None, km: Optional[str] = None, operator: Optional[str] = None, session: AsyncSession = Depends(get_db)):
    return await get_print_history(session, limit, offset, gtin, km, operator)

@router.get("/stats", response_model=StatsResponse)
async def stats(session: AsyncSession = Depends(get_db)):
    return await get_warehouse_stats(session)

@router.get("/available")
async def check_available(gtin: Optional[str] = None, article: Optional[str] = None, session: AsyncSession = Depends(get_db)):
    count = await get_available_count(session, gtin, article)
    return {"free": count}


# --- ЗАЩИЩЕННЫЕ МАРШРУТЫ АДМИНИСТРАТОРА ---
@router.post("/reset-reservations", dependencies=[Depends(verify_admin)])
async def api_reset_reservations(session: AsyncSession = Depends(get_db)):
    count = await reset_stuck_reservations(session)
    return {"status": "success", "message": f"Сброшено зависших резервов: {count}"}

@router.post("/import", dependencies=[Depends(verify_admin)])
async def import_excel_api(file: UploadFile = File(...), mode: str = Form("replace")):
    # Используем локальную папку
    upload_dir = os.path.join(DATA_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        return await process_excel_import(file_path, mode)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/archive-history", dependencies=[Depends(verify_admin)])
async def archive_history_api(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(PrintHistory))
    items = result.scalars().all()
    
    filename = f"history_archive_{datetime.now():%Y%m%d_%H%M%S}.csv"
    # Используем локальную папку
    archive_dir = os.path.join(DATA_DIR, "archives")
    os.makedirs(archive_dir, exist_ok=True)
    filepath = os.path.join(archive_dir, filename)
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["datetime", "gtin", "km", "article", "operator", "workstation"])
        for item in items:
            writer.writerow([item.datetime, item.gtin, item.km, item.article, item.operator, item.workstation])
            
    await session.execute(delete(PrintHistory))
    await session.commit()
    return {"status": "success", "message": f"История сохранена в {filename} и очищена"}