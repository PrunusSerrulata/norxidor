from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column

class Account(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    register_time: Mapped[float]
    coin: Mapped[int]
    last_checkin_time: Mapped[float]

class Nickname(Model):
    session_id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    group_id: Mapped[int]
    nickname: Mapped[str]
