# db.py

from config import DB_PATH
import sqlite3
from config import DB_NAME
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
        for _ in range(12):
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