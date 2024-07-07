from ..types.account import Account, Nickname
from nonebot import on_shell_command, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.exception import MatcherException
from nonebot.matcher import Matcher
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser, Namespace, is_type, to_me
from nonebot_plugin_orm import async_scoped_session

parser = ArgumentParser(prog="NICK | 修改昵称")
parser.add_argument("nickname", type=str, help="要修改的昵称")

matcher = on_shell_command(
    "nick",
    aliases={"修改昵称"},
    parser=parser,
    rule=is_type(GroupMessageEvent)&to_me(),
    priority=10,
    block=True,
)

@matcher.handle()
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    session: async_scoped_session,
    args: Namespace = ShellCommandArgs(),
):
    if await session.get(Account, event.user_id):
        nickname = await session.get(Nickname, event.get_session_id())
        try:
            if nickname:
                nickname.nickname = args.nickname
                await session.flush([nickname])
            else:
                session.add(Nickname(session_id=event.get_session_id(), user_id=event.user_id, group_id=event.group_id, nickname=args.nickname))
            await session.commit()
            await matcher.finish(MessageSegment.at(event.user_id) + f" 成功修改昵称为{args.nickname}")
        except MatcherException:
            raise
        except Exception as e:
            logger.opt(exception=e).error(type(e).__name__)
            await matcher.finish("昵称修改失败")
    else:
        await matcher.finish("尊敬的"+MessageSegment.at(event.user_id)+"，您尚未注册账户，请先注册！")