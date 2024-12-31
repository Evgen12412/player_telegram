import asyncio
import io
import os
import sqlite3
import unicodedata

from pydub import AudioSegment
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest

# Ваши данные
api_id = '21825944'
api_hash = '574a1fba91efbbec3a9b854d6eeceab7'
phone_number = '+79280433030'

# Имя канала (или ссылка)
channel_username = 'https://t.me/+MpeNP3bDz2EwZGIy'  # Например, 'telegram' для канала @telegram

# Создаем клиент
client = TelegramClient('session_name', api_id, api_hash)

# Подключение к базе данных SQLite
def init_db():
    conn = sqlite3.connect('telegram_files.db')
    cursor = conn.cursor()
    # Создаем таблицу, если она не существует
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_title TEXT NOT NULL,
            file_name TEXT NOT NULL,
            date TEXT NOT NULL,
            size INTEGER NOT NULL,
            mime_type TEXT NOT NULL,
            download_link TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Проверка существования файла в базе данных
def file_exists(file_name):
    conn = sqlite3.connect('telegram_files.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM files WHERE file_name = ?', (file_name,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Добавление данных в базу данных
def save_to_db(track_title, file_name, date, size, mime_type, download_link):
    conn = sqlite3.connect('telegram_files.db')
    cursor = conn.cursor()
    # Вставляем данные в таблицу
    cursor.execute('''
        INSERT INTO files (track_title, file_name, date, size, mime_type, download_link)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (track_title, file_name, date, size, mime_type, download_link))
    conn.commit()
    conn.close()
    print(f"Данные сохранены в базу данных: {file_name}")

# Функция для перекодирования аудиофайла в MP3 в памяти
def convert_to_mp3_in_memory(file_data):
    audio = AudioSegment.from_file(io.BytesIO(file_data))
    mp3_io = io.BytesIO()
    audio.export(mp3_io, format="mp3")
    mp3_io.seek(0)
    return mp3_io

# Функция для нормализации имени файла
def normalize_filename(filename):
    # Удаляем диакритические знаки и заменяем пробелы на подчеркивания
    normalized = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('utf-8')
    return normalized.replace(' ', '_')

async def fetch_channel_info():
    # Получаем информацию о канале
    channel = await client.get_entity(channel_username)

    # Получаем полную информацию о канале (включая количество участников)
    full_channel = await client(GetFullChannelRequest(channel))
    print(f"Название канала: {channel.title}")
    print(f"Описание канала: {full_channel.full_chat.about}")
    print(f"Количество участников: {full_channel.full_chat.participants_count}")

async def monitor_channel():
    # Получаем информацию о канале
    channel = await client.get_entity(channel_username)

    # Получаем последнее сообщение для отслеживания новых
    last_message_id = None
    while True:
        try:
            async for message in client.iter_messages(channel, limit=1000):  # Проверяем последние 10 сообщений
                if message.media:
                    print(f"Тип медиа: {message.media.__class__.__name__}")
                    if hasattr(message.media, 'document'):
                        # Получаем имя файла
                        file_name = getattr(message.file, 'name', 'audio.mp3')
                        if isinstance(file_name, bytes):
                            file_name = file_name.decode('utf-8', errors='ignore')

                        # Кодируем имя файла в UTF-8
                        file_name = file_name.encode('utf-8', errors='ignore').decode('utf-8')

                        # Нормализуем имя файла
                        normalized_file_name = normalize_filename(file_name)
                        mp3_file_name = f"{os.path.splitext(normalized_file_name)[0]}.mp3"
                        # Проверяем, существует ли файл в базе данных
                        if not file_exists(mp3_file_name):
                            # Скачиваем файл в память
                            file_data = await message.download_media(file=bytes)
                            # Перекодируем в MP3 в памяти
                            mp3_io = convert_to_mp3_in_memory(file_data)
                            # Получаем MIME-тип
                            mime_type = "audio/mpeg"
                            # Сохраняем данные в базу данных
                            save_to_db(
                                track_title=file_name,
                                file_name=mp3_file_name,
                                date=message.date.isoformat(),  # Преобразуем дату в строку
                                size=mp3_io.getbuffer().nbytes,
                                mime_type=mime_type,
                                download_link=f"https://t.me/c/{channel.id}/{message.id}"
                            )
                            print(f"Добавлен файл: {mp3_file_name}")
                        else:
                            print(f"Файл уже существует: {mp3_file_name}")
                if last_message_id is None:
                    last_message_id = message.id
                elif message.id > last_message_id:
                    last_message_id = message.id
            # Задержка между проверками (например, 60 секунд)
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Ошибка при мониторинге канала: {e}")
            await asyncio.sleep(60)  # Повторная попытка через 60 секунд

async def main():
    # Инициализация базы данных
    init_db()

    # Подключаемся к Telegram
    await client.start(phone_number)

    # Получаем информацию о канале
    await fetch_channel_info()

    # Запускаем мониторинг канала
    await monitor_channel()

# Запускаем клиент
with client:
    client.loop.run_until_complete(main())