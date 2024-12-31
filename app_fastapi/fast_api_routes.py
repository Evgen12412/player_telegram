import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import sqlite3

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
AUDIO_DIR = os.path.join(STATIC_DIR, "audio")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# Настраиваем шаблоны и статические файлы
templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Функция для получения аудиофайлов из базы данных
def get_audio_files():
    conn = sqlite3.connect('telegram_files.db')
    cursor = conn.cursor()
    # Выбираем только аудиофайлы и сортируем их по размеру (по убыванию)
    cursor.execute('''
        SELECT  file_name, size, download_link
        FROM files
        WHERE mime_type LIKE 'audio%'
        ORDER BY size DESC
    ''')
    audio_files = cursor.fetchall()
    print(audio_files)
    conn.close()

    # Разделяем файлы на две категории
    sermons = [file for file in audio_files if file[1] > 8888888]  # Проповеди
    music = [file for file in audio_files if file[1] <= 8888888]   # Музыка

    return {"sermons": sermons, "music": music}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Получаем аудиофайлы из базы данных
    audio_files = get_audio_files()
    return templates.TemplateResponse("index.html", {"request": request, **audio_files})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)


