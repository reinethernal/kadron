# Contributing

## Creating a plugin

1. Copy `plugin_template.py` from the project root into the `plugins` directory.
   Name the new file using the pattern `<your_name>_plugin.py`.
2. Open the new file and implement the methods described in the template:
   - `register_handlers`
   - `get_commands`
   - Optional hooks such as `get_keyboards`, `on_plugin_load` and `on_plugin_unload`
3. Make sure the file exposes a `load_plugin()` function that returns an instance
   of your plugin class. The plugin manager relies on this function to load the
   plugin.

Files that follow the `*_plugin.py` naming convention are loaded automatically
when the bot starts. If you remove or rename the file so it no longer matches
this pattern, the plugin is disabled. You can also disable or enable a plugin at
runtime using `PluginManager.unload_plugin()` and `PluginManager.load_plugin()`
respectively.
