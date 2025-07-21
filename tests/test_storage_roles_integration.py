import asyncio
import importlib
from pathlib import Path
import sys

import aiogram

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class DummyBot(aiogram.Bot):
    pass


def test_survey_plugins_use_admin_storage_and_roles():
    pm_module = importlib.reload(importlib.import_module("plugin_manager"))
    dp = pm_module.Dispatcher()
    router = pm_module.Router()
    bot = DummyBot()
    pm = pm_module.PluginManager(dp, bot, router=router)
    asyncio.run(pm.load_plugins())

    import plugins_admin.storage_plugin as sp
    import plugins_admin.roles_plugin as rp
    import plugins_surveys.survey_plugin as surv
    import plugins_surveys.export_plugin as exp

    assert surv.storage is sp.storage
    assert exp.storage is sp.storage
    assert isinstance(exp.roles_plugin, rp.RolesPlugin)
