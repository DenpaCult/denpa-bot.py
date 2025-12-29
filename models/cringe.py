from dataclasses import dataclass
from discord import Message


@dataclass
class CringeMessage:
    """a discord message that has been voted as cringe"""

    id: int
    author_id: int
    guild_id: int

    @classmethod
    def from_message(cls, message: Message):
        if message.guild is None:
            raise Exception("message.guild can NOT be None")

        return cls(message.id, message.author.id, message.guild.id)

    @classmethod
    def from_database(cls, item: tuple[int, int, int, int]):
        return cls(item[1], item[2], item[3])
