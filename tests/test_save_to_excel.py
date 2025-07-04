import os
import sys
import importlib
from pathlib import Path
import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Load real pandas, replacing any stub from conftest
sys.modules.pop('pandas', None)
real_pandas = importlib.import_module('pandas')
sys.modules.pop('openpyxl', None)
real_openpyxl = importlib.import_module('openpyxl')
openpyxl = real_openpyxl

from utils import data_manager


def test_excel_header(tmp_path, monkeypatch):
    # Ensure real pandas and openpyxl are used
    monkeypatch.setitem(sys.modules, 'pandas', real_pandas)
    monkeypatch.setitem(sys.modules, 'openpyxl', real_openpyxl)
    importlib.reload(data_manager)
    monkeypatch.setattr(data_manager, 'DATA_FOLDER', str(tmp_path))
    os.makedirs(tmp_path, exist_ok=True)
    filename = data_manager.save_to_excel(
        user_id=1,
        first_name='F',
        last_name='L',
        username='u',
        group_id=10,
        group_name='g',
        survey_date='2024-01-01',
        responses=[{'question': 'Q1', 'answer': 'A1'}],
        survey_name='Test Survey',
    )
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    assert header == [
        'User ID',
        'First Name',
        'Last Name',
        'Username',
        'Group ID',
        'Group Name',
        'Survey Date',
        'Survey Name',
        'Question',
        'Answer',
    ]
