import re
import time
from .. import utils
from ..types.character import Character
from ... import account_management
from sqlalchemy import delete
from nonebot import on_command, on_shell_command, logger
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
)
from nonebot.exception import MatcherException
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandArg, CommandStart, ShellCommandArgv
from nonebot.permission import SUPERUSER
from nonebot.rule import ArgumentParser, Namespace, is_type, to_me
from nonebot.typing import T_State
from nonebot_plugin_orm import async_scoped_session

# region forcecdelete

forcecdelete_parser = ArgumentParser(prog="FORCECDELETE")
forcecdelete = on_shell_command(
    "!forcecdelete",
    parser=forcecdelete_parser,
    permission=SUPERUSER,
    rule=is_type(GroupMessageEvent),
    priority=10,
    block=True,
)


@forcecdelete.handle()
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    state: T_State,
    session: async_scoped_session,
    prefix: str = CommandStart(),
    args: list[str | MessageSegment] = ShellCommandArgv(),
):
    if prefix != "!" or len(args) < 1:
        await matcher.finish()

    target = account_management.utils.get_target_from_msg(args[0])
    if target is None:
        await matcher.finish("请提供合法目标")

    character = await utils.find_character(target, event.group_id, session)
    if not character:
        await matcher.finish("未找到符合的角色")
    state["character"] = character
    await matcher.send(
        f"确定要删除角色“{character.name}”（{character.race.name_zh}，{'&'.join([x.name_zh for x in character.classes])}）吗？（输入YES确认，其余取消）"
    )


@forcecdelete.got("conformation")
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    session: async_scoped_session,
    state: T_State,
    conformation: str = ArgPlainText(),
):
    if conformation != "YES":
        await matcher.finish("已取消操作。")

    try:
        await session.execute(
            delete(Character).where(Character.id == state["character"].id)
        )
        await session.commit()
        await matcher.finish("角色已删除完毕。")
    except MatcherException:
        raise
    except Exception as e:
        logger.opt(exception=e).error(type(e).__name__)
        await matcher.finish("角色删除失败")


# endregion forcecdelete
