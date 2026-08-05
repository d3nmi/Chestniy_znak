import os
import sys
import socket
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.config import settings
from backend.api import router

app = FastAPI(
    title="KM Server API",
    description="Система маркировки товаров для склада",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === УМНОЕ ОПРЕДЕЛЕНИЕ ПУТИ ДЛЯ СТАТИКИ ===
if getattr(sys, 'frozen', False):
    # Путь к папке, где лежит скомпилированный .exe
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    # Путь к папке, где лежит скрипт main.py
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
async def serve_index():
    # Гарантируем абсолютный путь к index.html рядом с запускатором
    index_path = os.path.join(ROOT_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "error", "message": f"Файл index.html не найден по пути: {index_path}"}

app.include_router(router, prefix="/api")

# --- ФУНКЦИЯ ДЛЯ ОПРЕДЕЛЕНИЯ IP-АДРЕСА В СЕТИ ---
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = settings.port
    
    print("\n" + "="*60)
    print(" СЕРВЕР МАРКИРОВКИ УСПЕШНО ЗАПУЩЕН И ГОТОВ К РАБОТЕ!")
    print("="*60)
    print(f" На этом компьютере откройте: http://localhost:{port}")
    print(f" На других устройствах откройте: http://{local_ip}:{port}")
    print("="*60)
    print(" (Для остановки сервера просто закройте это черное окно)\n")
    print(" (Привозникновении проблем обратитесь к: daniil.mitreykin@noytech.com)\n")

    # Запуск сервера
    uvicorn.run(app, host="0.0.0.0", port=port)