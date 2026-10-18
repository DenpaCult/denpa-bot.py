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
