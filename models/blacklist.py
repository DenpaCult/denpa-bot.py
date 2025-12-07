from discord import Role


class BlacklistRole:
    """
    blacklisted roles for role command
    """

    def __init__(self, id):
        self.id = id

    def from_role(role: Role) -> type["BlacklistRole"]:
        return BlacklistRole(role.id)
