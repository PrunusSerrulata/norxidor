import re
from enum import IntFlag, unique
from functools import reduce
from typing import Self


@unique
class Alignment(IntFlag):
    def __new__(cls, value, *args, **kwargs):
        return IntFlag.__new__(cls, value)
    
    def __init__(self, value, name_zh: str, abbr: str, index: int = -1):
        self.name_zh = name_zh
        self.abbr = abbr
        self.index = index

    Lawful =    0b000001, "守序", "L"
    _Neutral1 = 0b000010, "中立", "N"
    Chaotic =   0b000100, "混乱", "C"
    
    Good =      0b001000, "善良", "G"
    _Neutral2 = 0b010000, "中立", "N"
    Evil =      0b100000, "邪恶", "E"

    Lawful_Good = Lawful[0] | Good[0], "守序善良", "LG", 0
    Lawful_Neutral = Lawful[0] | _Neutral2[0], "守序中立", "LN", 1
    Lawful_Evil = Lawful[0] | Evil[0], "守序邪恶", "LE", 2
    Neutral_Good = _Neutral1[0] | Good[0], "中立善良", "NG", 3
    Neutral = _Neutral1[0] | _Neutral2[0], "绝对中立", "N", 4
    Neutral_Evil = _Neutral1[0] | Evil[0], "中立邪恶", "NE", 5
    Chaotic_Good = Chaotic[0] | Good[0], "混乱善良", "CG", 6
    Chaotic_Neutral = Chaotic[0] | _Neutral2[0], "混乱中立", "CN", 7
    Chaotic_Evil = Chaotic[0] | Evil[0], "混乱邪恶", "CE", 8

    def is_lawful(self) -> bool: return self & Alignment.Lawful == Alignment.Lawful
    def is_chaotic(self) -> bool: return self & Alignment.Chaotic == Alignment.Chaotic
    def is_good(self) -> bool: return self & Alignment.Good == Alignment.Good
    def is_evil(self) -> bool: return self & Alignment.Evil == Alignment.Evil
    def is_neutral(self) -> bool:
        return self & Alignment._Neutral1 == Alignment._Neutral1 or self & Alignment._Neutral2 == Alignment._Neutral2

    @staticmethod
    def get_all_alignments():
        return [Alignment.Lawful_Good, Alignment.Lawful_Neutral, Alignment.Lawful_Evil,
                Alignment.Neutral_Good, Alignment.Neutral, Alignment.Neutral_Evil,
                Alignment.Chaotic_Good, Alignment.Chaotic_Neutral, Alignment.Chaotic_Evil]

    @classmethod
    def get_alignments_where(cls, *args: Self, reversed: bool = False):
        return [i for i in cls.get_all_alignments() if reduce(lambda x, y: x or y, [(i&j==j) if not reversed else (i&j!=j) for j in args], 0)]

    @staticmethod
    def from_name(name: str):
        alignment_cn_to_en = {
            "守序善良": Alignment.Lawful_Good,
            "守序中立": Alignment.Lawful_Neutral,
            "守序邪恶": Alignment.Lawful_Evil,
            "中立善良": Alignment.Neutral_Good,
            "绝对中立": Alignment.Neutral,
            "中立邪恶": Alignment.Neutral_Evil,
            "混乱善良": Alignment.Chaotic_Good,
            "混乱中立": Alignment.Chaotic_Neutral,
            "混乱邪恶": Alignment.Chaotic_Evil,
        }
        alignment_abbr_to_en = {
            "L": Alignment.Lawful,
            "C": Alignment.Chaotic,
            "G": Alignment.Good,
            "E": Alignment.Evil,
            "N": Alignment._Neutral1,
        }
        
        name = name.replace(" ", "_").title()
        if match := re.match(r"[a-zA-Z]{1,2}", name):
            name = match.group(0).upper()
            if name == "N":
                return Alignment.Neutral
            else:
                if name[0] == "N":
                    return Alignment._Neutral1 | alignment_abbr_to_en[name[1]]
                elif name[1] == "N":
                    return alignment_abbr_to_en[name[0]] | Alignment._Neutral2
                else:
                    return alignment_abbr_to_en[name[0]] | alignment_abbr_to_en[name[1]]
        else:
            if name in Alignment.__members__:
                return Alignment[name]
            elif name in alignment_cn_to_en:
                return alignment_cn_to_en[name]
            else:
                return None