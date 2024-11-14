from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

from config import TELEGRAM_TOKEN, ADMIN_USER_TELEGRAM_ID, DB_PATH
from db.db import (create_tables, save_answer, save_relation, get_unanswered_questions, get_answer,
                   get_existing_answers_for_question)
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
                    f'Введите ответов - {9-count_answer} на вопрос №{context.user_data['current_question']} "{context.user_data['questions_name']}", один за другим.')
            else:
                await update.message.reply_text(
                    f'Введите 9 ответов на вопрос №{context.user_data['current_question']} "{context.user_data['questions_name']}", один за другим.')
        else:
            await update.message.reply_text('На все вопросы уже записаны ответы')
    else:
        # Тут логика работы бота для прохождения теста
        await update.message.reply_text("Привет! Вы не являетесь администратором и не можете добавлять вопросы.")

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    text = update.message.text
    state = context.user_data.get('state')

    if str(user_id) == ADMIN_USER_ID:
        if state == ADDING_ANSWERS:
            current_question_id = context.user_data['current_question']
            questions = context.user_data['questions']

            answer_id = get_answer(text)

            # logging.info(f"Проверка ответа на существующий: {answer_id}")

            if answer_id == text:
                # logging.info('Ответ не найден в бд')
                answer_id = save_answer(text)
                context.user_data['answers'].append(answer_id)
                save_relation(current_question_id, answer_id)
            else:
                # logging.info('Ответ найден в бд')
                context.user_data['answers'].append(answer_id['id'])
                save_relation(current_question_id, answer_id['id'])

            if len(context.user_data['answers']) < 9:
                await update.message.reply_text(
                    f"Ответ {len(context.user_data['answers'])} сохранен. Введите следующий.")
            else:
                current_question_index = questions.index(
                    {'id': current_question_id, 'question': context.user_data['questions_name']})
                if current_question_index + 1 < len(questions):
                    next_question = questions[current_question_index + 1]
                    context.user_data['current_question'] = next_question['id']
                    context.user_data['questions_name'] = next_question['question']
                    context.user_data['answers'] = get_existing_answers_for_question(
                        next_question['id']) or []  # Очищаем список ответов для следующего вопроса

                    count_answer = len(context.user_data['answers'])

                    if count_answer > 0:
                        await update.message.reply_text(
                            f'Введите ответов - {9 - count_answer} на вопрос №{context.user_data['current_question']} "{context.user_data['questions_name']}", один за другим.')
                    else:
                        await update.message.reply_text(
                            f'Введите 9 ответов на вопрос №{context.user_data['current_question']} "{context.user_data['questions_name']}", один за другим.')
                else:
                    await update.message.reply_text("Все вопросы и ответы успешно сохранены.")
                    context.user_data['state'] = None

# Запуск бота
def main():
    create_tables()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()


if __name__ == '__main__':
    main()