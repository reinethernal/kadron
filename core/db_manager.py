# core/db_manager.py

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE = os.getenv("DATABASE", "database.db")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Таблица опросов (polls)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            anonymous BOOLEAN DEFAULT 0,
            time_limit DATETIME,
            scheduled_time DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Таблица вопросов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id INTEGER,
            text TEXT,
            type TEXT,
            options TEXT,
            FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE
        )
    ''')
    # Таблица тегов для опросов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poll_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id INTEGER,
            tag TEXT,
            FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE
        )
    ''')
    # Таблица групп
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER UNIQUE,
            title TEXT
        )
    ''')
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            category TEXT DEFAULT 'Новичок',
            last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
            warnings INTEGER DEFAULT 0
        )
    ''')
    # Таблица настроек
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    # Таблица обратной связи (отзывы, рейтинг)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id INTEGER,
            user_id INTEGER,
            feedback TEXT,
            rating INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE
        )
    ''')
    # Таблица для pending пользователей (капча)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_users (
            user_id INTEGER,
            chat_id INTEGER,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    # Таблица ответов пользователей на вопросы опросов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            poll_id INTEGER,
            question_id INTEGER,
            user_id INTEGER,
            answer TEXT,
            timestamp DATETIME,
            FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
        )
    ''')
    # Настройки: тестовый режим, приветствие
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value) VALUES ('test_mode', '0')
    ''')
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value) VALUES ('welcome_message', ?)
    ''', (os.getenv("WELCOME_MESSAGE", "Добро пожаловать, {username}!"),))

    # Таблица group_settings для хранения «входного» опроса
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER UNIQUE,
            join_poll_id INTEGER,
            FOREIGN KEY (join_poll_id) REFERENCES polls(id) ON DELETE SET NULL
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

# --- Опросы ---
def add_poll(name: str) -> int:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO polls (name) VALUES (?)', (name,))
    conn.commit()
    poll_id = cursor.lastrowid
    conn.close()
    logger.info(f"Poll '{name}' added with ID {poll_id}.")
    return poll_id

def poll_exists(name: str) -> bool:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM polls WHERE name = ?', (name,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_all_polls() -> List[str]:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM polls')
    polls = [row[0] for row in cursor.fetchall()]
    conn.close()
    return polls

def get_poll_id_by_name(name: str) -> Optional[int]:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM polls WHERE name = ?', (name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_poll_by_id(poll_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, anonymous, time_limit, scheduled_time FROM polls WHERE id = ?', (poll_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'id': result[0],
            'name': result[1],
            'anonymous': bool(result[2]),
            'time_limit': result[3],
            'scheduled_time': result[4]
        }
    return None

def update_poll_anonymous(poll_id: int, anonymous: bool):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('UPDATE polls SET anonymous = ? WHERE id = ?', (1 if anonymous else 0, poll_id))
    conn.commit()
    conn.close()
    logger.info(f"Poll ID {poll_id} anonymous set to {anonymous}.")

def update_poll_time_limit(poll_id: int, time_limit: Optional[datetime]):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    if time_limit is None:
        cursor.execute('UPDATE polls SET time_limit = NULL WHERE id = ?', (poll_id,))
    else:
        cursor.execute('UPDATE polls SET time_limit = ? WHERE id = ?',
                       (time_limit.strftime("%Y-%m-%d %H:%M:%S"), poll_id))
    conn.commit()
    conn.close()
    logger.info(f"Poll ID {poll_id} time limit updated to {time_limit}.")

def schedule_poll(poll_id: int, scheduled_time: datetime):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('UPDATE polls SET scheduled_time = ? WHERE id = ?',
                   (scheduled_time.strftime("%Y-%m-%d %H:%M:%S"), poll_id))
    conn.commit()
    conn.close()
    logger.info(f"Poll ID {poll_id} scheduled for {scheduled_time}.")

