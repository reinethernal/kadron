import asyncio
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import importlib
import aiogram  # noqa: E402
import plugin_manager  # noqa: E402


class DummyBot(aiogram.Bot):
    pass


def make_ok_plugin(path: Path):
    path.write_text(
        """
class Plugin:
    async def register_handlers(self, router):
        pass
    def get_commands(self):
        return []

def load_plugin(bot=None, plugin_manager=None):
    return Plugin()
"""
    )


def make_fail_plugin(path: Path):
    path.write_text(
        """
class Plugin:
    def __init__(self):
        raise RuntimeError('boom')

    async def register_handlers(self, router):
        pass

def load_plugin(bot=None, plugin_manager=None):
    return Plugin()
"""
    )


def test_load_plugins_continues_on_error(tmp_path, monkeypatch):
    pkg_dir = tmp_path / "plugs"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    make_ok_plugin(pkg_dir / "good_plugin.py")
    make_fail_plugin(pkg_dir / "bad_plugin.py")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.chdir(tmp_path)

    pm_module = importlib.reload(importlib.import_module("plugin_manager"))
    dp = pm_module.Dispatcher()
    router = pm_module.Router()
    bot = DummyBot()
    pm = pm_module.PluginManager(dp, bot, plugin_dir=pkg_dir, router=router)

    logged = []

    def fake_log(msg, *args, **kwargs):
        if args:
            msg = msg % args
        logged.append(msg)

    monkeypatch.setattr(pm_module.logger, "exception", fake_log)
    monkeypatch.setattr(pm_module.logger, "error", fake_log)

    asyncio.run(pm.load_plugins())

    assert "good_plugin" in pm.plugins
    assert "bad_plugin" not in pm.plugins
    assert logged


def test_missing_required_plugins_error_after_attempt(tmp_path, monkeypatch):
    pkg_dir = tmp_path / "plugs2"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    make_ok_plugin(pkg_dir / "good_plugin.py")
    make_fail_plugin(pkg_dir / "bad_plugin.py")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.chdir(tmp_path)

    pm_module = importlib.reload(importlib.import_module("plugin_manager"))
    dp = pm_module.Dispatcher()
    router = pm_module.Router()
    bot = DummyBot()
    pm = pm_module.PluginManager(dp, bot, plugin_dir=pkg_dir, router=router)

    monkeypatch.setattr(pm_module.logger, "exception", lambda *a, **k: None)
    monkeypatch.setattr(pm_module.logger, "error", lambda *a, **k: None)

    with pytest.raises(pm_module.MissingRequiredPluginsError) as exc:
        asyncio.run(pm.load_plugins(required_plugins=["bad_plugin"]))

    assert "bad_plugin" in str(exc.value)
    assert "good_plugin" in pm.plugins
