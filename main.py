from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

from config import TELEGRAM_TOKEN, ADMIN_USER_TELEGRAM_ID, DB_PATH
from db.db import create_tables, save_answer, save_relation, get_unanswered_questions, get_answer
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
        # Получаем все вопросы, для которых нет записей в Relation_questions_answer
        unanswered_questions = get_unanswered_questions()
        if unanswered_questions:
            # Сохраняем вопросы в контексте
            context.user_data['questions'] = unanswered_questions
            context.user_data['questions_name'] = unanswered_questions[0]['question']  # Название текущего вопроса
            context.user_data['current_question'] = unanswered_questions[0]['id']  # Индекс текущего вопроса
            context.user_data['answers'] = []  # Список для хранения ответов на текущий вопрос
            context.user_data['state'] = ADDING_ANSWERS

            # Предлагаем ввести ответы для первого вопроса
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
            current_question_index = context.user_data['current_question']
            questions = context.user_data['questions']

            # Проверка ответа на существубщий в бд
            answer_id = get_answer(text)

            logging.info(f"Проверка ответа на существующий: {answer_id}")

            if answer_id == text:
                logging.info('Ответ не найден в бд')

                # Добавляем ответ в базу данных
                answer_id = save_answer(text)
                context.user_data['answers'].append(answer_id)
                save_relation(current_question_index, answer_id)  # Сохраняем связь вопрос-ответ
            else:
                logging.info('Ответ найден в бд')

                # Добавляем запись в релейшн таблицу с найденым ответом
                context.user_data['answers'].append(answer_id['id'])
                save_relation(current_question_index, answer_id['id'])  # Сохраняем связь вопрос-ответ

            # Проверяем, введено ли 9 ответов
            if len(context.user_data['answers']) < 9:
                await update.message.reply_text(
                    f"Ответ {len(context.user_data['answers'])} сохранен. Введите следующий.")
            else:
                # Все ответы для текущего вопроса введены, переходим к следующему вопросу
                if current_question_index + 1 < len(questions):
                    context.user_data['current_question'] += 1
                    context.user_data['answers'] = []  # Очищаем список ответов для следующего вопроса
                    await update.message.reply_text(
                        f'Введите 9 ответов на вопрос №{context.user_data['current_question']}  "{context.user_data['questions_name']}", один за другим.')
                else:
                    await update.message.reply_text("Все вопросы и ответы успешно сохранены.")
                    context.user_data['state'] = None  # Завершаем процесс

# Запуск бота
def main():
    create_tables()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()


if __name__ == '__main__':
    main()