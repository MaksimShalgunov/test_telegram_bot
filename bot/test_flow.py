import logging

from db.db import get_question_and_answers, save_user_progress, get_next_question
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

# Константы для состояния
ASKING_QUESTIONS = 1


# Функция для начала теста
async def start_test(update, context):
    user_id = update.effective_user.id
    logging.info("Функция start_test вызвана.")
    # Получаем первый вопрос и ответы
    question, answers = get_question_and_answers(1)  # Например, id=1 для первого вопроса

    context.user_data['current_question_id'] = 1

    # Генерируем кнопки ответов
    reply_markup = create_answer_buttons(answers)

    # Проверяем, что вызвало событие: сообщение или callback_query
    if update.message:
        await update.message.reply_text(f"Вопрос №{context.user_data['current_question_id']} - {question}", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(f"Вопрос №{context.user_data['current_question_id']} - {question}", reply_markup=reply_markup)

# Функция для создания кнопок ответов
def create_answer_buttons(answers, selected_answers=None):
    if selected_answers is None:
        selected_answers = set()

    buttons = [
        [InlineKeyboardButton(
            f"{'✔️ ' if answer['id'] in selected_answers else ''}{answer['text']}",
            callback_data=f"answer_{answer['id']}"
        )] for answer in answers
    ]
    buttons.append([InlineKeyboardButton("Ответить", callback_data="submit_answer")])
    return InlineKeyboardMarkup(buttons)
