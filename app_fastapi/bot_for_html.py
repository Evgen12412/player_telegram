import asyncio
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Замените на ваш токен
TOKEN = '7785249240:AAF7uEYbUNTLD7HkM_TotKzgPXO57jLKx8U'
# Замените на ID вашего канала (например, -1001234567890)
CHANNEL_ID = '-2465406066'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    print("Получена команда /start")
    await update.message.reply_text('Привет! Я бот, который загружает аудиофайлы с канала.')

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик новых сообщений с канала."""
    print("Получено новое сообщение с канала")
    if update.channel_post and update.channel_post.audio:
        print("Сообщение с канала содержит аудиофайл")
        file = await update.channel_post.audio.get_file()
        print(f"Файл найден. File ID: {file.file_id}")

        # Сохранение файла
        file_path = f"app_fastapi/static/audio/{file.file_id}.mp3"
        print(f"Пытаюсь сохранить файл в: {file_path}")

        try:
            await file.download_to_drive(file_path)
            print(f"Файл успешно сохранен: {file_path}")
        except Exception as e:
            print(f"Ошибка при сохранении файла: {e}")
    else:
        print("Сообщение с канала не содержит аудиофайла")

async def download_channel_history(context: ContextTypes.DEFAULT_TYPE):
    """Загрузка истории сообщений с канала."""
    print("Загрузка истории сообщений с канала...")
    try:
        async for message in context.bot.get_chat_history(chat_id=CHANNEL_ID):
            if message.audio:
                print("Найден аудиофайл в истории сообщений")
                file = await message.audio.get_file()
                print(f"Файл найден. File ID: {file.file_id}")

                # Сохранение файла
                file_path = f"app_fastapi/static/audio/{file.file_id}.mp3"
                print(f"Пытаюсь сохранить файл в: {file_path}")

                try:
                    await file.download_to_drive(file_path)
                    print(f"Файл успешно сохранен: {file_path}")
                except Exception as e:
                    print(f"Ошибка при сохранении файла: {e}")

            # Добавляем задержку между запросами
            await asyncio.sleep(1)

    except AttributeError:
        print("Метод get_chat_history недоступен. Используем get_updates.")
        updates = await context.bot.get_updates()
        for update in updates:
            if update.channel_post and update.channel_post.audio:
                await handle_channel_post(update, context)
            # Добавляем задержку между запросами
            await asyncio.sleep(1)

def main() -> None:
    """Запуск бота."""
    print("Запуск бота...")
    application = Application.builder().token(TOKEN).connection_pool_size(10).pool_timeout(30).build()

    print("Добавление обработчиков...")
    application.add_handler(CommandHandler("start", start))
    # application.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_channel_post))

    # Запуск загрузки истории сообщений в основном цикле событий
    loop = asyncio.get_event_loop()
    loop.create_task(download_channel_history(application))

    print("Бот запущен и ожидает сообщений...")
    application.run_polling()

if __name__ == '__main__':
    # Создание папок, если они не существуют
    os.makedirs("app_fastapi/static/audio", exist_ok=True)
    main()