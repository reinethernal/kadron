import importlib
import pytest


@pytest.mark.parametrize("value", ["123,456", "[123,456]"])
def test_admin_ids_parsing(value, monkeypatch):
    monkeypatch.setenv("ADMIN_IDS", value)
    admin_module = importlib.reload(importlib.import_module("plugins.admin.admin_plugin"))
    edit_module = importlib.reload(
        importlib.import_module("plugins.surveys.edit_question_plugin")
    )
    assert admin_module.ADMIN_IDS == [123, 456]
    assert edit_module.ADMIN_IDS == [123, 456]
