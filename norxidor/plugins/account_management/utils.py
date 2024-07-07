import re
from .types.account import Account, Nickname
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import select


def get_target_from_msg(msg: str | MessageSegment) -> int | str | None:
    target = None
    if type(msg) is int:
        pass
    elif type(msg) is str:
        target = int(msg) if re.match(r"\d+", msg) else msg
    elif type(msg) is MessageSegment and msg.type == "at":
        target = int(msg.data["qq"])

    return target


async def find_account(
    target: str | int, group_id: int | None, session: async_scoped_session
) -> tuple[Account | None, Nickname | None]:
    account, nickname = None, None
    if type(target) is int:
        account = await session.get(Account, target)
        if group_id:
            nickname = await session.get(Nickname, f"group_{group_id}_{target}")
    else:
        nickname = await session.scalar(
            select(Nickname).where(
                Nickname.group_id == group_id, Nickname.nickname == target
            )
        )
        if nickname:
            account = await session.get(Account, nickname.user_id)

    return (account, nickname)
