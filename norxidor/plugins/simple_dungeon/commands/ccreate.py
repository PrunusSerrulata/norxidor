import nonebot
from functools import reduce
from ..types.alignment import Alignment
from ..types.character import Gender, Character
from ..types.character_class import CharacterClass
from ..types.race import Race
from ... import account_management
from nonebot import on_command, logger
from nonebot.adapters import MessageTemplate
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.exception import MatcherException
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText
from nonebot.rule import is_type
from nonebot.typing import T_State
from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import select

BAR_STRING = nonebot.get_driver().config.bar_string

reserved_names = ["诺辛德", "norxidor", "酒馆老板"]

rule = is_type(GroupMessageEvent)
matcher = on_command(
    "ccreate", aliases={"创建角色"}, rule=rule, priority=10, block=True
)


@matcher.handle()
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    state: T_State,
    session: async_scoped_session,
):
    account, nickname = await account_management.utils.find_account(
        event.user_id, event.group_id, session
    )
    if not account:
        await matcher.finish(
            "尊敬的" + MessageSegment.at(event.user_id) + "，您尚未注册账户，请先注册！（使用命令【/(register|注册) [昵称]】注册，昵称为可选项，使用时需at本机器人）"
        )

    if await session.get(Character, event.get_session_id()):
        await matcher.finish(
            f"亲爱的{(nickname.nickname+' ') if nickname else ''}"
            + MessageSegment.at(event.user_id)
            + "，您已经创建过角色！"
        )
    state["character"] = {}


@matcher.got("name", prompt="请输入角色名称（输入!quit退出）：")
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    state: T_State,
    session: async_scoped_session,
    name: str = ArgPlainText(),
):
    if name == "!quit":
        await matcher.finish("已退出角色创建。")
    elif len(name.strip()) == 0:
        await matcher.reject("用户名不能为空，请重新输入！")
    elif name.lower() in reserved_names:
        await matcher.reject("该名称被保留，请重新输入！")
    elif await session.scalar(
        select(Character).where(
            Character.group_id == event.group_id, Character.name == name
        )
    ):
        await matcher.reject("该名称已有其他角色使用，请重新输入！")
    state["character"]["name"] = name.strip()


@matcher.got("gender", prompt="请选择角色性别（男/M或女/F，输入!quit退出）：")
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    state: T_State,
    gender: str = ArgPlainText(),
):
    if gender == "!quit":
        await matcher.finish("已退出角色创建。")
    gender = gender.lower()
    if gender not in ("男", "m", "女", "f"):
        await matcher.reject("性别不合法，请重新输入！" if len(gender) == 1 else None)
    state["character"]["gender"] = (
        Gender.Male if gender in ["男", "m"] else Gender.Female
    )


@matcher.got(
    "race",
    prompt="请选择角色种族（输入!quit退出）：\n\n"
    + "\n".join([f"{i.value}. {i.name_zh}/{i.name.replace('_', ' ')}" for i in Race]),
)
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    state: T_State,
    race: str = ArgPlainText(),
):
    if race.lower() == "!quit":
        await matcher.finish("已退出角色创建。")
    elif race.isdigit():
        if int(race) > len(Race):
            await matcher.reject("种族不合法，请重新输入！")
        state["character"]["race"] = Race(int(race))
    else:
        if _race := Race.from_name(race):
            state["character"]["race"] = _race
        else:
            await matcher.reject("种族不合法，请重新输入！")


@matcher.got(
    "class_",
    prompt="请选择角色职业（输入!quit退出）：\n\n"
    + "\n".join([f"{i.value}. {i.name_zh}/{i.name}" for i in CharacterClass])
    + "\n\n兼职请输入全部职业（最多3个）并以空格分隔",
)
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    state: T_State,
    class_: str = ArgPlainText(),
):
    def get_class(s: str) -> CharacterClass | None:
        if s.isdigit():
            _class = int(s)
            return CharacterClass(_class) if _class <= len(CharacterClass) else None
        else:
            return CharacterClass.from_name(s)

    if class_ == "!quit":
        await matcher.finish("已退出角色创建。")

    classes: list[CharacterClass] = []
    _classes = class_.split(" ")
    for i in _classes:
        if c := get_class(i):
            classes.append(c)

    if len(classes) == 0:
        await matcher.reject("未提供合法职业，请重新输入！")
    elif len(classes) > 3:
        await matcher.reject("提供的兼职职业多于3个，请重新输入！")

    alignments = list(reduce(lambda x, y: x & y, (set(x.alignments) for x in classes)))
    alignments.sort(key=lambda x: x.index)
    if len(alignments) == 0:
        await matcher.reject("该兼职职业组合不存在可用阵营，请重新输入！")

    state["character"]["classes"] = classes
    state["avaliable_alignments"] = alignments
    state["prompt_alignment"] = "\n".join(
        [
            f"{i+1}. {alignments[i].name_zh}/{alignments[i].name.replace('_', ' ')}/{alignments[i].abbr}"  # type: ignore
            for i in range(len(alignments))
        ]
    )


@matcher.got(
    "alignment",
    prompt=MessageTemplate("请选择角色阵营（输入!quit退出）：\n\n{prompt_alignment}"),
)
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    state: T_State,
    session: async_scoped_session,
    alignment: str = ArgPlainText(),
):
    if alignment == "!quit":
        await matcher.finish("已退出角色创建。")
    elif alignment.isdigit():
        if int(alignment) >= len(state["avaliable_alignments"]):
            await matcher.reject("阵营不合法，请重新输入！")
        state["character"]["alignment"] = state["avaliable_alignments"][int(alignment)]
    else:
        _alignment = Alignment.from_name(alignment)
        if _alignment and _alignment in state["avaliable_alignments"]:
            state["character"]["alignment"] = _alignment
        else:
            await matcher.reject("阵营不合法，请重新输入！")

    character = Character(
        id=event.get_session_id(),
        user_id=event.user_id,
        group_id=event.group_id,
        name=state["character"]["name"],
        gender=state["character"]["gender"],
        race=state["character"]["race"],
        _str_class=",".join([str(x.value) for x in state["character"]["classes"]]),
        alignment=state["character"]["alignment"],
        str_=18,
        dex_=18,
        con_=18,
        int_=18,
        wis_=18,
        cha_=18,
    )
    state["character"]["instance"] = character
    state["prompt_conformation"] = character.get_introduction(no_stat=True)


@matcher.got(
    "conformation",
    prompt=MessageTemplate(
        "角色信息如下："+f"\n{BAR_STRING}\n"+"{prompt_conformation}"+f"\n{BAR_STRING}\n"+"确认创建请输入yes/确认，其余取消："
    ),
)
async def _(
    matcher: Matcher,
    event: GroupMessageEvent,
    session: async_scoped_session,
    state: T_State,
    conformation: str = ArgPlainText(),
):
    if conformation.lower() not in ("yes", "确认"):
        await matcher.finish("角色创建已取消。")

    session.add(state["character"]["instance"])
    try:
        await session.commit()
        await matcher.finish("角色创建完毕！")
    except MatcherException:
        raise
    except Exception as e:
        logger.opt(exception=e).error(type(e).__name__)
        await matcher.finish("角色创建失败")
