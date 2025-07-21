import asyncio
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aiogram  # noqa: E402
from plugin_manager import PluginManager  # noqa: E402
import plugin_manager  # noqa: E402


class DummyBot(aiogram.Bot):
    pass


def test_load_plugin_import_error_logs_and_raises(tmp_path, monkeypatch):
    pkg_dir = tmp_path / "badpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.chdir(tmp_path)

    dp = aiogram.Dispatcher()
    router = aiogram.Router()
    bot = DummyBot()
    pm = PluginManager(dp, bot, plugin_dir=pkg_dir, router=router)

    messages = []

    def fake_error(msg, *args, **kwargs):
        if args:
            msg = msg % args
        messages.append(msg)

    monkeypatch.setattr(plugin_manager.logger, "error", fake_error)

    with pytest.raises(plugin_manager.PluginLoadError):
        asyncio.run(pm.load_plugin("missing_plugin"))

    assert messages
    assert "missing_plugin" in messages[0]
    assert "ModuleNotFoundError" in messages[0]
