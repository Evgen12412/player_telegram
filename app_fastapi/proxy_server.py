import asyncio
import logging
import mimetypes
import os
import tempfile
import unicodedata
from contextlib import asynccontextmanager
from urllib.parse import unquote, quote

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from telethon import TelegramClient
from telethon.tl.types import PeerChannel

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

# Конфигурация Telegram клиента
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Глобальная переменная для клиента
client = None

# Удаляем старую сессию если она существует
if os.path.exists('bot_session.session'):
    try:
        os.remove('bot_session.session')
        logger.info("Старая сессия удалена")
    except Exception as e:
        logger.error(f"Ошибка при удалении старой сессии: {e}")

async def init_client():
    global client
    for attempt in range(3):  # Пробуем 3 раза
        try:
            client = TelegramClient('bot_session', API_ID, API_HASH)
            await client.start(bot_token=BOT_TOKEN)
            logger.info("Telegram client started successfully")
            return client
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if os.path.exists('bot_session.session'):
                os.remove('bot_session.session')
            # Увеличиваем время ожидания между попытками
            await asyncio.sleep(5 * (attempt + 1))
    raise Exception("Failed to initialize Telegram client after 3 attempts")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    try:
        client = await init_client()
        yield
    finally:
        if client:
            await client.disconnect()
            logger.info("Telegram client disconnected")
            if os.path.exists('bot_session.session'):
                os.remove('bot_session.session')

app = FastAPI(lifespan=lifespan)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def normalize_filename(filename):
    # Удаляем диакритические знаки и заменяем пробелы на подчеркивания
    normalized = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('utf-8')
    return normalized.replace(' ', '_')

def remove_temp_file(path: str):
    try:
        os.remove(path)
        logger.info(f"Temporary file {path} removed")
    except Exception as e:
        logger.error(f"Error removing temporary file {path}: {e}")

@app.get("/proxy")
async def proxy(url: str, background_tasks: BackgroundTasks):
    try:
        logger.info(f"Received request for URL: {url}")

        # Декодируем URL
        decoded_url = unquote(url)
        logger.info(f"Decoded URL: {decoded_url}")

        # Извлекаем ID сообщения и канала из URL
        parts = decoded_url.split('/')
        if len(parts) < 2:
            raise ValueError("URL must contain both channel_id and message_id")
        try:
            channel_id = int(parts[-2])
            message_id = int(parts[-1])
        except ValueError as ve:
            logger.error(f"Invalid channel_id or message_id: {ve}")
            raise HTTPException(status_code=400, detail="Invalid channel_id or message_id")
        logger.info(f"Parsed channel_id: {channel_id}, message_id: {message_id}")

        # Проверяем подключение клиента
        if not client or not client.is_connected():
            logger.error("Telegram client is not connected")
            raise HTTPException(status_code=500, detail="Telegram client is not connected")

        # Загружаем сущность канала
        try:
            channel = await client.get_entity(PeerChannel(channel_id))
            logger.info(f"Loaded channel entity: {channel.title}")
        except Exception as e:
            logger.error(f"Error loading channel entity: {e}")
            raise HTTPException(status_code=400, detail=f"Error loading channel entity: {str(e)}")

        # Получаем сообщение
        try:
            message = await client.get_messages(channel, ids=message_id)
            if not message:
                logger.error("Message not found")
                raise HTTPException(status_code=404, detail="Message not found")

            if not message.media:
                logger.error("Message has no media")
                raise HTTPException(status_code=404, detail="Message has no media")

            logger.info(f"Found message with media type: {type(message.media)}")

            # Скачиваем файл во временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                await message.download_media(file=temp_file.name)
                temp_file_path = temp_file.name
                logger.info(f"Downloaded file to temporary path: {temp_file_path}")

            # Получаем имя файла
            file_name = getattr(message.file, 'name', 'audio.mp3')
            if isinstance(file_name, bytes):
                file_name = file_name.decode('utf-8', errors='ignore')

            # Кодируем имя файла в UTF-8
            file_name = file_name.encode('utf-8', errors='ignore').decode('utf-8')
            logger.debug(f"Encoded file name: {file_name}")

            # Нормализуем имя файла
            normalized_file_name = normalize_filename(file_name)
            logger.debug(f"Normalized file name: {normalized_file_name}")

            # URL-кодируем оригинальное имя файла для использования в filename*
            quoted_filename = quote(file_name)
            logger.debug(f"Quoted filename: {quoted_filename}")

            # Формируем заголовок Content-Disposition с использованием filename* для поддержки UTF-8
            content_disposition = f'inline; filename="{normalized_file_name}"; filename*=UTF-8\'\'{quoted_filename}'
            logger.debug(f"Content-Disposition: {content_disposition}")

            # Определяем MIME-тип на основе расширения файла
            mime_type, _ = mimetypes.guess_type(normalized_file_name)
            if not mime_type:
                mime_type = "application/octet-stream"
            logger.debug(f"Determined MIME type: {mime_type}")

            # Возвращаем файл с помощью FileResponse
            response = FileResponse(
                path=temp_file_path,
                media_type=mime_type,
                filename=normalized_file_name,
                headers={
                    "Content-Disposition": content_disposition,
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "no-cache",
                    "Content-Length": str(os.path.getsize(temp_file_path))
                }
            )
            logger.info(f"FileResponse prepared for file: {normalized_file_name}")

            # Добавляем задачу удаления временного файла
            background_tasks.add_task(remove_temp_file, temp_file_path)
            logger.info(f"Background task added to remove file: {temp_file_path}")

            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5501, log_level="debug")

    # uvicorn proxy_server:app --host 0.0.0.0 --port 5501 --reload