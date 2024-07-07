import random
from .types.character import Character
from .. import account_management
from ..account_management.types.account import Account, Nickname
from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import select

def roll(n: int, f: int, m: int=0) -> int:
    """骰子roll点

    Args:
        n (int): 骰子个数
        f (int): 骰子面数
        m (int, optional): 附加常数值，默认为0

    Returns:
        int: roll点结果
    """
    res = m
    for _ in range(n):
        res += random.randint(1, f)
    return res

def d20() -> int:
    """投一个20面骰

    Returns:
        int: roll点结果
    """
    return roll(1, 20)

async def find_character(target: int | str, group_id: int, session: async_scoped_session) -> Character | None:
    account, _ = await account_management.utils.find_account(target, group_id, session)
    if not account:
        return await session.scalar(select(Character).where(Character.name == target, Character.group_id == group_id))
    else:
        return await session.scalar(select(Character).where(Character.id == f"group_{group_id}_{account.id}"))