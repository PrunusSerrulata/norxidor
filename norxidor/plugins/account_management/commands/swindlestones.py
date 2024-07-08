import math
import nonebot
import random
import re
import statistics
from functools import reduce
from typing import Literal
from .. import config, utils
from nonebot import on_shell_command, logger
from nonebot.adapters.onebot.v11 import (
    Message,
    GroupMessageEvent,
    PrivateMessageEvent,
    MessageSegment,
)
from nonebot.exception import MatcherException, ParserExit
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, ShellCommandArgs
from nonebot.rule import ArgumentParser, Namespace, is_type, to_me
from nonebot.typing import T_State
from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column

AI_VERSION = 2

MULTIPLIERS = [4, 6]

BAR_STRING = nonebot.get_driver().config.bar_string

COMMAND_TIP = """\
💡【CxN】：进行猜测（C为个数，N为骰子面值）
🔨【call】：揭穿对手并结算本轮
🔍【check】：查看当前状态
ℹ【help】：查看规则与帮助
🏳【quit】：认输并放弃赌注（若有）"""

RULE_TEXT = f"""\
游戏开始时，玩家手中各有数枚骰子，您的目标是猜中场上所有骰子存在某种分布，或是揭穿对方的虚假猜测，直至某一方骰数为0为止。
{BAR_STRING}
💡【猜测】：玩家可以猜测当前场上至少存在【C枚】面值为【N】的骰子，其中C必须大于等于上次猜测中的C，且若相等则N必须较上次的为大。
例：场上共有8枚4面骰，若上家猜测3x2，则本回合您只能猜测(4~8)x(2~4)，或(3)x(3~4)。

🔨【揭穿】：玩家可以在对手做出猜测后予以揭穿，此举将会展示双方手中的骰子，并判断对手的猜测是否正确。若猜测正确，则揭穿者输掉本轮，否则上家输掉本轮。
无论结果如何，双方都重新抓骰，输家将少抓一个骰子。

🏁【结束】：当一方无骰可抓时，游戏结束，另一方赢得游戏。"""

ARGS_HELP_TEXT = f"""\
🔧【自定义】：SWINDLESTONES [赌注] [难度] [骰子预设]
赌注：默认为0，最高为10。普通难度倍率为{MULTIPLIERS[0]}，困难为{MULTIPLIERS[1]}，向下取整
难度：0普通/1困难（目前暂未开放困难难度）
骰子预设：NdF，代表开局双方各有N枚F面骰"""

FULL_HELP_TEXT = (
    RULE_TEXT
    + f"\n{BAR_STRING}\n"
    + ARGS_HELP_TEXT
    + f"\n{BAR_STRING}\n局内命令：\n"
    + COMMAND_TIP
)

INGAME_HELP_TEXT = RULE_TEXT + f"\n{BAR_STRING}\n局内命令：\n" + COMMAND_TIP


class SwindlestonesStatistics(Model):
    version: Mapped[int] = mapped_column(primary_key=True, default=AI_VERSION)
    game_count: Mapped[int] = mapped_column(default=0)
    bot_win_count: Mapped[int] = mapped_column(default=0)


def pmf_B(k: int, n: int, p: float) -> float:
    """二项分布概率质量函数 `Pr(X = k; n, p)`"""
    if k > n or p < 0 or p > 1:
        raise ValueError
    return math.comb(n, k) * p**k * (1 - p) ** (n - k)


def cdf_B(k: int, n: int, p: float) -> float:
    """二项分布累积分布函数 `Pr(X <= k; n, p)`"""
    res = 0
    for i in range(k + 1):
        res += pmf_B(i, n, p)
    return res


