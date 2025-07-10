import importlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import sys


def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "analytics.db"
    monkeypatch.setenv("DATABASE", str(db_path))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    db_module = importlib.reload(importlib.import_module("core.db_manager"))
    db_module.initialize_db()

    now = datetime.now()

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE messages (chat_id INTEGER, user_id INTEGER, timestamp DATETIME)"
        )
        cur.execute(
            "CREATE TABLE reactions (chat_id INTEGER, user_id INTEGER, timestamp DATETIME)"
        )

        # Users for activity stats
        cur.executemany(
            "INSERT INTO users (user_id, last_activity) VALUES (?, ?)",
            [
                (1, now - timedelta(days=1)),
                (2, now - timedelta(days=3)),
                (3, now - timedelta(hours=12)),
            ],
        )
        conn.commit()

    # Survey with responses and feedback
    poll_id = db_module.add_poll("P")
    db_module.add_question_to_poll(poll_id, "Q", "single_choice", ["a", "b"])
    q = db_module.get_questions_by_poll(poll_id)[0]

    db_module.add_response(poll_id, q["id"], 1, "a", now)
    db_module.add_response(poll_id, q["id"], 1, "a", now + timedelta(seconds=5))
    db_module.add_response(poll_id, q["id"], 2, "b", now + timedelta(seconds=10))
    db_module.add_response(poll_id, q["id"], 2, "b", now + timedelta(seconds=40))

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO messages VALUES (?,?,?)",
            [
                (123, 1, now),
                (123, 2, now),
                (123, 1, now - timedelta(days=1)),
            ],
        )
        cur.executemany(
            "INSERT INTO reactions VALUES (?,?,?)",
            [
                (123, 1, now),
                (123, 2, now),
            ],
        )
        cur.executemany(
            "INSERT INTO feedback (poll_id, user_id, feedback, rating, created_at) VALUES (?,?,?,?,?)",
            [
                (poll_id, 1, "good", 5, now),
                (poll_id, 1, "ok", 4, now),
                (poll_id, 2, "bad", 3, now),
            ],
        )
        conn.commit()

    return db_module, poll_id


def test_get_survey_statistics(tmp_path, monkeypatch):
    db, poll_id = setup_db(tmp_path, monkeypatch)
    stats = db.get_survey_statistics(poll_id)
    assert stats.participant_count == 2
    assert stats.option_distribution == {"a": 2, "b": 2}
    assert round(stats.average_duration, 1) == 17.5


def test_get_group_activity(tmp_path, monkeypatch):
    db, _ = setup_db(tmp_path, monkeypatch)
    activity = db.get_group_activity(123, 2)
    assert activity.message_count == 3
    assert activity.new_users == 2
    assert activity.reactions == 2


def test_get_user_ratings(tmp_path, monkeypatch):
    db, _ = setup_db(tmp_path, monkeypatch)
    ratings = db.get_user_ratings(123)
    ratings = sorted(ratings, key=lambda r: r.user_id)
    assert ratings[0].user_id == 1
    assert round(ratings[0].rating, 1) == 4.5
    assert ratings[0].feedback_count == 2
    assert ratings[1].user_id == 2
    assert round(ratings[1].rating, 1) == 3.0
    assert ratings[1].feedback_count == 1
