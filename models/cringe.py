from discord import Message

class Cringe:
    """
    Cringe object containing the message id of the message that has been reacted to
    """

    @classmethod
    def from_message(cls, message: Message):
        return cls(message.id)

    @classmethod
    def from_database(cls, item: tuple[int,int]):
        return cls(item[1])
    
    def __init__(self, id: int):
        self.id: int = id
