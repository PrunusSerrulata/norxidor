import nonebot
from .. import config, utils
from datetime import datetime, timedelta, timezone
from nonebot import on_shell_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import ShellCommandArgv
from nonebot.rule import ArgumentParser, is_type
from nonebot_plugin_orm import async_scoped_session

BAR_STRING = nonebot.get_driver().config.bar_string

parser = ArgumentParser(prog="LOOKUP | 查询")

matcher = on_shell_command(
    "lookup",
    aliases={"查询"},
    parser=parser,
    rule=is_type(GroupMessageEvent),
    priority=10,
    block=True,
)

@matcher.handle()
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    session: async_scoped_session,
    args: list[str | MessageSegment] = ShellCommandArgv(),
):
    target = utils.get_target_from_msg(args[0]) if len(args) > 0 else event.user_id
    if target is None:
        await matcher.finish(
            MessageSegment.at(event.user_id) + " 请提供合法的查询目标：本群昵称/QQ号/at"
        )

    account, nickname = await utils.find_account(target=target, group_id=event.group_id, session=session)

    if not account:
        await matcher.finish(
            MessageSegment.at(event.user_id) + " 未找到符合的查询对象！"
        )
    else:
        tz_utc_8 = timezone(timedelta(hours=8))
        await matcher.finish(
            MessageSegment.at(event.user_id)
            + MessageSegment.text(
                f"\n查询对象："
                + (f"{nickname.nickname} ({account.id})" if nickname else str(account.id))
                + f"\n{BAR_STRING}"
                + f"\n注册时间：{datetime.fromtimestamp(account.register_time, tz=tz_utc_8).strftime('%Y/%m/%d %H:%M:%S')} (UTC+8)"
                + f"\n上次签到时间：{datetime.fromtimestamp(account.last_checkin_time, tz=tz_utc_8).strftime('%Y/%m/%d %H:%M:%S')} (UTC+8)"
                + f"\n{config.coin_notation}：{account.coin}"
            )
        )