def dice_probability(k: int, kmin: int, kmax: int, n: int, f: int) -> float:
    """在`n`个`f`面骰中，已知指定面值的骰子数目在`kmin`与`kmax`之间，求所有骰子中有至少`k`个相应面值骰子的概率`(kmin ≤ k ≤ kmax)`。

    Args:
        `k` (int): 目标值
        `kmin` (int): 对应面值骰子数量的下限
        `kmax` (int): 对应面值骰子数量的上限
        `n` (int): 骰子总数
        `f` (int): 骰子面数
    """
    p = 1 / f
    if k <= kmin:
        return 1
    elif k > kmax:
        return 0
    else:
        return ((1 - cdf_B(k - 1, n, p)) - (1 - cdf_B(kmax, n, p))) / (
            1 - cdf_B(kmin - 1, n, p) - (1 - cdf_B(kmax, n, p))
        )

def p_no_more_than_k_same(k: int, n: int, d: int) -> float:
    """有d种不同的项目共n个，其中同种项目的个数不足k的概率"""
    if k == 1:
        return math.factorial(d) / (math.factorial(d-n)*d**n)
    
    res = 0
    for i in range(1, math.floor(n/k)+1):
        a = math.factorial(n)*math.factorial(d) / (d**(i*k)*math.factorial(i)*math.factorial(k)**i*math.factorial(n-i*k)*math.factorial(d-i))
        s = 0
        for j in range(1, k):
            s += p_no_more_than_k_same(j, n-i*k, d-i)*(d-i)**(n-i*k)/d**(n-i*k)
        res += a*s
    return res

def p_at_least_k_same(k: int, n: int, d: int) -> float:
    """有d种不同的项目共n个，其中同种项目的个数至少为k的概率"""
    if k > n:
        raise ValueError("k must lower or equal to n")
    if k <= math.ceil(n/d):
        return 1
    else:
        return sum([p_no_more_than_k_same(i, n, d) for i in range(k, n+1)])

def check_guess_valid(guess: tuple[int, int, bool], last_guess: tuple[int, int, bool]):
    valid = False
    if guess[0] == last_guess[0] and guess[1] > last_guess[1]:
        valid = True
    elif guess[0] > last_guess[0]:
        valid = True

    return valid


