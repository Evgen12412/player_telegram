import asyncio
import io
import os
import sqlite3
import unicodedata

from dotenv import load_dotenv
from pydub import AudioSegment
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest


# Загрузка переменных окружения из .env файла
load_dotenv()


# Ваши данные
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
phone_number = os.getenv('PHONE_NUMBER')

# Имя канала (или ссылка)
channel_username = 'https://t.me/+MpeNP3bDz2EwZGIy'  # Например, 'telegram' для канала @telegram

# Создаем клиент
client = TelegramClient('session_name', api_id, api_hash)


# Подключение к базе данных SQLite
def init_db():
    conn = sqlite3.connect('telegram_files.db')
    cursor = conn.cursor()
    # Список таблиц с их базовыми именами
    tables = ['song', 'podcast', 'bible', 'sermons', 'evedence']
    languages = ['ru', 'en']

    for table_base in tables:
        for lang in languages:
            table_name = f"{table_base}_{lang}"
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_title TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mime_type TEXT NOT NULL,
                    download_link TEXT NOT NULL
                )
            ''')
    # Таблица плейлиста
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS my_playlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            added_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


# Проверка существования файла в соответствующей таблице
def file_exists(table_name, file_name):
    conn = sqlite3.connect('telegram_files.db')
    cursor = conn.cursor()
    cursor.execute(f'SELECT id FROM {table_name} WHERE file_name = ?', (file_name,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


# Добавление данных в соответствующую таблицу
def save_to_db(table_name, track_title, file_name, date, size, mime_type, download_link):
    conn = sqlite3.connect('telegram_files.db')
    cursor = conn.cursor()
    # Вставляем данные в таблицу
    cursor.execute(f'''
        INSERT INTO {table_name} (track_title, file_name, date, size, mime_type, download_link)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (track_title, file_name, date, size, mime_type, download_link))
    conn.commit()
    conn.close()
    print(f"Данные сохранены в базу данных: {file_name} в таблицу {table_name}")


# Функция для добавления в плейлист
def add_to_playlist(file_name):
    conn = sqlite3.connect('telegram_files.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO my_playlist (file_name, added_at)
        VALUES (?, ?)
    ''', (file_name, asyncio.get_event_loop().time()))
    conn.commit()
    conn.close()
    print(f"Файл добавлен в плейлист: {file_name}")


# Функция для перекодирования аудиофайла в MP3 в памяти
def convert_to_mp3_in_memory(file_data):
    audio = AudioSegment.from_file(io.BytesIO(file_data))
    mp3_io = io.BytesIO()
    audio.export(mp3_io, format="mp3")
    mp3_io.seek(0)
    return mp3_io


# Функция для нормализации имени файла
def normalize_filename(filename):
    # Возвращаем оригинальное имя файла без изменений
    return filename


# Определение таблицы по префиксу и постфиксу
def determine_table(file_name):
    prefix_mapping = {
        'S_': 'song',
        'P_': 'podcast',
        'B_': 'bible',
        'SE_': 'sermons',
        'E_': 'evedence'
    }

    # Поиск префикса
    table_base = None
    for prefix, table in prefix_mapping.items():
        if file_name.startswith(prefix):
            table_base = table
            break

    if not table_base:
        return None  # Неизвестный тип файла

    # Определение языка по постфиксу
    if file_name.endswith('_ru.mp3'):
        language = 'ru'
    elif file_name.endswith('_en.mp3'):
        language = 'en'
    else:
        language = 'ru'  # По умолчанию на русском

    return f"{table_base}_{language}"


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
            async for message in client.iter_messages(channel, limit=1000):  # Проверяем последние 1000 сообщений
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

                        # Определяем таблицу
                        table_name = determine_table(mp3_file_name)
                        if not table_name:
                            print(f"Неизвестный тип файла: {mp3_file_name}. Файл пропущен.")
                            continue

                        # Проверяем, существует ли файл в базе данных
                        if not file_exists(table_name, mp3_file_name):
                            # Скачиваем файл в память
                            file_data = await message.download_media(file=bytes)
                            # Перекодируем в MP3 в памяти
                            mp3_io = convert_to_mp3_in_memory(file_data)
                            # Получаем MIME-тип
                            mime_type = "audio/mpeg"
                            # Сохраняем данные в базу данных
                            save_to_db(
                                table_name=table_name,
                                track_title=file_name,
                                file_name=mp3_file_name,
                                date=message.date.isoformat(),  # Преобразуем дату в строку
                                size=mp3_io.getbuffer().nbytes,
                                mime_type=mime_type,
                                download_link=f"https://t.me/c/{channel.id}/{message.id}"
                            )
                            # Добавляем в плейлист при необходимости
                            add_to_playlist(mp3_file_name)
                            print(f"Добавлен файл: {mp3_file_name} в таблицу {table_name}")
                        else:
                            print(f"Файл уже существует: {mp3_file_name} в таблице {table_name}")
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