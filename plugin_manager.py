"""
Plugin Manager for Telegram Bot

This module handles loading, unloading, and managing plugins for the bot.
It provides a central registry for all plugins and their functionality.
"""

import importlib
import os
import logging
from typing import Dict, List, Any, Optional
from aiogram import Dispatcher, Bot
from aiogram.types import BotCommand

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages all plugins for the bot"""
    
    def __init__(self, dp: Dispatcher):
        self.dp = dp
        self.plugins = {}
        self.plugin_dir = "plugins"
        
    async def load_plugins(self):
        """Load all plugins from the plugins directory"""
        if not os.path.exists(self.plugin_dir):
            logger.warning(f"Plugin directory {self.plugin_dir} does not exist")
            os.makedirs(self.plugin_dir)
            return
            
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith("_plugin.py") and not filename.startswith("__"):
                plugin_name = filename[:-3]  # Remove .py extension
                await self.load_plugin(plugin_name)
                
    async def load_plugin(self, plugin_name: str) -> bool:
        """Load a specific plugin by name"""
        if plugin_name in self.plugins:
            logger.warning(f"Plugin {plugin_name} is already loaded")
            return False
            
        try:
            module = importlib.import_module(f"{self.plugin_dir}.{plugin_name}")
            plugin = module.load_plugin()
            
            # Register plugin handlers
            await plugin.register_handlers(self.dp)
            
            # Call plugin load hook if it exists
            if hasattr(plugin, "on_plugin_load"):
                plugin.on_plugin_load()
                
            self.plugins[plugin_name] = plugin
            logger.info(f"Plugin {plugin_name} loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return False
            
    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a specific plugin by name"""
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin {plugin_name} is not loaded")
            return False
            
        try:
            plugin = self.plugins[plugin_name]
            
            # Call plugin unload hook if it exists
            if hasattr(plugin, "on_plugin_unload"):
                plugin.on_plugin_unload()
                
            # Remove plugin from registry
            del self.plugins[plugin_name]
            
            logger.info(f"Plugin {plugin_name} unloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False
            
    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """Get a plugin by name"""
        return self.plugins.get(plugin_name)
        
    def get_all_plugins(self) -> Dict[str, Any]:
        """Get all loaded plugins"""
        return self.plugins
        
    def get_all_commands(self) -> List[BotCommand]:
        """Get all commands from all plugins"""
        commands = []
        for plugin in self.plugins.values():
            if hasattr(plugin, "get_commands"):
                commands.extend(plugin.get_commands())
        return commands
    
    async def setup_bot_commands(self, bot: Bot):
        """Set up bot commands from all plugins"""
        commands = self.get_all_commands()
        if commands:
            await bot.set_my_commands(commands)
            logger.info(f"Set up {len(commands)} bot commands")
    
    def get_all_keyboards(self) -> Dict[str, Any]:
        """Get all keyboards from all plugins"""
        keyboards = {}
        for plugin in self.plugins.values():
            if hasattr(plugin, "get_keyboards"):
                plugin_keyboards = plugin.get_keyboards()
                if plugin_keyboards:
                    keyboards.update(plugin_keyboards)
        return keyboards
