import plugin_manager as pm_module


class DummyRoles:
    def has_permission(self, user_id, perm):
        return user_id == 1 and perm == "allow"


class DummyPlugin:
    __plugin_meta__ = {
        "admin_menu": [
            {"text": "A", "callback": "a", "permission": "allow"},
            {"text": "B", "callback": "b", "permission": "deny"},
            {"text": "C", "callback": "c"},
        ]
    }

    async def register_handlers(self, router):
        pass


def test_admin_menu_respects_permissions():
    pm = pm_module.PluginManager(pm_module.Dispatcher(), pm_module.Bot(), router=pm_module.Router())
    pm.plugins = {"roles_plugin": DummyRoles(), "dummy": DummyPlugin()}

    items_user1 = pm.get_admin_menu_items(user_id=1)
    items_user2 = pm.get_admin_menu_items(user_id=2)
    items_none = pm.get_admin_menu_items()

    assert {"text": "A", "callback": "a"} in items_user1
    assert {"text": "B", "callback": "b"} not in items_user1
    assert {"text": "C", "callback": "c"} in items_user1

    assert {"text": "A", "callback": "a"} not in items_user2
    assert {"text": "B", "callback": "b"} not in items_user2
    assert {"text": "C", "callback": "c"} in items_user2

    assert {"text": "A", "callback": "a"} in items_none
    assert {"text": "B", "callback": "b"} in items_none
    assert {"text": "C", "callback": "c"} in items_none
