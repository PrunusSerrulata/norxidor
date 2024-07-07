import nonebot
import time
from .. import config
from ..types.account import Account, Nickname
from datetime import datetime, timedelta, timezone
from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.exception import MatcherException
from nonebot.matcher import Matcher
from nonebot.rule import is_type
from nonebot_plugin_orm import async_scoped_session

BAR_STRING = nonebot.get_driver().config.bar_string

matcher = on_command("goodday", aliases={"good-day", "日安"}, rule=is_type(GroupMessageEvent), priority=10, block=True)
@matcher.handle()
async def _(matcher: Matcher, event: GroupMessageEvent, session: async_scoped_session):
    if account := await session.get(Account, event.user_id):
        nickname = await session.get(Nickname, event.get_session_id())
        nickname = nickname.nickname + " " if nickname else ""
        
        tz_utc_8 = timezone(timedelta(hours=8))
        
        today = datetime.now(tz_utc_8)
        _time = today.time()
        if _time.hour in range(2, 5):
            # 02:00~04:59
            greetings = "凌晨时分，旅客们大都陷入沉眠，皎洁的月光洒进空无一人的大厅。"
            res = [ "你不知为何现在还醒着，借着昏暗的灯光在一楼的签到册上签下了自己的名字。诺辛德早上会看到的。",
                    "直到离开客房前的那一刻你才意识到自己今天已经和诺辛德打过招呼了。"]
        elif _time.hour in range(5, 9):
            # 05:00~08:59
            greetings = "清晨时分，太阳已经升起，一些旅客正准备动身。"
            res = [ "诺辛德每天都到的很早。“今天真早啊！”他在签到册上签下你的名字。",
                    "“一日之计在于晨，”诺辛德对你说，“您觉得呢？”"]
        elif _time.hour in range(9, 11):
            # 09:00~10:59
            greetings = "“早上好！”诺辛德看到了你，热情的向你打招呼。"
            res = [ "他一边在签到册上签下你的名字一边问：“想吃什么早餐吗？”",
                    "“冒险者们大都出门冒险去了，”他说，“您今天有什么计划吗？”"]
        elif _time.hour in range(11, 14):
            # 11:00~13:59
            greetings = "“中午好！”诺辛德的声音和各色菜肴的香味一同从大厅里飘出。"
            res = [ "“犒劳犒劳自己吧！”他一边说着，一边打开签到册，签下你的名字。",
                    "“吃点好的，无论是作为奖赏，还是积蓄能量，”他说。"]
        elif _time.hour in range(14, 17):
            # 14:00~16:59
            greetings = "下午时分，大厅里的人稍微少了一些。诺辛德在柜台清点着账目。"
            res = [ "“下午好啊，”他抬起头来看见了你，随即打开签到册，签下你的名字。",
                    "“要来点下午茶吗？”他抬头看到了你，“闲暇时光可是很难得的。”"]
        elif _time.hour in range(17, 19):
            # 17:00~18:59
            greetings = "天色渐晚，大厅里的人渐渐地多了起来。诺辛德在柜台忙得不可开交。"
            res = [ "“晚上好，”见你到来，他迅速打开签到册，潦草签下你的名字。",
                    "“这个点总是很忙，”他无奈地对你说，“冒险者们都很喜欢这个地方。”"]
        elif _time.hour in range(19, 22):
            # 19:00~21:59
            greetings = "夜幕爬上天空，大厅内气氛欢腾，各色人声不绝于耳。"
            res = [ "“晚上好！”诺辛德笑着打开签到册，签下你的名字。“想喝什么？”",
                    "“我的酒馆欢迎所有人，不要闹事就好。”诺辛德对你说，“我知道你不会的。”"]
        else:
            # 22:00~次日01:59
            greetings = "夜色已深，大厅内依旧人声鼎沸。诺辛德正在柜台清点着账目。"
            res = [ "“今天辛苦了，”他看到了你，打开签到册，签下你的名字，“客房已经打扫干净了。”",
                    "“马上就要打烊了，”他对你说，“您也早点休息吧。”"]
            
        
        refresh_time = datetime(today.year, today.month, today.day-1 if today.hour < 4 else today.day, hour=4, tzinfo=tz_utc_8).timestamp()
        last_checkin_time = account.last_checkin_time
        if last_checkin_time < refresh_time:
            account.last_checkin_time = time.time()
            account.coin += 1
            session.add(account)
            try:
                await session.commit()
                await matcher.finish(
                    greetings + res[0]
                    + f"\n{BAR_STRING}"
                    + f"\n亲爱的{nickname}" + MessageSegment.at(event.user_id) + f"，今日签到成功，{config.coin_notation}+1！"
                    )
            except MatcherException:
                raise
            except Exception as e:
                logger.opt(exception=e).error(type(e).__name__)
                await matcher.finish("签到失败")
        else:
            await matcher.finish(
                greetings + res[1]
                + f"\n{BAR_STRING}"
                + f"\n亲爱的{nickname}" + MessageSegment.at(event.user_id) + "，你今天已经签到过啦！（签到于UTC+8每日凌晨4时刷新）"
                )
    else:
        await matcher.finish("尊敬的"+MessageSegment.at(event.user_id)+"，您尚未注册账户，请先注册！")