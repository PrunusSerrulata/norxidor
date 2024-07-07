import re
import time
from .. import config, utils
from ..types.account import Account, Nickname
from sqlalchemy import delete
from nonebot import on_command, on_shell_command, logger
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Message,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.exception import MatcherException
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandArg, CommandStart, ShellCommandArgv
from nonebot.permission import SUPERUSER
from nonebot.rule import ArgumentParser, Namespace, is_type, to_me
from nonebot.typing import T_State
from nonebot_plugin_orm import async_scoped_session

# region dbnuke

dbnuke = on_command(
    "!!dbnuke",
    permission=SUPERUSER,
    priority=10,
    block=True,
)


@dbnuke.handle()
async def _(
    matcher: Matcher,
    event: GroupMessageEvent | PrivateMessageEvent,
    state: T_State,
    prefix: str = CommandStart(),
    args: Message = CommandArg(),
):
    if prefix != "!":
        await matcher.finish()

    if args:
        state["target"] = args.extract_plain_text().lower()
        if state["target"] not in ["group", "all"]:
            await matcher.finish()

    if state["target"] == "group" and type(event) is PrivateMessageEvent:
        await matcher.finish("无法在私聊中删除群数据！")
    await matcher.send(
        MessageSegment.at(event.user_id)
        + f" 确认要删除{'本群对应的' if state['target'] == 'group' else '【所有】'}数据吗？"
    )


@dbnuke.got("conformation")
async def _(
    matcher: Matcher,
    event: GroupMessageEvent | PrivateMessageEvent,
    session: async_scoped_session,
    state: T_State,
    conformation: str = ArgPlainText(),
):
    if conformation != "YES":
        await matcher.finish("已取消操作。")

    try:
        if state["target"] == "group" and type(event) is GroupMessageEvent:
            await session.execute(
                delete(Nickname).where(Nickname.group_id == event.group_id)
            )
        else:
            await session.execute(delete(Account))
            await session.execute(delete(Nickname))
        await session.commit()
        await matcher.finish("数据已删除完毕。")
    except MatcherException:
        raise
    except Exception as e:
        logger.opt(exception=e).error(type(e).__name__)
        await matcher.finish("数据删除失败")


# endregion

# region forcenick

forcenick_parser = ArgumentParser(prog="FORCENICK")
forcenick = on_shell_command(
    "!forcenick",
    parser=forcenick_parser,
    permission=SUPERUSER,
    rule=is_type(GroupMessageEvent),
    priority=10,
    block=True,
)


@forcenick.handle()
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    session: async_scoped_session,
    prefix: str = CommandStart(),
    args: list[str | MessageSegment] = ShellCommandArgv(),
):
    if prefix != "!" or len(args) < 2:
        await matcher.finish()

    target, new_nick = utils.get_target_from_msg(args[0]), args[1]

    if target is None:
        await matcher.finish("请提供合法目标")

    if type(new_nick) is not str:
        await matcher.finish("请提供合法昵称")

    account, nickname = await utils.find_account(
        target=target, group_id=event.group_id, session=session
    )
    if not account:
        await matcher.finish("未找到符合的对象")

    try:
        if nickname:
            nickname.nickname = new_nick
            await session.flush([nickname])
        else:
            session.add(
                Nickname(
                    session_id=f"group_{event.group_id}_{account.id}",
                    user_id=account.id,
                    group_id=event.group_id,
                    nickname=new_nick,
                )
            )
        target_id = account.id
        await session.commit()
        await matcher.finish(
            "成功修改" + MessageSegment.at(target_id) + f" 的昵称为{new_nick}"
        )
    except MatcherException:
        raise
    except Exception as e:
        logger.opt(exception=e).error(type(e).__name__)
        await matcher.finish("昵称修改失败")


# endregion forceregister

# region forceregister

forceregister_parser = ArgumentParser(prog="FORCEREGISTER")
forceregister = on_shell_command(
    "!forceregister",
    parser=forceregister_parser,
    permission=SUPERUSER,
    rule=is_type(GroupMessageEvent),
    priority=10,
    block=True,
)


