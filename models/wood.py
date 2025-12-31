from dataclasses import dataclass
from discord import Message

# TODO: maybe author_id for some cool stats?


@dataclass
class WoodMessage:
    """a discord message that has been starred by a sufficient amount of guild members"""

    id: int
    guild_id: int

    @classmethod
    def from_message(cls, message: Message):
        assert message.guild is not None

        return cls(message.id, message.guild.id)

    @classmethod
    def from_database(cls, item: tuple[int, int, int]):
        return cls(item[1], item[2])
