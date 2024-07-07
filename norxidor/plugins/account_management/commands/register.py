import time
from ..types.account import Account, Nickname
from nonebot import on_shell_command, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.exception import MatcherException
from nonebot.matcher import Matcher
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser, Namespace, is_type, to_me
from nonebot_plugin_orm import async_scoped_session

parser = ArgumentParser(prog="REGISTER | 注册")
parser.add_argument("nickname", type=str, nargs="?", default="", help="您的昵称，可选")

matcher = on_shell_command("register", aliases={"注册"}, parser=parser, rule=is_type(GroupMessageEvent)&to_me(), priority=10, block=True)
@matcher.handle()
async def _(matcher: Matcher, event: GroupMessageEvent, session: async_scoped_session, args: Namespace = ShellCommandArgs()):
    if await session.get(Account, event.user_id):
        nickname = await session.get(Nickname, event.get_session_id())
        await matcher.finish(f"亲爱的{(nickname.nickname+' ') if nickname else ''} " + MessageSegment.at(event.user_id) + "，您已经注册过了！")
    
    nickname = args.nickname
    session.add(Account(id=event.user_id, register_time=time.time(), coin=0, last_checkin_time=0))
    if nickname:
        session.add(Nickname(session_id=event.get_session_id(), user_id=event.user_id, group_id=event.group_id, nickname=nickname))
        
    try:
        await session.commit()
        await matcher.finish(f"尊敬的{(nickname+' ') if nickname else ''}" + MessageSegment.at(event.user_id) + "，您已成功注册账户！")
    except MatcherException:
        raise
    except Exception as e:
        logger.opt(exception=e).error(type(e).__name__)
        await matcher.finish("注册账户失败")
    