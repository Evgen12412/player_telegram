import os
import asyncio
import nest_asyncio
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Применение nest_asyncio
nest_asyncio.apply()

# Загрузка переменных окружения из .env файла
load_dotenv()

# Получение переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')  # Токен вашего бота
WEB_APP_URL = 'https://player-apps.ru'  # Замените на ваш реальный URL с HTTPS

# Проверка наличия необходимых переменных
if not BOT_TOKEN:
    logger.error("BOT_TOKEN не найден в переменных окружения.")
    raise ValueError("Не найден BOT_TOKEN в переменных окружения. Проверьте файл .env.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start. Отправляет кнопку для открытия Web App."""
    logger.info(f"Получена команда /start от пользователя {update.effective_user.id}")
    try:
        web_app_info = WebAppInfo(url=WEB_APP_URL)
        keyboard = [[InlineKeyboardButton("Открыть Плеер", web_app=web_app_info)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            'Привет! Нажмите кнопку ниже, чтобы открыть музыкальный плеер.',
            reply_markup=reply_markup
        )
        logger.info("Сообщение с кнопкой Web App успешно отправлено.")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения с кнопкой Web App: {e}")

async def main_bot() -> None:
    """Запуск Telegram бота."""
    logger.info("Запуск Telegram бота.")
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        await application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    asyncio.run(main_bot())