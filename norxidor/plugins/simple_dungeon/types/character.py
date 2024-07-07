from ..types.alignment import Alignment
from ..types.character_class import CharacterClass
from ..types.race import Race
from enum import Enum, unique, auto
from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property

@unique
class Gender(Enum):
    Male = auto()
    """男
    """
    
    Female = auto()
    """女
    """

class Character(Model):
    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    group_id: Mapped[int]
    name: Mapped[str]
    gender: Mapped[Gender]
    race: Mapped[Race]
    _str_class: Mapped[str]
    alignment: Mapped[Alignment]
    str_: Mapped[int]
    dex_: Mapped[int]
    con_: Mapped[int]
    int_: Mapped[int]
    wis_: Mapped[int]
    cha_: Mapped[int]
    exp: Mapped[int] = mapped_column(default=0)
    gold: Mapped[int] = mapped_column(default=0)
    
    @hybrid_property
    def classes(self) -> list[CharacterClass]:
        return [CharacterClass(int(x)) for x in self._str_class.split(",")]
    @classes.setter
    def _(self, value: list[CharacterClass]):
        self._str_class = ",".join([x.name for x in value])
    
    def get_introduction(self, no_stat: bool = False):
        return f"""\
名称：{self.name}
性别：{'男' if self.gender is Gender.Male else '女'}
种族：{self.race.name_zh}
职业：{'&'.join([x.name_zh for x in self.classes])}
阵营：{self.alignment.name_zh}
力量：{self.str_}
敏捷：{self.dex_}
体质：{self.con_}
智力：{self.int_}
感知：{self.wis_}
魅力：{self.cha_}\
{f'经验值：{self.exp}'+chr(10) if not no_stat else ''}\
{f'金币：{self.gold}'+chr(10) if not no_stat else ''}"""