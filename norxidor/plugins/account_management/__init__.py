from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="account_management",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

from . import utils
from .commands import *