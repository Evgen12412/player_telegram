import os
import sqlite3

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

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

# Список категорий и таблиц
CATEGORIES = {
    "Музыка": ["song_ru", "song_en"],
    "Подкасты": ["podcast_ru", "podcast_en"],
    "Библия": ["bible_ru", "bible_en"],
    "Проповеди": ["sermons_ru", "sermons_en"],
    "Доказательства": ["evedence_ru", "evedence_en"]
}


def get_audio_files():
    conn = sqlite3.connect('telegram_files.db')
    cursor = conn.cursor()

    audio_files = {}

    for category, tables in CATEGORIES.items():
        audio_files[category] = []
        for table in tables:
            cursor.execute(f'''
                SELECT file_name, size, download_link
                FROM {table}
                WHERE mime_type LIKE 'audio%'
                ORDER BY size DESC
            ''')
            fetched_files = cursor.fetchall()
            for file in fetched_files:
                audio_files[category].append(file)

    conn.close()
    return audio_files


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Получаем аудиофайлы из базы данных
    audio_files = get_audio_files()
    return templates.TemplateResponse("index.html", {"request": request, "audio_files": audio_files})


@app.head("/", response_class=HTMLResponse)
async def head_root():
    return


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)