import nest_asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.error import BadRequest
import asyncio
import threading
import time

nest_asyncio.apply()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "7552907266:AAHW6TJPNHa7C_sD2PPjTe4-CgGRi6q7mho"
YOUR_ID = 730612339
GROUP_CHAT_ID = -1002372687727
CLIENT_TIMEOUT = 60

client_state = {}
client_timers = {}
accepting_orders = True

async def get_chat_admins(chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        return [admin.user.id for admin in admins]
    except BadRequest:
        logger.error("Не удалось получить список администраторов.")
        return []

def is_time_related_query(text):
    time_keywords = ["когда", "приедешь", "время", "будешь", "когда будешь"]
    if any(keyword in text.lower() for keyword in time_keywords):
        return True
    return False

def remove_client_timer(user_id):
    if user_id in client_timers:
        del client_timers[user_id]
        if user_id in client_state:
            client_state[user_id]['answered'] = False

async def handle_message(update: Update, context: CallbackContext):
    global accepting_orders
    try:
        if update.message:
            user_id = update.message.from_user.id
            username = update.message.from_user.username
            text = update.message.text

            logger.info(f"Получено сообщение от {user_id} (@{username}): {text}")

            if update.message.chat.id == GROUP_CHAT_ID:
                admins_ids = await get_chat_admins(GROUP_CHAT_ID)

                if user_id not in admins_ids:
                    await context.bot.send_message(YOUR_ID, f"Сообщение от клиента (@{username}): {text}")

                    if accepting_orders:
                        if user_id not in client_timers:
                            timer = threading.Timer(CLIENT_TIMEOUT, remove_client_timer, args=[user_id])
                            timer.start()
                            client_timers[user_id] = timer
                            client_state[user_id] = {'time': time.time(), 'answered': False}

                        if user_id in client_state and not client_state[user_id]['answered']:
                            if time.time() - client_state[user_id]['time'] <= CLIENT_TIMEOUT:
                                if is_time_related_query(text):
                                    await context.bot.send_message(GROUP_CHAT_ID, f"Прибуду через 10 минут. (@{username})")
                                else:
                                    await context.bot.send_message(GROUP_CHAT_ID, "Еду") #Удалено имя пользователя
                                client_state[user_id]['answered'] = True

            if user_id == YOUR_ID and update.message.reply_to_message:
                logger.info(f"Ответ на сообщение: {update.message.reply_to_message}")
                logger.info(f"GROUP_CHAT_ID: {GROUP_CHAT_ID}")
                logger.info("Условие выполняется")
                original_message = update.message.reply_to_message.text
                await context.bot.send_message(GROUP_CHAT_ID, f" {update.message.text}")

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        if update.message:
            await update.message.reply_text("Произошла ошибка при обработке вашего сообщения.")

async def start(update: Update, context: CallbackContext):
    if update.message.chat.id == YOUR_ID:
        keyboard = [[KeyboardButton('/start_orders'), KeyboardButton('/stop_orders')]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Привет! Я бот, помогающий таксистам отвечать на запросы.", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Привет! Я бот, помогающий таксистам отвечать на запросы.")

async def get_chat_id(update: Update, context: CallbackContext):
    await update.message.reply_text(f"Chat ID: {update.message.chat.id}")

async def stop_orders(update: Update, context: CallbackContext):
    global accepting_orders
    accepting_orders = False
    await update.message.reply_text("Прием заказов отключен.")

async def start_orders(update: Update, context: CallbackContext):
    global accepting_orders
    accepting_orders = True
    await update.message.reply_text("Прием заказов включен.")

async def main():
    global application
    try:
        application = Application.builder().token(TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("get_chat_id", get_chat_id))
        application.add_handler(CommandHandler("stop_orders", stop_orders))
        application.add_handler(CommandHandler("start_orders", start_orders))
        application.add_handler(MessageHandler(filters.TEXT, handle_message))

        await application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

asyncio.run(main())