def delete_poll_by_id(poll_id: int):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM polls WHERE id = ?', (poll_id,))
    cursor.execute('DELETE FROM questions WHERE poll_id = ?', (poll_id,))
    cursor.execute('DELETE FROM poll_tags WHERE poll_id = ?', (poll_id,))
    conn.commit()
    conn.close()
    logger.info(f"Poll {poll_id} and related data deleted.")

delete_survey_by_id = delete_poll_by_id

def add_poll_tag(poll_id: int, tag: str):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO poll_tags (poll_id, tag) VALUES (?, ?)', (poll_id, tag))
    conn.commit()
    conn.close()
    logger.info(f"Tag '{tag}' added to poll ID {poll_id}.")

def get_poll_tags(poll_id: int) -> List[str]:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT tag FROM poll_tags WHERE poll_id = ?', (poll_id,))
    tags = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tags

def filter_polls(keyword: str) -> List[str]:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT p.name FROM polls p
        LEFT JOIN poll_tags t ON p.id = t.poll_id
        WHERE p.name LIKE ? OR t.tag LIKE ?
    ''', (f'%{keyword}%', f'%{keyword}%'))
    polls = [row[0] for row in cursor.fetchall()]
    conn.close()
    return polls

# Вопросы
def add_question_to_poll(poll_id: int, text: str, q_type: str, options: Optional[List[str]] = None):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    options_str = ','.join(options) if options else None
    cursor.execute('INSERT INTO questions (poll_id, text, type, options) VALUES (?, ?, ?, ?)',
                   (poll_id, text, q_type, options_str))
    conn.commit()
    conn.close()
    logger.info(f"Question added to poll {poll_id}.")

def get_questions_by_poll(poll_id: int) -> List[Dict]:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, text, type, options FROM questions WHERE poll_id = ?', (poll_id,))
    questions = []
    for row in cursor.fetchall():
        questions.append({
            'id': row[0],
            'text': row[1],
            'type': row[2],
            'options': row[3].split(',') if row[3] else []
        })
    conn.close()
    return questions

def update_question_text(question_id: int, new_text: str):
    """Update the text of a question by its ID."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('UPDATE questions SET text = ? WHERE id = ?', (new_text, question_id))
    conn.commit()
    conn.close()
    logger.info(f"Question {question_id} text updated to '{new_text}'.")

def update_question_options(question_id: int, options: List[str]):
    """Update the options for a question by its ID."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    options_str = ','.join(options) if options else None
    cursor.execute('UPDATE questions SET options = ? WHERE id = ?', (options_str, question_id))
    conn.commit()
    conn.close()
    logger.info(f"Question {question_id} options updated.")

def delete_question_by_id(question_id: int):
    """Delete a question and its answers by ID."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
    conn.commit()
    conn.close()
    logger.info(f"Question {question_id} deleted.")

# --- Группы ---
def add_group(group_id: int, title: str):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO groups (group_id, title) VALUES (?, ?)', (group_id, title))
    conn.commit()
    conn.close()
    logger.info(f"Group '{title}' with ID {group_id} added.")

def get_all_groups() -> List[Dict]:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT group_id, title FROM groups')
    groups = [{'group_id': row[0], 'title': row[1]} for row in cursor.fetchall()]
    conn.close()
    return groups

# --- Настройка «входного» опроса для группы ---
def set_group_join_poll(group_id: int, poll_id: Optional[int]):
    """Устанавливаем (или меняем) опрос, который будет отправляться при вступлении в группу."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO group_settings (group_id, join_poll_id)
        VALUES (?, ?)
        ON CONFLICT(group_id)
        DO UPDATE SET join_poll_id=excluded.join_poll_id
    ''', (group_id, poll_id))
    conn.commit()
    conn.close()
    logger.info(f"Group {group_id} join_poll set to {poll_id}.")

