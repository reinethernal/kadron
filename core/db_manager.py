# core/db_manager.py

import sqlite3
from sqlalchemy import create_engine, func, distinct
from sqlalchemy.orm import sessionmaker
from core.models import Base, Poll, Question, User, Response, Message
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE = os.getenv("DATABASE", "database.db")
logger = logging.getLogger(__name__)

engine = create_engine(f"sqlite:///{DATABASE}")
SessionLocal = sessionmaker(bind=engine)


@dataclass
class SurveyStats:
    participant_count: int
    option_distribution: Dict[str, int]
    average_duration: float


@dataclass
class ActivityStats:
    message_count: int
    new_users: int
    reactions: int


@dataclass
class UserRating:
    user_id: int
    rating: float
    feedback_count: int


def initialize_db():
    """Create database tables."""
    Base.metadata.create_all(
        engine,
        tables=[
            Poll.__table__,
            Question.__table__,
            User.__table__,
            Response.__table__,
        ],
    )
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Таблица тегов для опросов
        # Таблица тегов для опросов
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS poll_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id INTEGER,
                tag TEXT,
                FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE
            )
        """
        )
        # Таблица групп
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER UNIQUE,
                title TEXT
            )
        """
        )
        # Таблица настроек
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )
        # Таблица обратной связи (отзывы, рейтинг)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id INTEGER,
                user_id INTEGER,
                feedback TEXT,
                rating INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE
            )
        """
        )
        # Таблица для pending пользователей (капча)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_users (
                user_id INTEGER,
                chat_id INTEGER,
                PRIMARY KEY (user_id, chat_id)
            )
        """
        )
        # Настройки: тестовый режим, приветствие
        cursor.execute(
            """
            INSERT OR IGNORE INTO settings (key, value) VALUES ('test_mode', '0')
        """
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO settings (key, value) VALUES ('welcome_message', ?)
        """,
            (os.getenv("WELCOME_MESSAGE", "Добро пожаловать, {username}!"),),
        )

        # Таблица group_settings для хранения «входного» опроса
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS group_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER UNIQUE,
                join_poll_id INTEGER,
                FOREIGN KEY (join_poll_id) REFERENCES polls(id) ON DELETE SET NULL
            )
        """
        )

    logger.info("Database initialized successfully.")


# --- Опросы ---
def add_poll(name: str) -> int:
    with SessionLocal() as session:
        poll = Poll(name=name)
        session.add(poll)
        session.commit()
        session.refresh(poll)
        poll_id = poll.id
    logger.info(f"Poll '{name}' added with ID {poll_id}.")
    return poll_id


def poll_exists(name: str) -> bool:
    with SessionLocal() as session:
        return session.query(Poll.id).filter_by(name=name).first() is not None


def get_all_polls() -> List[str]:
    with SessionLocal() as session:
        return [p.name for p in session.query(Poll).all()]


def get_poll_id_by_name(name: str) -> Optional[int]:
    with SessionLocal() as session:
        poll = session.query(Poll).filter_by(name=name).first()
        return poll.id if poll else None


def get_poll_by_id(poll_id: int) -> Optional[Dict]:
    with SessionLocal() as session:
        poll = session.query(Poll).get(poll_id)
        if poll:
            return {
                "id": poll.id,
                "name": poll.name,
                "anonymous": bool(poll.anonymous),
                "time_limit": poll.time_limit,
                "scheduled_time": poll.scheduled_time,
            }
        return None


def update_poll_anonymous(poll_id: int, anonymous: bool):
    with SessionLocal() as session:
        session.query(Poll).filter(Poll.id == poll_id).update({"anonymous": anonymous})
        session.commit()
    logger.info(f"Poll ID {poll_id} anonymous set to {anonymous}.")


def update_poll_time_limit(poll_id: int, time_limit: Optional[datetime]):
    with SessionLocal() as session:
        session.query(Poll).filter(Poll.id == poll_id).update(
            {"time_limit": time_limit}
        )
        session.commit()
    logger.info(f"Poll ID {poll_id} time limit updated to {time_limit}.")


def schedule_poll(poll_id: int, scheduled_time: datetime):
    with SessionLocal() as session:
        session.query(Poll).filter(Poll.id == poll_id).update(
            {"scheduled_time": scheduled_time}
        )
        session.commit()
    logger.info(f"Poll ID {poll_id} scheduled for {scheduled_time}.")


def delete_poll_by_id(poll_id: int):
    with SessionLocal() as session:
        session.query(Poll).filter(Poll.id == poll_id).delete()
        session.query(Question).filter(Question.poll_id == poll_id).delete()
        session.commit()
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM poll_tags WHERE poll_id = ?", (poll_id,))
    logger.info(f"Poll {poll_id} and related data deleted.")


delete_survey_by_id = delete_poll_by_id


def add_poll_tag(poll_id: int, tag: str):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO poll_tags (poll_id, tag) VALUES (?, ?)", (poll_id, tag)
        )
    logger.info(f"Tag '{tag}' added to poll ID {poll_id}.")


