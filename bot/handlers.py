from telegram import Update
from telegram.ext import CallbackContext

from config import TELEGRAM_TOKEN, ADMIN_USER_TELEGRAM_ID
from db.db import (save_answer, save_relation, get_answer,
                   get_existing_answers_for_question, get_question_and_answers, save_user_progress, get_next_question)
from bot.test_flow import create_answer_buttons

# Настраиваем Telegram Bot Token и ID администратора
ADMIN_USER_ID = ADMIN_USER_TELEGRAM_ID
BOT_TOKEN = TELEGRAM_TOKEN

# Состояния бота
ADDING_QUESTION, ADDING_ANSWERS = range(2)

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    text = update.message.text
    state = context.user_data.get('state')

    if str(user_id) == ADMIN_USER_ID:
        if state == ADDING_ANSWERS:
            current_question_id = context.user_data['current_question']
            questions = context.user_data['questions']

            answer_id = get_answer(text)

            if answer_id == text:
                answer_id = save_answer(text)
                context.user_data['answers'].append(answer_id)
                save_relation(current_question_id, answer_id)
            else:
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


# Функция для обработки ответов пользователя
async def handle_user_answer(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if not context.user_data.get('selected_answers'):
        context.user_data['selected_answers'] = set()

    if data.startswith("answer_"):
        # Обработка выбора ответа
        answer_id = int(data.split("_")[1])
        selected_answers = context.user_data['selected_answers']

        if answer_id in selected_answers:
            selected_answers.remove(answer_id)  # Убираем выбор
        else:
            selected_answers.add(answer_id)  # Добавляем выбор

        # Получаем текущий вопрос и ответы
        current_question_id = context.user_data.get('current_question_id')
        question, answers = get_question_and_answers(current_question_id)

        # Обновляем текст кнопок
        reply_markup = create_answer_buttons(answers, selected_answers)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
        await query.answer("Ответ обновлен.")

    elif data == "submit_answer":
        # Сохраняем все выбранные ответы в базу
        selected_answers = context.user_data.get('selected_answers', set())
        for answer_id in selected_answers:
            save_user_progress(user_id, answer_id)

        # Очищаем выбранные ответы
        context.user_data['selected_answers'] = set()

        # Логика для перехода к следующему вопросу
        next_question_id, next_question_text, next_answers = get_next_question(user_id, context.user_data['current_question_id'])
        if next_question_id:
            context.user_data['current_question_id'] = next_question_id
            question, answers = get_question_and_answers(next_question_id)
            reply_markup = create_answer_buttons(answers)
            await query.edit_message_text(f"Вопрос №{next_question_id} - {question}", reply_markup=reply_markup)
        else:
            await query.edit_message_text("Тест завершен. Спасибо за участие!")