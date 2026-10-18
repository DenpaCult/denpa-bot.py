class Cum:
    """
    Cum object containing the id of cummer and cummee
    """

    def __init__(self, guild_id: int, cummer_id: int, cummee_id: int):
        self.guild_id: int = guild_id
        self.cummer_id: int = cummer_id
        self.cummee_id: int = cummee_id
