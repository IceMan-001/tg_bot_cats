import logging
import os
import datetime

import pytz
import requests
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import CallbackContext, ApplicationBuilder, CommandHandler, MessageHandler, filters
from database import Database

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('BOT_TOKEN')  # Получаем токен

# Логирование ошибок
logging.basicConfig(
    format='%(asctime)s - %(name) - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)  # Создаем логин

db = Database()  # создаем базу данных


def add_user(user_id):  # Добавление пользователя
    try:
        db.add_user(user_id)
    except Exception as e:
        logger.error(e)


def get_all_users():
    try:
        users = db.get_all_users()
        return users
    except Exception as e:
        logger.error(e)


def fetch_cat():
    url = 'https://api.thecatapi.com/v1/image/search'
    headers = {}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # if data and 'url' in data[0]:
        if data and isinstance(data[0], dict):
            cat_photo_url = data[0]['url']
            return cat_photo_url
    except Exception as e:
        logger.error(f"Ошибка при получении данных {e}")


async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    add_user(user.id)
    await update.message.reply_text('Привет, ты классный(ая)! Я буду отправлять тебе котиков каждое утро!')


async def help(update, context: CallbackContext):
    await update.message.reply_text('Из доступных команд только /start')


async def send_cat_images(application):
    users = db.get_all_users()
    if not users:
        logger.info('Нет пользователей в БД')
        return

    cat_photo_url = fetch_cat()
    if not cat_photo_url:
        logger.info('Не удалось получить url фотографии')
        return

    for user_id in users.copy():
        try:
            await application.bot.send_photo(chat_id=user_id[0], photo=cat_photo_url)
            logger.info('Фотография была отправлена')
        except Exception as e:
            logger.info(f"При отправке фотографии произошла ошибка {e}")


async def unknown_command(update: Update, context: CallbackContext):
    await update.message.reply_text('Такой команды нет. Просто напиши /start')




async def scheduled_send_cat(context: CallbackContext):
    """Обертка для запуска твоей функции через JobQueue"""
    await send_cat_images(context.application)


def main():
    # Создаем приложение
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Хендлеры
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), unknown_command))

    # Настройка расписания через встроенный JobQueue
    moscow_tz = pytz.timezone('Europe/Moscow')
    job_queue = application.job_queue

    # Аналог твоего CronTrigger (каждый день в 20:00)
    job_queue.run_daily(
        scheduled_send_cat,
        time=datetime.time(hour=20, minute=0, tzinfo=moscow_tz)
    )

    logger.info('Бот и планировщик запущены!')

    # run_polling сам создаст event loop и запустит планировщик
    application.run_polling()

if __name__ == '__main__':
    main()
