import importlib
from datetime import datetime
from pathlib import Path
import sys


def test_add_and_get_responses(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE", str(db_path))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    db_module = importlib.reload(importlib.import_module("core.db_manager"))
    db_module.initialize_db()
    poll_id = db_module.add_poll("Test")
    db_module.add_question_to_poll(poll_id, "Q1", "Одиночный выбор", ["a", "b"])
    question = db_module.get_questions_by_poll(poll_id)[0]
    db_module.add_response(poll_id, question["id"], 123, "a", datetime.now())
    responses = db_module.get_responses_by_poll(poll_id)
    assert len(responses) == 1
    assert responses[0]["answer"] == "a"
