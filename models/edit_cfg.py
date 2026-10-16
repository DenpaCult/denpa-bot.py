from collections.abc import Sequence
from dataclasses import dataclass


@dataclass
class EditCfg:
    """
    Config model in the db for the "old messages" edit event
    """

    id: int
    guild_id: int
    time_limit_h: int  # hours
    report_channel_id: int
    mention_list: Sequence[str]
    ignore_roles: Sequence[str]

    @classmethod
    def from_database(cls, item: tuple[int, int, int, int, str, str]):
        return cls(
            item[0],
            item[1],
            item[2],
            item[3],
            item[4].split(", ") if item[4] else [],
            item[5].split(", ") if item[5] else [],
        )
