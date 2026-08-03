from dataclasses import dataclass


@dataclass
class EditCfg:
    """
    Config model in the db for the "old messages" edit event
    """

    id: int
    guild_id: int
    time_limit_h: int # hours
    report_channel_id: int
    mention_list: list[str]
    ignore_roles: list[str]

    @classmethod
    def from_database(cls, item: tuple[int, int, int, int, list[str], list[str]]):
        return cls(*item)
