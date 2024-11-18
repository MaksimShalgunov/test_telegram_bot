# db.py
from os.path import curdir

from config import DB_PATH
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)

def get_connection():
    return sqlite3.connect(DB_PATH)

def create_tables():
    connection = get_connection()
    cursor = connection.cursor()

    # Создаем таблицу вопросов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL
        )
    ''')

    # Проверяем, есть ли уже данные в таблице
    cursor.execute("SELECT COUNT(*) FROM Questions WHERE question = ?",
                   ("Выберите те ценности, которые вам откликаются",))
    count = cursor.fetchone()[0]

    # Если данных нет, добавляем 12 одинаковых вопросов
    if count == 0:
        question_text = "Выберите те ценности, которые вам откликаются"
        for _ in range(6):
            cursor.execute("INSERT INTO Questions (question) VALUES (?)", (question_text,))
        connection.commit()  # Сохраняем изменения

    # Создаем таблицу ответов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Answer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            answer TEXT NOT NULL
        )
    ''')

    # Создаем таблицу для связей вопросов и ответов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Relation_questions_answer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_question INTEGER,
            id_answer INTEGER,
            FOREIGN KEY (id_question) REFERENCES Questions (id),
            FOREIGN KEY (id_answer) REFERENCES Answer (id)
        )
    ''')

    # Создаем таблицу прогресса пользователя
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS User_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_tg_user INTEGER NOT NULL,
            id_relation INTEGER,
            score INTEGER DEFAULT 0,
            FOREIGN KEY (id_relation) REFERENCES Relation_questions_answer (id)
        )
    ''')

    connection.commit()
    connection.close()

# Функция для сохранения ответа
def save_answer(answer_text):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO Answer (answer) VALUES (?)", (answer_text,))
    connection.commit()
    answer_id = cursor.lastrowid
    connection.close()
    return answer_id

# Функция для сохранения связей вопрос-ответ
def save_relation(question_id, answer_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO Relation_questions_answer (id_question, id_answer) VALUES (?, ?)",
                   (question_id, answer_id))
    connection.commit()
    connection.close()

def get_all_questions():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute('''
        SELECT * FROM Questions q
    ''')
    questions = cursor.fetchall()
    connection.close()

    return [{'id': q[0], 'question': q[1]} for q in questions]

# Функция для получения всех вопросов из базы данных, которые имеют менее 9 ответов на них
def get_unanswered_questions():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute('''
        SELECT q.id, q.question, COUNT(rqa.id_answer) AS answer_count
        FROM Questions q
        LEFT JOIN Relation_questions_answer rqa ON q.id = rqa.id_question
        GROUP BY q.id
        HAVING answer_count < 9 OR answer_count IS NULL
    ''')
    questions = cursor.fetchall()
    connection.close()
    # Преобразуем результаты в список словарей для удобства
    return [{'id': q[0], 'question': q[1]} for q in questions]

# Дополнительная функция для проверки на существующий овтет в таблице Answer
def get_answer(answer_text):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT a.id, a.answer FROM Answer a WHERE a.answer = ?", (answer_text,))
    answer = cursor.fetchone()
    connection.close()

    if answer is None:
        return answer_text
    else:
        return {'id': answer[0], 'answer': answer[1]}

# Дополнительная функция для получения существующих ответов на вопрос
def get_existing_answers_for_question(question_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute('''
        SELECT a.id FROM Answer a
        JOIN Relation_questions_answer rqa ON a.id = rqa.id_answer
        WHERE rqa.id_question = ?
    ''', (question_id,))
    answers = cursor.fetchall()
    connection.close()

    # Преобразуем результаты в список ID ответов
    return [answer[0] for answer in answers] if answers else []

def save_user_progress(user_id, answer_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute('''
        INSERT INTO User_progress (id_tg_user, id_relation, score)
        VALUES (?, ?, ?)
    ''', (user_id, answer_id, 1))
    connection.commit()
    connection.close()


def get_question_and_answers(question_id):
    """
    Получает текст вопроса и список связанных ответов по id вопроса.

    :param question_id: ID вопроса, который нужно извлечь.
    :return: кортеж (вопрос, ответы), где
             - вопрос: текст вопроса,
             - ответы: список словарей с ключами 'id' и 'text' для каждого ответа.
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Получаем текст вопроса по question_id
    cursor.execute("SELECT question FROM Questions WHERE id = ?", (question_id,))
    question = cursor.fetchone()

    if not question:
        connection.close()
        return None, None

    question_text = question[0]

    # Получаем ответы для данного вопроса из таблицы Relation_questions_answer
    cursor.execute('''
        SELECT a.id, a.answer
        FROM Relation_questions_answer rqa
        JOIN Answer a ON rqa.id_answer = a.id
        WHERE rqa.id_question = ?
    ''', (question_id,))
    answers = cursor.fetchall()

    # Преобразуем ответы в список словарей
    answers_list = [{'id': answer[0], 'text': answer[1]} for answer in answers]

    connection.close()
    return question_text, answers_list


# Функции для взаимодействия с базой данных
def get_next_question(user_id, question_id):
    connection = get_connection()
    cursor = connection.cursor()
    next_id = question_id + 1

    cursor.execute('''
        SELECT q.id, q.question
        FROM Questions q
        LEFT JOIN Relation_questions_answer rqa ON q.id = rqa.id_question
        LEFT JOIN User_progress up ON up.id_relation = rqa.id AND up.id_tg_user = ?
        WHERE q.id = ? AND up.id IS NULL
    ''', (user_id, next_id,))

    question_row = cursor.fetchone()

    if question_row:
        question_id, question_text = question_row
        cursor.execute('''
            SELECT rqa.id, a.answer
            FROM Relation_questions_answer rqa
            JOIN Answer a ON rqa.id_answer = a.id
            WHERE rqa.id_question = ?
        ''', (question_id,))
        answers = cursor.fetchall()
        connection.close()
        return question_id, question_text, answers

    connection.close()
    return None, None, None

def update_question_in_db(question_id, new_question):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute('''
        SELECT q.id, q.question
        FROM Questions q
        WHERE q.id = ?
    ''', (question_id,))
    question = cursor.fetchone()

    if question:
        cursor.execute('''
            UPDATE Questions SET question = ? WHERE Questions.id = ?;
        ''', (new_question, question_id))
        connection.commit()
        connection.close()
        return True
    else:
        connection.close()
        return False

def update_answer_in_db(answer_id, new_answer):
    connection = get_connection()
    cursor = connection.cursor()
    #Написать код изменения ответа для конкретного вопроса