def ai_guess(state: T_State) -> tuple[int, int, Literal[False]] | None:
    f: int = state["swindlestones"]["dice_face"]

    player_dices: list[int] = state["swindlestones"]["player_dices"]
    ai_dices: list[int] = state["swindlestones"]["ai_dices"]
    dice_count = len(player_dices + ai_dices)

    if not state["swindlestones"]["last_guess"]:  # 先手
        STRATEGY_TABLE = [
            [1],
            [5, 5],
            [1, 3, 6],
            [1, 1, 2, 6],
            [0, 1, 1, 2, 6],
        ]

        # 投机：增加猜测数目上限
        opportunistic_limit = 0
        for i in range(len(player_dices)-1, 0, -1):
            if random.random() <= dice_probability(i, 0, len(player_dices), len(player_dices), f):
                opportunistic_limit += i
                break
        if opportunistic_limit > 0:
            logger.info(f"投机：猜测数目上限+{opportunistic_limit}")

        missing_faces = [
            x for x in range(1, f + 1) if x not in ai_dices
        ]  # ai手上缺失的骰子
        if len(missing_faces) > 0 and random.random() <= 0.5:
            chosen_face = random.choice(missing_faces)
            logger.info(
                "欺诈性开局："
                + ("随机" if len(missing_faces) > 1 else "")
                + f"选择不存在的面值{chosen_face}"
            )
            return (min(random.randint(1, 2), len(ai_dices) + opportunistic_limit), chosen_face, False)

        selected_dice = random.choice(statistics.multimode(ai_dices))
        selected_dice_count = ai_dices.count(selected_dice)
        strategy = STRATEGY_TABLE[selected_dice_count - 1]

        chosen_count, threshold = 0, 0
        rand = random.randint(1, reduce(lambda x, y: x + y, strategy))
        for _n in range(len(strategy)):
            if rand > threshold and rand <= threshold + strategy[_n]:
                chosen_count = _n + 1 + opportunistic_limit
                logger.info(
                    ("" if chosen_count <= selected_dice_count else "欺诈性")
                    + f"开局：选择策略{chosen_count}x{selected_dice}"
                )
                break
            else:
                threshold += strategy[_n]

        return (chosen_count, selected_dice, False)

    else:  # 后手或玩家已猜测
        player_c: int
        player_n: int
        player_c, player_n, _ = state["swindlestones"]["last_guess"]
        ai_last_c: int
        ai_last_n: int
        ai_last_c, ai_last_n, _ = (
            state["swindlestones"]["ai_last_guess"]
            if state["swindlestones"]["ai_last_guess"]
            else (0, 0, False)
        )

        if player_c > dice_count - len([x for x in ai_dices if x != player_n]):
            logger.info("玩家猜测的骰子数目超过了场上可能存在的最大数目")
            return None

        if (cdiff := player_c - ai_dices.count(player_n)) > 0:
            player_possible_dice_count = len(player_dices) - sum([v for k, v in state["swindlestones"]["ai_memory"].items() if k != player_n])
            if (player_possible_dice_count <= 0
                or random.random() >= p_at_least_k_same(cdiff, player_possible_dice_count, f)
                or (_r := random.random() <= 0.15 * cdiff)):
                logger.info(f"{'随机' if '_r' in vars() else ''}怀疑玩家欺诈")
                return None
            
        if max(state["swindlestones"]["ai_memory"].values()) > 0 or player_n == ai_last_n: # 玩家后手
            opportunistic_limit = 0
            for i in range(len(player_dices)-1, 0, -1):
                if random.random() <= dice_probability(i, 0, len(player_dices), len(player_dices), f):
                    opportunistic_limit += i
                    break
            if opportunistic_limit > 0:
                logger.info(f"投机：猜测玩家所持骰数目+{opportunistic_limit}")
            guaranteed_player_dice_count = (
                player_c - (ai_last_c if player_n == ai_last_n else 1)
            )
            guaranteed_player_dice_count = int(guaranteed_player_dice_count / 2) + opportunistic_limit
        else: # 玩家先手，或AI先手后玩家不跟面值
            guaranteed_player_dice_count = int(player_c / 2 * max((5 - len(player_dices)) / 2, 1))
        
        if state["swindlestones"]["ai_memory"][player_n] < guaranteed_player_dice_count:
            state["swindlestones"]["ai_memory"][player_n] = guaranteed_player_dice_count

        best_probabilities: dict[int, tuple[int, float]] = {}  # { 面值: (个数, 概率) }

        for _n in range(1, f + 1):  # 遍历所有面值
            all_probabilities: list[tuple[int, float]] = []
            count_min = ai_dices.count(_n) + state["swindlestones"]["ai_memory"][_n]
            count_max = (
                dice_count
                - len([x for x in ai_dices if x != _n])
                - sum([v for k, v in state["swindlestones"]["ai_memory"].items() if k != _n])
            )
            if _n == player_n and count_max < count_min:
                logger.info(f"玩家猜测思路过于投机")
                return None
            
            # count_max = max(count_max, count_min)
            if (
                len(player_dices) < len(ai_dices)
                and _n == player_n
                and player_c == 1
                and count_max <= 2
                and random.random() <= (1 - len(player_dices) / len(ai_dices)) / 2
            ):
                logger.info("情况对玩家很不利，进行诱导")
                count_max += 1
            for _c in range(count_min, count_max + 1):  # 遍历可能的所有骰子数目
                if (
                    _c == player_c
                    and _n == player_n
                    and dice_probability(_c, count_min, count_max, dice_count, f) < 0.1
                ):
                    logger.info("玩家当前猜测的骰子组合可能性过小")
                    return None
                if check_guess_valid(
                    (_c, _n, False), state["swindlestones"]["last_guess"]
                ):  # 按规则筛选猜测
                    all_probabilities.append(
                        (_c, dice_probability(_c, count_min, count_max, dice_count, f))
                    )
            all_probabilities.sort(key=lambda x: x[0], reverse=True)  # 按骰子数目排序
            if len(all_probabilities) > 0:
                best_probabilities[_n] = max(
                    all_probabilities, key=lambda x: x[1]
                )  # 确保找到最大概率中骰子数量最大的

        if len(best_probabilities) == 0:
            logger.info("不存在合法的猜测")
            return None

        best_probability = max(best_probabilities.values(), key=lambda x: x[1])[1]
        if best_probability < 0.1:
            logger.info("所有合法猜测的可能性均过小")
            return None

        best_probabilities = {
            k: v for (k, v) in best_probabilities.items() if v[1] == best_probability and k > 0
        }
        if len(best_probabilities) == 0:
            logger.info("最佳猜测中所有可用的骰子面值对应的数目均为0")
            return None
        
        
        res = min(best_probabilities.keys())
        logger.info(
            f"面值最小的最佳猜测：{best_probabilities[res][0]}x{res} @ {best_probabilities[res][1]}"
        )
        return (best_probabilities[res][0], res, False)


