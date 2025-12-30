from dataclasses import dataclass
from discord import Member


@dataclass
class GuardedUser:
    """
    DeleteGuard object containing the user id of delete guarded members
    """

    id: int
    guild_id: int

    @classmethod
    def from_member(cls, member: Member):
        return cls(member.id, member.guild.id)

    @classmethod
    def from_database(cls, item: tuple[int, int]):
        return cls(item[0], item[1])
