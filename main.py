from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, CallbackQueryHandler, filters

from config import TELEGRAM_TOKEN, ADMIN_USER_TELEGRAM_ID, DB_PATH
from db.db import (create_tables, save_answer, save_relation, get_unanswered_questions, get_answer,
                   get_existing_answers_for_question)

from bot.test_flow import start_test
from bot.handlers import handle_message, handle_user_answer
import logging

# Настраиваем Telegram Bot Token и ID администратора
ADMIN_USER_ID = ADMIN_USER_TELEGRAM_ID
BOT_TOKEN = TELEGRAM_TOKEN

# Состояния бота
ADDING_QUESTION, ADDING_ANSWERS = range(2)

logging.basicConfig(level=logging.INFO)

# Асинхронные обработчики команд и сообщений
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    if str(user_id) == ADMIN_USER_ID:
        unanswered_questions = get_unanswered_questions()
        if unanswered_questions:
            # Сохраняем вопросы в контексте
            context.user_data['questions'] = unanswered_questions
            context.user_data['questions_name'] = unanswered_questions[0]['question']
            context.user_data['current_question'] = unanswered_questions[0]['id']

            # Получаем уже существующие ответы для текущего вопроса, если они есть
            existing_answers = get_existing_answers_for_question(context.user_data['current_question'])
            context.user_data[
                'answers'] = existing_answers if existing_answers else []

            context.user_data['state'] = ADDING_ANSWERS
            count_answer = len (context.user_data['answers'])

            if count_answer > 0:
                await update.message.reply_text(
                    f'Привет админ - {user_name}! Введите ответов - {9-count_answer} на вопрос №{context.user_data['current_question']} "{context.user_data['questions_name']}", один за другим.')
            else:
                await update.message.reply_text(
                    f'Привет админ - {user_name}! Введите 9 ответов на вопрос №{context.user_data['current_question']} "{context.user_data['questions_name']}", один за другим.')
        else:
            await update.message.reply_text('На все вопросы уже записаны ответы')
    else:
        # Приветствие пользователя и вывод кнопки "Начать тест"
        reply_text = f"Привет, {update.message.from_user.first_name}! Предлагаю пройти тест на важность ценностей. Вы готовы?"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Начать тест", callback_data="start_test")]
        ])
        await update.message.reply_text(reply_text, reply_markup=reply_markup)

# Функция обработчика кнопки "Начать тест"
async def button(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "start_test":
        await start_test(update, context)

# Запуск бота
def main():
    create_tables()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(start_test, pattern="^start_test$"))
    application.add_handler(CallbackQueryHandler(handle_user_answer))
    application.add_handler(CallbackQueryHandler(button))  # Добавляем CallbackQueryHandler для обработки нажатий

    application.run_polling()


if __name__ == '__main__':
    main()