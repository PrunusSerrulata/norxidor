from pydantic import BaseModel


class Config(BaseModel):
    """Plugin Config Here"""
    coin_notation: str = "🐰🪙"