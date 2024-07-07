from enum import Enum, auto, unique
from typing import Any, Mapping

from norxidor.plugins.simple_dungeon.types.character_class import CharacterClass

@unique
class BodySize(Enum):
    Small = auto()
    Medium = auto()
    Large = auto()

@unique
class Race(Enum):
    def __new__(cls, *args, **kwds):
          value = len(cls.__members__) + 1
          obj = object.__new__(cls)
          obj._value_ = value
          return obj
    
    def __init__(self, bodysize: BodySize, stat_modifiers: dict[str, int], stat_restrictions: Mapping[str, tuple[int, int]], check_bonuses: dict[str, int], favored_classes: list[CharacterClass], traits: list[Any], name_zh: str) -> None:
        super().__init__()
        
        self.bodysize: BodySize = bodysize
        self.stat_modifiers: dict[str, int] = stat_modifiers
        self.stat_restrictions: Mapping[str, tuple[int, int]] = stat_restrictions
        self.check_bonuses: dict[str, int] = check_bonuses
        self.favored_classes: list[CharacterClass] = favored_classes
        self.traits: list[Any] = traits
        self.name_zh = name_zh


    Dwarf = BodySize.Medium, {"con": 2, "cha": -2}, {}, {}, [], [], "矮人"
    """矮人
    """

    Elf = BodySize.Medium, {"dex": 2, "con": -2}, {}, {}, [], [], "精灵"
    """精灵
    """

    Gnome = BodySize.Small, {"con": 2, "str": -2}, {}, {}, [], [], "地精"
    """地精
    """
    
    Half_Elf = BodySize.Medium, {}, {}, {}, [], [], "半精灵"
    """半精灵
    """
    
    Halfling = BodySize.Small, {"dex": 2, "str": -2}, {}, {}, [], [], "半身人"
    """半身人
    """
    
    Half_Orc = BodySize.Medium, {"str": 2, "int": -2, "cha": -2}, {"int": (3, -1)}, {}, [], [], "半兽人"
    """半兽人
    """
    
    Human = BodySize.Medium, {}, {}, {}, [], [], "人类"
    """人类
    """
    
    @staticmethod
    def from_name(name: str):
        races_cn_to_en = {
            "矮人": "Dwarf",
            "精灵": "Elf",
            "侏儒": "Gnome",
            "半精灵": "Half-Elf",
            "半身人": "Halfling",
            "半兽人": "Half-Orc",
            "人类": "Human",
        }
    
        name = name.title()
        if name in Race.__members__:
            return Race[name]
        elif name in races_cn_to_en:
            return Race[races_cn_to_en[name]]
        else:
            return None