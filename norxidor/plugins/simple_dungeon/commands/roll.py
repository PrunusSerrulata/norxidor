import argparse
import re
import textwrap
from nonebot import on_command, on_shell_command
from nonebot.exception import ParserExit
from nonebot.matcher import Matcher
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser, Namespace
from .. import utils

def dice_notation(arg):
    if not re.match(r"^\d*[Dd](\d+|%)([\+-]\d+)?$", arg):
        raise argparse.ArgumentTypeError("Invalid value")
    else:
        n = re.match(r"\d+(?=[Dd])", arg)
        n = int(n.group(0)) if n else 1
        
        f = re.search(r"(?<=[Dd])(\d+|%)", arg).group(0) # type: ignore
        f = 100 if f == "%" else int(f)
        
        m = re.search(r"[\+-]\d+", arg)
        m = int(m.group(0)) if m else 0
        
        if n == 0 or f == 0:
            raise argparse.ArgumentTypeError("Invalid value")
        
        return (n, f, m)
        

parser = ArgumentParser(prog="ROLL | r", formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("dice_notation", type=dice_notation, help=textwrap.dedent("""\
                    Dice notation in the form of [N]d(F|%%)[(+|-)M], where
                        N: the number of dice to be rolled (default to 1),
                        F: the number of faces of each die (%% for 100),
                        M: the number that will be added (or subtracted) to the final value (default to 0)
"""))

roll = on_shell_command("roll", aliases={"r"}, parser=parser, priority=10, block=True)

@roll.handle()
async def _(matcher: Matcher, args: Namespace = ShellCommandArgs()):
    await matcher.finish("投骰结果为：%i" % (utils.roll(*args.dice_notation)))
    
@roll.handle()
async def _(matcher: Matcher, args: ParserExit = ShellCommandArgs()):
    if args.status == 0:
        await matcher.finish(args.message)  # help message
    else:
        await matcher.finish(args.message)  # error message

d20 = on_command("d20", priority=10, block=True)

@d20.handle()
async def _(matcher: Matcher):
    await matcher.finish("投骰结果为：%i" % (utils.roll(1, 20)))