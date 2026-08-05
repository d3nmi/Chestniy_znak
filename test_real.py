import asyncio
from backend.importer import process_excel_import

async def main():
    # Замените 'my_codes.xlsx' на точное имя вашего файла
    file_name = "my_codes.xlsx" 
    
    print(f"Запускаем импорт файла: {file_name}")
    try:
        result = await process_excel_import(file_name, mode="replace")
        print(f"Итог: {result}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())