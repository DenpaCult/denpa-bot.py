from dataclasses import dataclass


@dataclass
class Cum:
    """
    A Cum Event
    """

    guild_id: int
    cummer_id: int
    cummee_id: int
    created_at_ms: int | None = None  # will be None for events pre-rewrite
