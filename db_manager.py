import sqlite3
import os

DB_FILE = "surveys.db"

def initialize_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Создание таблиц
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            survey_id INTEGER,
            question TEXT NOT NULL,
            FOREIGN KEY (survey_id) REFERENCES surveys(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY,
            title TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_users (
            user_id INTEGER,
            chat_id INTEGER,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    conn.commit()
    conn.close()
    ensure_initial_survey_exists()

def ensure_initial_survey_exists():
    if not survey_exists("первичный"):
        survey_id = add_survey("первичный")
        questions = [
            "Кто вы? (самозанятый, ИП, в найме, собственник)",
            "Откуда вы? (регион деятельности)",
            "Преследуемые цели от вступления в сообщество",
            "Возможная польза для участников сообщества",
            "Что-то от себя/ пожелания/ предложения и прочее"
        ]
        for question in questions:
            add_question(survey_id, question)

def add_group(group_id, title):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO groups (id, title) VALUES (?, ?)", (group_id, title))
    conn.commit()
    conn.close()

def remove_group(group_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM groups WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()

def get_all_groups():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM groups")
    groups = cursor.fetchall()
    conn.close()
    return groups

def survey_exists(survey_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM surveys WHERE name = ?", (survey_name,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def add_survey(survey_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO surveys (name) VALUES (?)", (survey_name,))
    conn.commit()
    survey_id = cursor.lastrowid
    conn.close()
    return survey_id

def add_question(survey_id, question):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO questions (survey_id, question) VALUES (?, ?)", (survey_id, question))
    conn.commit()
    conn.close()

def delete_survey_by_id(survey_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM surveys WHERE id = ?", (survey_id,))
    cursor.execute("DELETE FROM questions WHERE survey_id = ?", (survey_id,))
    conn.commit()
    conn.close()

def get_all_surveys():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM surveys")
    surveys = [row[0] for row in cursor.fetchall()]
    conn.close()
    return surveys

def get_survey_id_by_name(survey_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM surveys WHERE name = ?", (survey_name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_survey_name_by_id(survey_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM surveys WHERE id = ?", (survey_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_questions_by_survey(survey_id, include_ids=False):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if include_ids:
        cursor.execute("SELECT id, question FROM questions WHERE survey_id = ? ORDER BY id ASC", (survey_id,))
    else:
        cursor.execute("SELECT question FROM questions WHERE survey_id = ? ORDER BY id ASC", (survey_id,))
    questions = cursor.fetchall()
    conn.close()
    return questions

def add_user_to_pending(user_id, chat_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO pending_users (user_id, chat_id) VALUES (?, ?)", (user_id, chat_id))
    conn.commit()
    conn.close()

def is_user_pending(user_id, chat_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM pending_users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def remove_user_from_pending(user_id, chat_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()

def get_pending_chats_for_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM pending_users WHERE user_id = ?", (user_id,))
    chats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return chats

def get_group_info_by_chat_id(chat_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM groups WHERE id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else None

# Новые функции для редактирования опросов и вопросов

def update_survey_name(survey_id, new_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE surveys SET name = ? WHERE id = ?", (new_name, survey_id))
    conn.commit()
    conn.close()

def update_question_text(question_id, new_text):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE questions SET question = ? WHERE id = ?", (new_text, question_id))
    conn.commit()
    conn.close()

def delete_question_by_id(question_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()

def add_question_to_survey(survey_id, question_text):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO questions (survey_id, question) VALUES (?, ?)", (survey_id, question_text))
    conn.commit()
    conn.close()
