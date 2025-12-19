from discord import User

class DeleteGuard:
    """
    DeleteGuard object containing the user id of delete guarded members
    """

    @classmethod
    def from_user(cls, user: User):
        return cls(user.id)

    @classmethod
    def from_database(cls, item: tuple[int,int]):
        return cls(item[1])
    
    def __init__(self, id: int):
        self.id: int = id