def get_poll_tags(poll_id: int) -> List[str]:
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tag FROM poll_tags WHERE poll_id = ?", (poll_id,))
        tags = [row[0] for row in cursor.fetchall()]
    return tags


def filter_polls(keyword: str) -> List[str]:
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
        SELECT DISTINCT p.name FROM polls p
        LEFT JOIN poll_tags t ON p.id = t.poll_id
        WHERE p.name LIKE ? OR t.tag LIKE ?
    """,
            (f"%{keyword}%", f"%{keyword}%"),
        )
        polls = [row[0] for row in cursor.fetchall()]
    return polls


# Вопросы
def add_question_to_poll(
    poll_id: int, text: str, q_type: str, options: Optional[List[str]] = None
):
    with SessionLocal() as session:
        options_str = ",".join(options) if options else None
        q = Question(poll_id=poll_id, text=text, type=q_type, options=options_str)
        session.add(q)
        session.commit()
    logger.info(f"Question added to poll {poll_id}.")


def get_questions_by_poll(poll_id: int) -> List[Dict]:
    with SessionLocal() as session:
        questions = session.query(Question).filter(Question.poll_id == poll_id).all()
        result = []
        for q in questions:
            result.append(
                {
                    "id": q.id,
                    "text": q.text,
                    "type": q.type,
                    "options": q.options.split(",") if q.options else [],
                }
            )
        return result


def update_question_text(question_id: int, new_text: str):
    """Update the text of a question by its ID."""
    with SessionLocal() as session:
        session.query(Question).filter(Question.id == question_id).update(
            {"text": new_text}
        )
        session.commit()
    logger.info(f"Question {question_id} text updated to '{new_text}'.")


def update_question_options(question_id: int, options: List[str]):
    """Update the options for a question by its ID."""
    with SessionLocal() as session:
        options_str = ",".join(options) if options else None
        session.query(Question).filter(Question.id == question_id).update(
            {"options": options_str}
        )
        session.commit()
    logger.info(f"Question {question_id} options updated.")


def delete_question_by_id(question_id: int):
    """Delete a question and its answers by ID."""
    with SessionLocal() as session:
        session.query(Question).filter(Question.id == question_id).delete()
        session.commit()
    logger.info(f"Question {question_id} deleted.")


# --- Группы ---
def add_group(group_id: int, title: str):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO groups (group_id, title) VALUES (?, ?)",
            (group_id, title),
        )
    logger.info(f"Group '{title}' with ID {group_id} added.")


def get_all_groups() -> List[Dict]:
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT group_id, title FROM groups")
        groups = [{"group_id": row[0], "title": row[1]} for row in cursor.fetchall()]
    return groups


# --- Настройка «входного» опроса для группы ---
def set_group_join_poll(group_id: int, poll_id: Optional[int]):
    """Устанавливаем (или меняем) опрос, который будет отправляться при вступлении в группу."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO group_settings (group_id, join_poll_id)
            VALUES (?, ?)
            ON CONFLICT(group_id)
            DO UPDATE SET join_poll_id=excluded.join_poll_id
        """,
            (group_id, poll_id),
        )
    logger.info(f"Group {group_id} join_poll set to {poll_id}.")


def get_group_join_poll(group_id: int) -> Optional[int]:
    """Возвращает ID опроса, который будет отправлен при вступлении в группу (или None)."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT join_poll_id FROM group_settings WHERE group_id=?", (group_id,)
        )
        result = cursor.fetchone()
    return result[0] if result else None


