from discord import Role


class BlacklistRole:
    """
    blacklisted roles for role command
    """

    @classmethod
    def from_role(cls, role: Role):
        return cls(role.name)

    @classmethod
    def from_database(cls, item: tuple[str,str]):
        return cls(item[1])
    
    def __init__(self, name: str):
        self.name: str = name
    
