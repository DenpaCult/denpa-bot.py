from dataclasses import dataclass

from discord import Message


@dataclass
class CringeMessage:
    """a discord message that has been voted as cringe"""

    id: int
    author_id: int | None  # may be null if migrated from old bot
    guild_id: int

    @classmethod
    def from_message(cls, message: Message):
        assert message.guild is not None

        return cls(message.id, message.author.id, message.guild.id)