# --- Пользователи ---
def update_user_activity(user_id: int, username: Optional[str] = None):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        if username:
            cursor.execute(
                """
                INSERT INTO users (user_id, username, last_activity) VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET last_activity = excluded.last_activity, username = excluded.username
            """,
                (user_id, username, datetime.now()),
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (user_id, last_activity) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET last_activity = excluded.last_activity
            """,
                (user_id, datetime.now()),
            )
    logger.info(f"User ID {user_id} activity updated.")


def get_active_users() -> int:
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        threshold = datetime.now() - timedelta(days=30)
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE last_activity >= ?", (threshold,)
        )
        result = cursor.fetchone()
    return result[0] if result else 0


def get_inactive_users(days: int = 30) -> List[Dict]:
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        threshold = datetime.now() - timedelta(days=days)
        cursor.execute(
            "SELECT user_id FROM users WHERE last_activity < ?", (threshold,)
        )
        users = [{"user_id": row[0]} for row in cursor.fetchall()]
    return users


# --- Настройки ---
def set_welcome_message(message: str):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("welcome_message", message),
        )
    logger.info("Welcome message updated.")


def get_welcome_message() -> Optional[str]:
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", ("welcome_message",))
        result = cursor.fetchone()
    return result[0] if result else None


def set_test_mode(enabled: bool):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("test_mode", "1" if enabled else "0"),
        )
    logger.info(f"Test mode set to {enabled}.")


def is_test_mode_enabled() -> bool:
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", ("test_mode",))
        result = cursor.fetchone()
    return result[0] == "1" if result else False


# --- Pending пользователи (капча) ---
def add_user_to_pending(user_id: int, chat_id: int):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO pending_users (user_id, chat_id) VALUES (?, ?)",
            (user_id, chat_id),
        )
    logger.info(f"User ID {user_id} added to pending in chat {chat_id}.")


def remove_user_from_pending(user_id: int, chat_id: int):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM pending_users WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        )
    logger.info(f"User ID {user_id} removed from pending in chat {chat_id}.")


def is_user_pending(user_id: int, chat_id: int) -> bool:
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM pending_users WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        )
        result = cursor.fetchone()
    return result is not None


def get_pending_chats_for_user(user_id: int) -> List[int]:
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT chat_id FROM pending_users WHERE user_id = ?", (user_id,)
        )
        chats = [row[0] for row in cursor.fetchall()]
    return chats


def get_scheduled_surveys() -> List[Dict]:
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, scheduled_time FROM polls WHERE scheduled_time IS NOT NULL"
        )
        polls = []
        for row in cursor.fetchall():
            polls.append({"id": row[0], "name": row[1], "scheduled_time": row[2]})
    return polls


# --- Responses ---
def add_response(
    poll_id: int,
    question_id: int,
    user_id: Optional[int],
    answer: str,
    timestamp: datetime,
):
    """Сохраняет ответ пользователя на вопрос."""
    with SessionLocal() as session:
        ts = (
            timestamp
            if isinstance(timestamp, datetime)
            else datetime.fromisoformat(str(timestamp))
        )
        resp = Response(
            poll_id=poll_id,
            question_id=question_id,
            user_id=user_id,
            answer=answer,
            timestamp=ts,
        )
        session.add(resp)
        session.commit()
    logger.info(f"Response added for poll {poll_id}, question {question_id}.")


def get_responses_by_poll(poll_id: int) -> List[Dict]:
    """Возвращает все ответы для указанного опроса."""
    with SessionLocal() as session:
        rows = session.query(Response).filter(Response.poll_id == poll_id).all()
        responses = []
        for r in rows:
            responses.append(
                {
                    "poll_id": r.poll_id,
                    "question_id": r.question_id,
                    "user_id": r.user_id,
                    "answer": r.answer,
                    "timestamp": r.timestamp,
                }
            )
        return responses


def get_survey_statistics(survey_id: int) -> SurveyStats:
    """Return statistics for a survey."""
    with SessionLocal() as session:
        participants = (
            session.query(func.count(distinct(Response.user_id)))
            .filter(Response.poll_id == survey_id)
            .scalar()
            or 0
        )

        rows = (
            session.query(Response.answer, func.count())
            .filter(Response.poll_id == survey_id)
            .group_by(Response.answer)
            .all()
        )
        distribution = {r[0]: r[1] for r in rows}

        subq = (
            session.query(
                (
                    func.julianday(func.max(Response.timestamp))
                    - func.julianday(func.min(Response.timestamp))
                ).label("duration")
            )
            .filter(Response.poll_id == survey_id)
            .group_by(Response.user_id)
            .having(Response.user_id.isnot(None))
            .subquery()
        )
        avg = session.query(func.avg(subq.c.duration)).scalar()
        avg_duration = float(avg * 86400) if avg is not None else 0.0

        return SurveyStats(participants, distribution, avg_duration)


def get_group_activity(chat_id: int, days: int) -> ActivityStats:
    """Return group activity statistics."""
    start = datetime.now() - timedelta(days=days)
    with SessionLocal() as session, sqlite3.connect(DATABASE) as conn:
        try:
            messages = (
                session.query(func.count())
                .select_from(Message)
                .filter(Message.chat_id == chat_id, Message.timestamp >= start)
                .scalar()
            )
        except Exception:
            messages = 0

        try:
            new_users = (
                session.query(func.count())
                .select_from(User)
                .filter(User.last_activity >= start)
                .scalar()
            )
        except Exception:
            new_users = 0

        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM reactions WHERE chat_id=? AND timestamp>=?",
                (chat_id, start),
            )
            reactions = cur.fetchone()[0]
        except sqlite3.OperationalError:
            reactions = 0

    return ActivityStats(messages or 0, new_users or 0, reactions)


def get_user_ratings(chat_id: int) -> List[UserRating]:
    """Return average ratings per user."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT user_id, AVG(rating), COUNT(*) FROM feedback WHERE chat_id=? GROUP BY user_id",
                (chat_id,),
            )
        except sqlite3.OperationalError:
            cursor.execute(
                "SELECT user_id, AVG(rating), COUNT(*) FROM feedback GROUP BY user_id"
            )
        rows = cursor.fetchall()

    return [
        UserRating(r[0], float(r[1]) if r[1] is not None else 0.0, r[2]) for r in rows
    ]
