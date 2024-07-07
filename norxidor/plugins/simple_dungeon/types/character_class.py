from .alignment import Alignment
from enum import Enum, unique
from typing import Any

class CharacterClass(Enum):
    def __new__(cls, *args, **kwargs):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(
        self, base_atk_bonus: list[int], saves: dict[str, int], hit_die: int, specials: list[Any], alignments: list[Alignment], name_zh: str
    ) -> None:
        super().__init__()

        self.base_atk_bonus: list[int] = base_atk_bonus
        self.saves: dict[str, int] = saves
        self.hit_die: int = hit_die
        self.specials: list[Any] = specials
        self.alignments: list[Alignment] = alignments
        self.name_zh = name_zh

    Barbarian = [], {}, 12, [], Alignment.get_alignments_where(Alignment.Lawful, reversed=True), "野蛮人"
    Bard = [], {}, 6, [], Alignment.get_alignments_where(Alignment.Lawful, reversed=True), "吟游诗人"
    Cleric = [], {}, 8, [], Alignment.get_alignments_where(Alignment.Neutral, reversed=True), "牧师"
    Druid = [], {}, 8, [], Alignment.get_alignments_where(Alignment._Neutral1, Alignment._Neutral2), "德鲁伊"
    Fighter = [], {}, 10, [], Alignment.get_all_alignments(), "战士"
    Monk = [], {}, 8, [], Alignment.get_alignments_where(Alignment.Lawful), "武僧"
    Paladin = [], {}, 10, [], [Alignment.Lawful_Good], "圣骑士"
    Ranger = [], {}, 8, [], Alignment.get_all_alignments(), "巡林客"
    Rogue = [], {}, 6, [], Alignment.get_all_alignments(), "游荡者"
    Sorcerer = [], {}, 4, [], Alignment.get_all_alignments(), "术士"
    Wizard = [], {}, 4, [], Alignment.get_all_alignments(), "法师"
    
    @staticmethod
    def from_name(name: str):
        classes_cn_to_en = {
            "野蛮人": "Barbarian",
            "吟游诗人": "Bard",
            "牧师": "Cleric",
            "德鲁伊": "Druid",
            "战士": "Fighter",
            "武僧": "Monk",
            "圣武士": "Paladin",
            "巡林客": "Ranger",
            "游荡者": "Rogue",
            "术士": "Sorcerer",
            "法师": "Wizard",
        }
        
        name = name.title()
        if name in CharacterClass.__members__:
            return CharacterClass[name]
        elif name in classes_cn_to_en:
            return CharacterClass[classes_cn_to_en[name]]
        else:
            return None