def end_round(state: T_State):
    f: int = state["swindlestones"]["dice_face"]

    _c: int
    _n: int
    is_player: bool
    _c, _n, is_player = state["swindlestones"]["last_guess"]

    player_dices: list[int]
    ai_dices: list[int]
    player_dices, ai_dices = (
        state["swindlestones"]["player_dices"],
        state["swindlestones"]["ai_dices"],
    )
    all_dices: list[int] = player_dices + ai_dices

    player_win = (is_player and all_dices.count(_n) >= _c) or (
        not is_player and all_dices.count(_n) < _c
    )
    if player_win:
        ai_dices.pop()
    else:
        player_dices.pop()

    player_dices = sorted([random.randint(1, f) for i in range(len(player_dices))])
    ai_dices = sorted([random.randint(1, f) for i in range(len(ai_dices))])
    state["swindlestones"]["player_dices"] = player_dices
    state["swindlestones"]["ai_dices"] = ai_dices

    return player_win


def get_dice_emoji_list(dices: list[int]):
    return "".join(
        [
            (str(x).encode("utf-8") + b"\xef\xb8\x8f\xe2\x83\xa3").decode("utf-8")
            for x in dices
        ]
    )


parser = ArgumentParser(prog="SWINDLESTONES | SS | 猜骰子 | 昆特骰")

parser.add_argument(
    "bet", type=int, nargs="?", default=0, help="赌注（最大为10），默认为0即无赌注"
)
parser.add_argument(
    "difficulty",
    type=int,
    nargs="?",
    choices=(0,),
    default=0,
    help="难度设置，0为一般（默认），1为困难（暂未开放！）",
)
parser.add_argument(
    "dice_notation",
    type=str,
    nargs="?",
    default="5d4",
    help="以NdF(1≤N≤5, 2≤F≤8)表示的骰子配置，默认为5d4",
)

matcher = on_shell_command(
    "swindlestones",
    aliases={"ss", "猜骰子", "昆特骰"},
    parser=parser,
    rule=is_type(GroupMessageEvent, PrivateMessageEvent),
    priority=10,
    block=True,
)


@matcher.handle()
async def _(
    matcher: Matcher,
    event: GroupMessageEvent | PrivateMessageEvent,
    args: ParserExit = ShellCommandArgs(),
):
    if args.status == 0:
        await matcher.finish(MessageSegment.at(event.user_id) + "\n" + FULL_HELP_TEXT)
    else:
        await matcher.finish("参数解析失败")


