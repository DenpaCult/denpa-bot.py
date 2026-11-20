from dataclasses import dataclass

from discord import Role


@dataclass
class BlacklistRole:
    """
    Roles which are not alllowed to be added/removed using ;;role
    """

    id: int
    guild_id: int

    @classmethod
    def from_role(cls, role: Role):
        return cls(role.id, role.guild.id)
