from discord import Role


class BlacklistRole:
    """
    blacklisted roles for role command
    """

    @classmethod
    def from_role(cls, role: Role):
        return cls(role.id)

    @classmethod
    def from_database(cls, item: tuple[int,int]):
        return cls(item[1])
    
    def __init__(self, id: int):
        self.id: int = id
