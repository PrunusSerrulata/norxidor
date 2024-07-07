import random
from nonebot import on_message
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageSegment,
)
from nonebot.matcher import Matcher
from nonebot.params import EventMessage
from nonebot.permission import SUPERUSER
from nonebot.rule import is_type, keyword, startswith

JULIAN_ID = 2791068632
MY_ID = 635231439


def check_julian(event: GroupMessageEvent):
    return event.user_id == JULIAN_ID

rule_ju = keyword("鞭打")
ju = on_message(
    rule=rule_ju,
    permission=check_julian,
    priority=10,
    block=True,
)

rule_su = is_type(GroupMessageEvent) & startswith("鞭打猪脸")
su = on_message(
    rule=rule_su,
    permission=SUPERUSER,
    priority=10,
    block=True,
)


@ju.handle()
@su.handle()
async def _(
    bot: Bot,
    matcher: Matcher,
    event: GroupMessageEvent,
    msg: Message = EventMessage(),
):
    # if event.user_id == JULIAN_ID:
    #     bot_id = (await bot.get_login_info())["user_id"]
    #     ju_trigger = False
    #     for ms in msg.get("at"):
    #         ju_trigger = ju_trigger | int(ms.data["qq"]) in [MY_ID, bot_id]
    #     if not ju_trigger:
    #         await matcher.finish()
    
    if random.randint(1, 20) == 20:
        await matcher.finish(
            "酒馆老板见猪脸如此造次，抡起铜头皮带抽向" + MessageSegment.at(JULIAN_ID) + f"，会心一击结结实实地打在了他的敏感部位，打得他皮开肉绽又如陀螺般旋转，造成了2d8={random.randint(1, 8)+random.randint(1, 8)}点伤害！"
        )
    else:
        await matcher.finish(
            "酒馆老板见猪脸如此造次，抡起铜头皮带就把" + MessageSegment.at(JULIAN_ID) + f" 抽得如陀螺般旋转，造成了1d8={random.randint(1, 8)}点伤害！"
        )