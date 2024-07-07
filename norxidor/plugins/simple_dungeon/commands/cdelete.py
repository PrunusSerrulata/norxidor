from ..types.character import Character
from ... import account_management
from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.exception import MatcherException
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandStart
from nonebot.rule import is_type
from nonebot.typing import T_State
from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import delete


reserved_names = ["诺辛德", "norxidor", "酒馆老板"]

rule = is_type(GroupMessageEvent)
matcher = on_command(
    "cdelete", aliases={"删除角色"}, rule=rule, priority=10, block=True
)


@matcher.handle()
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    state: T_State,
    session: async_scoped_session,
    prefix: str = CommandStart(),
):
    if prefix != "!":
        await matcher.finish()
    account, nickname = await account_management.utils.find_account(event.user_id, event.group_id, session)
    state["character"] = await session.get(Character, event.get_session_id())
    if not state["character"]:
        await matcher.finish(
            ("亲爱" if account else "尊敬") + f"的{(nickname.nickname+' ') if nickname else ''}"
            + MessageSegment.at(event.user_id)
            + "，您尚未创建角色！"
        )
    else:
        logger.debug("Classes: "+", ".join([x.name for x in state["character"].classes]))
        await matcher.send(
            f"亲爱的{(nickname.nickname+' ') if nickname else ''}"
            + MessageSegment.at(event.user_id)
            + f"，您确定要删除您的角色“{state['character'].name}”吗？（输入YES确认，其余取消）"
        )

@matcher.got("conformation")
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