def get_group_join_poll(group_id: int) -> Optional[int]:
    """Возвращает ID опроса, который будет отправлен при вступлении в группу (или None)."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT join_poll_id FROM group_settings WHERE group_id=?', (group_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# --- Пользователи ---
def update_user_activity(user_id: int, username: Optional[str] = None):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    if username:
        cursor.execute('''
            INSERT INTO users (user_id, username, last_activity) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_activity = excluded.last_activity, username = excluded.username
        ''', (user_id, username, datetime.now()))
    else:
        cursor.execute('''
            INSERT INTO users (user_id, last_activity) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_activity = excluded.last_activity
        ''', (user_id, datetime.now()))
    conn.commit()
    conn.close()
    logger.info(f"User ID {user_id} activity updated.")

def get_active_users() -> int:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    threshold = datetime.now() - timedelta(days=30)
    cursor.execute('SELECT COUNT(*) FROM users WHERE last_activity >= ?', (threshold,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_inactive_users(days: int = 30) -> List[Dict]:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    threshold = datetime.now() - timedelta(days=days)
    cursor.execute('SELECT user_id FROM users WHERE last_activity < ?', (threshold,))
    users = [{'user_id': row[0]} for row in cursor.fetchall()]
    conn.close()
    return users

# --- Настройки ---
def set_welcome_message(message: str):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', ('welcome_message', message))
    conn.commit()
    conn.close()
    logger.info("Welcome message updated.")

def get_welcome_message() -> Optional[str]:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', ('welcome_message',))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_test_mode(enabled: bool):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', ('test_mode', '1' if enabled else '0'))
    conn.commit()
    conn.close()
    logger.info(f"Test mode set to {enabled}.")

def is_test_mode_enabled() -> bool:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', ('test_mode',))
    result = cursor.fetchone()
    conn.close()
    return result[0] == '1' if result else False

# --- Pending пользователи (капча) ---
def add_user_to_pending(user_id: int, chat_id: int):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO pending_users (user_id, chat_id) VALUES (?, ?)', (user_id, chat_id))
    conn.commit()
    conn.close()
    logger.info(f"User ID {user_id} added to pending in chat {chat_id}.")

def remove_user_from_pending(user_id: int, chat_id: int):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM pending_users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    conn.commit()
    conn.close()
    logger.info(f"User ID {user_id} removed from pending in chat {chat_id}.")

def is_user_pending(user_id: int, chat_id: int) -> bool:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM pending_users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_pending_chats_for_user(user_id: int) -> List[int]:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM pending_users WHERE user_id = ?', (user_id,))
    chats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return chats

def get_scheduled_surveys() -> List[Dict]:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, scheduled_time FROM polls WHERE scheduled_time IS NOT NULL')
    polls = []
    for row in cursor.fetchall():
        polls.append({
            'id': row[0],
            'name': row[1],
            'scheduled_time': row[2]
        })
    conn.close()
    return polls

# --- Responses ---
def add_response(poll_id: int, question_id: int, user_id: Optional[int], answer: str, timestamp: datetime):
    """Сохраняет ответ пользователя на вопрос."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    ts = timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(timestamp, datetime) else str(timestamp)
    cursor.execute(
        'INSERT INTO responses (poll_id, question_id, user_id, answer, timestamp) VALUES (?, ?, ?, ?, ?)',
        (poll_id, question_id, user_id, answer, ts)
    )
    conn.commit()
    conn.close()
    logger.info(f"Response added for poll {poll_id}, question {question_id}.")


def get_responses_by_poll(poll_id: int) -> List[Dict]:
    """Возвращает все ответы для указанного опроса."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT poll_id, question_id, user_id, answer, timestamp FROM responses WHERE poll_id = ?',
        (poll_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    responses = []
    for row in rows:
        responses.append({
            'poll_id': row[0],
            'question_id': row[1],
            'user_id': row[2],
            'answer': row[3],
            'timestamp': row[4],
        })
    return responses