@matcher.handle()
async def _(
    matcher: Matcher,
    event: GroupMessageEvent | PrivateMessageEvent,
    state: T_State,
    session: async_scoped_session,
    args: Namespace = ShellCommandArgs(),
):
    if not await session.scalar(
        select(SwindlestonesStatistics).where(
            SwindlestonesStatistics.version == AI_VERSION
        )
    ):
        session.add(SwindlestonesStatistics())
        try:
            await session.commit()
        except Exception as e:
            logger.opt(exception=e).error(type(e).__name__)
            await matcher.finish("统计表创建失败")

    account, nickname = await utils.find_account(
        event.user_id,
        event.group_id if type(event) is GroupMessageEvent else None,
        session,
    )
    if not account:
        await matcher.finish(
            "尊敬的" + MessageSegment.at(event.user_id) + "，您尚未注册账户，请先注册！"
        )

    if args.bet < 0:
        await matcher.finish(
            MessageSegment.at(event.user_id)
            + f"\n“{nickname.nickname+'，' if nickname else ''}您可不能从我这里借钱当赌注啊！”"
            + f"\n{BAR_STRING}\n"
            + "⚠赌注必须非负且不大于10，想要无本买卖请不提供对应参数或提供0"
        )
    elif args.bet > account.coin:
        await matcher.finish(
            MessageSegment.at(event.user_id)
            + " 诺辛德看着你，面露难色：“您好像没有那么多钱……”"
        )
    elif args.bet > 10:
        await matcher.finish(
            MessageSegment.at(event.user_id)
            + f"\n“{nickname.nickname+'，' if nickname else ''}您出手真阔绰，恐怕我接不了……”"
            + f"\n{BAR_STRING}\n"
            + "⚠赌注必须非负且不大于10，想要无本买卖请不提供对应参数或提供0"
        )

    if not re.match(r"^\d+[dD]\d+$", args.dice_notation):
        await matcher.finish(
            MessageSegment.at(event.user_id) + " 请提供正确的骰子配置！"
        )
    else:
        n, f = map(int, args.dice_notation.lower().split("d"))
        if n == 0 or f <= 1:
            await matcher.finish(
                MessageSegment.at(event.user_id) + " 请提供正确的骰子配置！"
            )
        elif n > 5 or f > 8:
            await matcher.finish(
                MessageSegment.at(event.user_id) + " 骰子数目或面数过多！"
            )

    if args.bet > 0:
        try:
            account.coin -= args.bet
            await session.flush([account])
            await session.commit()
        except Exception as e:
            logger.opt(exception=e).error(type(e).__name__)
            await matcher.finish("数据操作失败")

    # init
    state["swindlestones"] = {
        "account": account,
        "nickname": nickname,
        "difficulty": args.difficulty,
        "bet": args.bet,
        "dice_face": f,
        "player_dices": sorted([random.randint(1, f) for i in range(n)]),
        "ai_dices": sorted([random.randint(1, f) for i in range(n)]),
        "last_guess": None,
        "ai_last_guess": None,
        "ai_memory": {i: 0 for i in range(1, f+1)},
        "ai_turn": False,
    }

    msg = (
        f"你排出了{args.bet}枚{config.coin_notation}放在桌面上当作赌注。"
        if args.bet > 0
        else ""
    )
    msg += f"诺辛德掏出了【{n}枚{f}面】的骰子，放在了你的手心里。"
    msg += [
        "“小赌怡情，大赌伤身，就这么玩玩也挺好。”",
        "“放心放心，我会给您留面子的，”他收下了您的赌注。",
        "“输了也别灰心，反正您也不会真的损失什么……”",
        "“我很期待最后谁会赢，您呢？”他收下了你的赌注。",
    ][args.difficulty * 2 + int(bool(args.bet))]

    msg += f"\n{BAR_STRING}"
    msg += f"\n🎲您手上的骰子为：{get_dice_emoji_list(state['swindlestones']['player_dices'])}"
    msg += f"\n诺辛德手上现在有【{len(state['swindlestones']['ai_dices'])}枚】骰子。"
    msg += f"\n{BAR_STRING}"
    msg += "\n诺辛德投了一枚硬币，"
    if random.random() <= 0.5:
        msg += "反面朝上，他先手。"
        state["swindlestones"]["ai_turn"] = True
        matcher.set_arg("cmd", Message())
    else:
        state["swindlestones"]["ai_turn"] = False
        msg += "正面朝上，您先手。"
        msg += "\n" + COMMAND_TIP

    await matcher.send(MessageSegment.at(event.user_id) + "\n" + msg)


