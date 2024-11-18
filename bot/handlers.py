from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from config import TELEGRAM_TOKEN, ADMIN_USER_TELEGRAM_ID
from db.db import (save_answer, save_relation, get_answer,
                   get_existing_answers_for_question, get_question_and_answers, save_user_progress, get_next_question,
                   get_all_questions, update_question_in_db, update_answer_in_db)
from bot.test_flow import create_answer_buttons

import logging

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

async def admin_menu_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    action = query.data

    if action == "view_questions":
        await view_questions(update, context)
    elif action == "view_answers":
        await view_answers(update, context)
    elif action == "edit_question":
        await edit_question_menu(update, context)
    elif action == "edit_answer":
        await edit_answer_menu(update, context)
    elif action == "create_answer":
        await create_answer_menu(update, context)
    await query.answer()

async def view_questions(update: Update, context: CallbackContext) -> None:
    questions = get_all_questions()  # Получение всех вопросов из базы
    if not questions:
        await update.callback_query.message.reply_text("Вопросы не найдены.")
        return

    question_list = "\n".join([f"Вопрос №{q['id']} - {q['question']}" for q in questions])
    await update.callback_query.message.reply_text(f"Список вопросов:\n{question_list}")

async def view_answers(update: Update, context: CallbackContext) -> None:
    questions = get_all_questions()  # Получение всех вопросов из базы
    buttons = [[InlineKeyboardButton(f"Вопрос №{q['id']}", callback_data=f"view_answers_{q['id']}")] for q in questions]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.callback_query.message.reply_text("Выберите вопрос:", reply_markup=reply_markup)

async def display_answers(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    question_id = int(query.data.split("_")[-1])

    question, answers = get_question_and_answers(question_id)  # Получение ответов по вопросу

    if not answers:
        await query.message.reply_text("Ответы не найдены.")
    else:
        answer_list = "\n".join([f"{a['id']} - {a['text']}" for a in answers])
        await query.message.reply_text(f"Ответы на вопрос №{question_id}:\n{answer_list}")
    await query.answer()

async def edit_question_menu(update: Update, context: CallbackContext) -> None:
    questions = get_all_questions()
    buttons = [[InlineKeyboardButton(f"Вопрос №{q['id']}", callback_data=f"edit_question_{q['id']}")] for q in questions]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.callback_query.message.reply_text("Выберите вопрос для редактирования:", reply_markup=reply_markup)

async def edit_question(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    question_id = int(query.data.split("_")[-1])
    context.user_data["edit_question_id"] = question_id

    await query.message.reply_text(f"Введите новый текст для вопроса №{question_id}:")
    context.user_data["state"] = "awaiting_new_question"
    logging.info(context.user_data["state"])
    await query.answer()

async def handle_text_input(update: Update, context: CallbackContext) -> None:
    if context.user_data.get("state") == "awaiting_new_question":
        new_question = update.message.text
        question_id = context.user_data["edit_question_id"]
        if update_question_in_db(question_id, new_question):  # Обновление вопроса в базе
            await update.message.reply_text(f"Вопрос №{question_id} успешно обновлен.")
        else:
            await update.message.reply_text(f"Вопрос №{question_id} не удалось обновить. Запись не найдена")
        context.user_data.clear()

    elif context.user_data.get("state") == "awaiting_new_answer":
        new_answer = update.message.text
        answer_id = context.user_data["edit_answer_id"]
        if update_answer_in_db(answer_id, new_answer):  # Логика обновления ответа
            await update.message.reply_text(f"Ответ успешно обновлен.")
        else:
            await update.message.reply_text(f"Ответ {new_answer} не удалось сохранить.")
        context.user_data.clear()
