import os
import sys
import importlib
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Load real pandas/openpyxl
sys.modules.pop("pandas", None)
real_pandas = importlib.import_module("pandas")
sys.modules.pop("openpyxl", None)
real_openpyxl = importlib.import_module("openpyxl")
openpyxl = real_openpyxl

from utils import data_manager  # noqa: E402


class DummyMessage:
    def __init__(self):
        self.docs = []

    async def answer_document(self, file, caption=""):
        self.docs.append((file, caption))

    async def edit_text(self, text):
        pass


class DummyCallback:
    def __init__(self):
        self.message = DummyMessage()

    async def answer(self):
        pass


def test_export_excel_file(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "pandas", real_pandas)
    monkeypatch.setitem(sys.modules, "openpyxl", real_openpyxl)
    importlib.reload(data_manager)
    monkeypatch.setattr(data_manager, "DATA_FOLDER", str(tmp_path))

    mod = importlib.reload(importlib.import_module("plugins_surveys.export_plugin"))
    plugin = mod.load_plugin()

    survey = {
        "id": "s1",
        "title": "Survey 1",
        "questions": [{"id": "q1", "text": "Q1", "type": "text_answer"}],
        "responses": [
            {
                "user_id": 1,
                "username": "alice",
                "group_id": 100,
                "group_name": "Group",
                "question_id": "q1",
                "answer": "A1",
                "timestamp": "2024-01-01",
            }
        ],
    }

    cb = DummyCallback()
    asyncio.run(plugin.export_excel(cb, survey))

    fname = tmp_path / "survey_results_Survey_1.xlsx"
    wb = openpyxl.load_workbook(fname)
    ws = wb.active
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    assert header == [
        "User ID",
        "First Name",
        "Last Name",
        "Username",
        "Group ID",
        "Group Name",
        "Survey Date",
        "Survey Name",
        "Question",
        "Answer",
    ]