@forceregister.handle()
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    session: async_scoped_session,
    prefix: str = CommandStart(),
    args: list[str | MessageSegment] = ShellCommandArgv(),
):
    if prefix != "!" or len(args) < 1:
        await matcher.finish()

    target = utils.get_target_from_msg(args[0])
    _nick = args[1] if len(args) >= 2 and type(args[1]) is str else None

    if type(target) is not int:
        await matcher.finish("请提供合法目标")

    account, nickname = await utils.find_account(
        target=target, group_id=event.group_id, session=session
    )
    if account:
        await matcher.finish(
            MessageSegment.at(account.id)
            + (f"（{nickname.nickname}）" if nickname else "")
            + "已经注册账户"
        )

    session.add(
        Account(id=target, register_time=time.time(), coin=0, last_checkin_time=0)
    )
    if _nick:
        session.add(
            Nickname(
                session_id=f"group_{event.group_id}_{target}",
                user_id=target,
                group_id=event.group_id,
                nickname=_nick,
            )
        )
    try:
        await session.commit()
        await matcher.finish(
            "成功为"
            + MessageSegment.at(target)
            + (f"（{_nick}）" if _nick else " ")
            + "注册账户"
        )
    except MatcherException:
        raise
    except Exception as e:
        logger.opt(exception=e).error(type(e).__name__)
        await matcher.finish("账户注册失败")


# endregion

# region deleteaccount

deleteaccount_parser = ArgumentParser(prog="DELETEACCOUNT")
deleteaccount = on_shell_command(
    "!deleteaccount",
    parser=deleteaccount_parser,
    permission=SUPERUSER,
    rule=is_type(GroupMessageEvent),
    priority=10,
    block=True,
)


@deleteaccount.handle()
async def _(
    matcher: Matcher,
    event: GroupMessageEvent | PrivateMessageEvent,
    session: async_scoped_session,
    state: T_State,
    prefix: str = CommandStart(),
    args: list[str | MessageSegment] = ShellCommandArgv(),
):
    if prefix != "!" or len(args) < 1:
        await matcher.finish()

    target = utils.get_target_from_msg(args[0])

    if target is None:
        await matcher.finish("请提供合法目标")

    account, nickname = await utils.find_account(
        target=target,
        group_id=event.group_id if type(event) is GroupMessageEvent else None,
        session=session,
    )
    if not account:
        await matcher.finish("未找到符合的对象")

    state["account_id"] = account.id
    await matcher.send(
        MessageSegment.at(event.user_id)
        + f" 确认要删除{state['account_id']}{f'（{nickname.nickname}）' if nickname else ''}的账户吗？"
    )


@deleteaccount.got("conformation")
async def _(
    matcher: Matcher,
    event: GroupMessageEvent | PrivateMessageEvent,
    session: async_scoped_session,
    state: T_State,
    conformation: str = ArgPlainText(),
):
    if conformation != "YES":
        await matcher.finish("已取消操作。")

    account_id = state["account_id"]
    try:
        await session.execute(delete(Account).where(Account.id == account_id))
        await session.execute(delete(Nickname).where(Nickname.user_id == account_id))
        await session.commit()
        await matcher.finish("已删除该用户。")
    except MatcherException:
        raise
    except Exception as e:
        logger.opt(exception=e).error(type(e).__name__)
        await matcher.finish("数据删除失败")


# endregion


# region addcoin

addcoin_parser = ArgumentParser(prog="ADDCOIN")
addcoin = on_shell_command(
    "!addcoin",
    parser=addcoin_parser,
    permission=SUPERUSER,
    rule=is_type(GroupMessageEvent),
    priority=10,
    block=True,
)


@addcoin.handle()
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    session: async_scoped_session,
    prefix: str = CommandStart(),
    args: list[str | MessageSegment] = ShellCommandArgv(),
):
    if prefix != "!" or len(args) < 1:
        await matcher.finish()

    if len(args) == 1:
        if type(args[0]) is not str or not re.match(r"^[+-]?\d+$", args[0]):
            await matcher.finish("参数不合法")
        target = event.user_id
        add_count = int(args[0])
    else:
        target = utils.get_target_from_msg(args[0])
        if type(args[1]) is not str or not re.match(r"^[+-]?\d+$", args[1]):
            await matcher.finish("参数不合法")
        else:
            add_count = int(args[1])

    if target is None:
        await matcher.finish("请提供合法目标")

    account, nickname = await utils.find_account(
        target=target, group_id=event.group_id, session=session
    )
    if not account:
        await matcher.finish("未找到符合的对象")

    try:
        target_id = account.id
        target_nick = nickname.nickname if nickname else None
        account.coin += add_count
        await session.flush([account])
        await session.commit()
        await matcher.finish(
            f"成功为{target_nick}" + MessageSegment.at(target_id) + " " + ("添加" if add_count >= 0 else "扣除") + f"{abs(add_count)}枚{config.coin_notation}！"
        )
    except MatcherException:
        raise
    except Exception as e:
        logger.opt(exception=e).error(type(e).__name__)
        await matcher.finish("兔币数据修改失败")

# endregion