@matcher.got("cmd")
async def _(
    matcher: Matcher,
    event: GroupMessageEvent | PrivateMessageEvent,
    state: T_State,
    session: async_scoped_session,
    cmd: str = ArgPlainText(),
):
    async def call(
        matcher: Matcher,
        event: GroupMessageEvent | PrivateMessageEvent,
        state: T_State,
        session: async_scoped_session,
        call_from_player: bool,
    ):
        game_end = False
        msg = "🔨"
        msg += f"{'你' if call_from_player else '诺辛德'}选择揭穿！双方都展示了自己的骰子……"
        msg += f"\n{BAR_STRING}"
        msg += f"\n您手上的骰子为：{' '.join([str(x) for x in state['swindlestones']['player_dices']])}"
        msg += f"\n诺辛德手上的骰子为：{' '.join([str(x) for x in state['swindlestones']['ai_dices']])}"

        _c: int
        _n: int
        is_player: bool
        _c, _n, is_player = state["swindlestones"]["last_guess"]
        msg += f"\n最后一次猜测是场上至少有【{_c}枚】面值为【{_n}】的骰子，由【{'您' if is_player else '诺辛德'}】提出。"
        msg += f"\n{BAR_STRING}\n"

        player_win = end_round(state)
        if player_win:
            msg += "🥳"
            msg += f"{'您猜中了' if is_player else '诺辛德猜错了'}！"
            if len(state["swindlestones"]["ai_dices"]) > 0:
                msg += "他下一轮需要少抓一枚骰子，且下一轮您先手。\n"
                state["swindlestones"]["ai_turn"] = False
            else:
                msg += "他已无骰可用，您赢得了本局游戏的胜利！🥳"
                game_end = True
        else:
            msg += "😢"
            msg += f"{'您猜错了' if is_player else '诺辛德猜中了'}！"
            if len(state["swindlestones"]["player_dices"]) > 0:
                msg += "您下一轮需要少抓一枚骰子，且下一轮他先手。\n"
                state["swindlestones"]["ai_turn"] = True
            else:
                msg += "您已无骰可用，输掉了本局游戏"
                msg += (
                    "！"
                    if state["swindlestones"]["bet"] == 0
                    else f"以及赌注{state['swindlestones']['bet']}枚{config.coin_notation}！"
                )
                msg += "😭"
                game_end = True
        state["swindlestones"]["last_guess"] = None
        state["swindlestones"]["ai_last_guess"] = None
        state["swindlestones"]["ai_memory"] = {i: 0 for i in range(1, state["swindlestones"]["dice_face"]+1)}

        if not game_end:
            msg += f"\n🎲您现在手上的骰子为：{get_dice_emoji_list(state['swindlestones']['player_dices'])}"
            msg += f"\n诺辛德手上现在有【{len(state['swindlestones']['ai_dices'])}枚】骰子。"
            if not state["swindlestones"]["ai_turn"]:
                await matcher.reject(MessageSegment.at(event.user_id) + "\n" + msg)
            else:
                await matcher.send(MessageSegment.at(event.user_id) + "\n" + msg)
        else:
            stat = await session.scalar(
                select(SwindlestonesStatistics).where(
                    SwindlestonesStatistics.version == AI_VERSION
                )
            )
            assert stat
            stat.game_count += 1
            if player_win:
                account, _ = await utils.find_account(
                    event.user_id,
                    event.group_id if type(event) is GroupMessageEvent else None,
                    session,
                )
                assert account
                coin_get = max(
                    int(
                        state["swindlestones"]["bet"] * (MULTIPLIERS[state["swindlestones"]["difficulty"]])
                    ),
                    1,
                )
                msg += f"\n您获得了{coin_get}枚{config.coin_notation}"
                account.coin += coin_get
                try:
                    await session.flush([account, stat])
                    await session.commit()
                    await matcher.finish(MessageSegment.at(event.user_id) + "\n" + msg)
                except MatcherException:
                    raise
                except Exception as e:
                    logger.opt(exception=e).error(type(e).__name__)
                    await matcher.finish("数据操作失败")
            else:
                stat.bot_win_count += 1
                try:
                    await session.flush([stat])
                    await session.commit()
                    await matcher.finish(MessageSegment.at(event.user_id) + "\n" + msg)
                except MatcherException:
                    raise
                except Exception as e:
                    logger.opt(exception=e).error(type(e).__name__)
                    await matcher.finish("统计数据写入失败")

    cmd = cmd.lower()

    if (
        not re.match(r"^(\d+x\d+|call|check|help|quit)$", cmd)
        and not state["swindlestones"]["ai_turn"]
    ):
        await matcher.reject(
            MessageSegment.at(event.user_id)
            + " 指令不合法，请重新输入指令！（输入help查看帮助）"
        )

    if cmd == "quit":
        await matcher.finish(
            MessageSegment.at(event.user_id)
            + " 🏳您已认输"
            + ("。" if state["swindlestones"]["bet"] == 0 else "，并输掉了所有赌注。")
        )
    elif cmd == "help":
        await matcher.reject(MessageSegment.at(event.user_id) + "\n" + INGAME_HELP_TEXT)
    elif cmd == "call":
        if not state["swindlestones"]["last_guess"]:
            await matcher.reject(
                MessageSegment.at(event.user_id)
                + " 您必须先进行一次猜测，请重新输入指令！（输入help查看帮助）"
            )
        await call(matcher, event, state, session, True)
    elif cmd == "check":
        msg = f"\n🔍您现在手上的骰子为：{get_dice_emoji_list(state['swindlestones']['player_dices'])}"
        msg += (
            f"\n诺辛德手上现在有【{len(state['swindlestones']['ai_dices'])}枚】骰子。"
        )
        if not state["swindlestones"]["last_guess"]:
            msg += "\n还没有人做出过猜测。"
        else:
            _c: int
            _n: int
            is_player: bool
            _c, _n, is_player = state["swindlestones"]["last_guess"]
            msg += f"\n最后一次猜测是场上至少有【{_c}枚】面值为【{_n}】的骰子，由【{'您' if is_player else '诺辛德'}】提出。"
        await matcher.reject(MessageSegment.at(event.user_id) + msg)
    elif cmd:
        dice_count = len(
            state["swindlestones"]["player_dices"] + state["swindlestones"]["ai_dices"]
        )
        c, n = map(int, cmd.split("x"))
        if (c <= dice_count and n <= state["swindlestones"]["dice_face"]) and (
            not state["swindlestones"]["last_guess"]
            or check_guess_valid((c, n, True), state["swindlestones"]["last_guess"])
        ):
            await matcher.send(
                MessageSegment.at(event.user_id)
                + f"\n🤔您猜场上现在至少有【{c}枚】面值为【{n}】的骰子。"
            )
            state["swindlestones"]["last_guess"] = (c, n, True)
            state["swindlestones"]["ai_turn"] = True
        else:
            if c > dice_count:
                await matcher.reject(
                    MessageSegment.at(event.user_id)
                    + " 指定的骰子个数大于场上骰子总个数，请重新输入指令！（输入help查看帮助）"
                )
            elif n > state["swindlestones"]["dice_face"]:
                await matcher.reject(
                    MessageSegment.at(event.user_id)
                    + " 指定的骰子面值大于骰子面数，请重新输入指令！（输入help查看帮助）"
                )
            else:
                await matcher.reject(
                    MessageSegment.at(event.user_id)
                    + " 骰子个数须大于等于上次的猜测，且若骰子个数相等则面值必须大于上次猜测，请重新输入指令！（输入help查看帮助）"
                )

    while state["swindlestones"]["ai_turn"]:
        state["swindlestones"]["ai_turn"] = False
        _ai_guess = ai_guess(state)

        if _ai_guess:
            state["swindlestones"]["last_guess"] = _ai_guess
            state["swindlestones"]["ai_last_guess"] = _ai_guess
            await matcher.reject(
                MessageSegment.at(event.user_id)
                + f"\n🤔诺辛德猜场上现在至少有【{_ai_guess[0]}枚】面值为【{_ai_guess[1]}】的骰子。现在轮到您了。"
            )
        else:
            await call(matcher, event, state, session, False)
