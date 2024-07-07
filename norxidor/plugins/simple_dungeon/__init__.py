from nonebot import get_plugin_config, require
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="simple_dungeon",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

require("account_management")

from .commands import *
