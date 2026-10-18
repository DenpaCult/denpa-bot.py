from asyncio import Lock

from attr import define, fields

from base.database import Database, db
from dao.dao import BaseDAO


@define
class Emoji:
    play: str
    stop: str
    queue: str
    success: str
    repeat: str
    error: str
    denpabot: str
    wood: str
    same: str
    take: str
    cat1: str
    uwu: str
    cunny: str
    cringe: str


@define
class Wood:
    threshold: int
    channel_id: int | None


@define
class Cringe:
    threshold: int
    channel_id: int | None
    expire_time: int  # s
    timeout_time: int  # s


@define
class DeleteGuard:
    channel_id: int | None


@define
class GuildConfig:
    """
    Per-server Settings. Defaults live in the tables itself. (see migrations/)
    """

    emoji: Emoji

    tplaylist: str
    koko_role: int | None

    wood: Wood
    cringe: Cringe
    delete_guard: DeleteGuard


# ;;config set tplaylist "..." maps to guild_config table, tplaylist column
# ;;config set wood threshold 123 maps to guild_config table, wood_threshold column
COLUMNS: dict[tuple[str | None, str], tuple[str, str]] = {
    (None, "tplaylist"): ("guild_config", "tplaylist"),
    (None, "koko_role"): ("guild_config", "koko_role_id"),
    ("wood", "threshold"): ("guild_config", "wood_threshold"),
    ("wood", "channel_id"): ("guild_config", "wood_channel_id"),
    ("cringe", "threshold"): ("guild_config", "cringe_threshold"),
    ("cringe", "channel_id"): ("guild_config", "cringe_channel_id"),
    ("cringe", "expire_time"): ("guild_config", "cringe_expire_s"),
    ("cringe", "timeout_time"): ("guild_config", "cringe_timeout_s"),
    ("delete_guard", "channel_id"): ("guild_config", "deleteguard_channel_id"),
    **{("emoji", f.name): ("guild_emoji", f.name) for f in fields(Emoji)},
}


class ConfigDao(BaseDAO):
    def __init__(self, db: Database):
        BaseDAO.__init__(self, db)

    async def ensure(self, guild_id: int):
        """create the server's settings rows with default values, if they don't exist yet"""
        await self.write(
            "INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?);", (guild_id,)
        )
        await self.write(
            "INSERT OR IGNORE INTO guild_emoji (guild_id) VALUES (?);", (guild_id,)
        )

    async def load(self, guild_id: int) -> GuildConfig:
        await self.ensure(guild_id)

        keys = list(COLUMNS)
        select = ", ".join(f"{table}.{column}" for table, column in COLUMNS.values())
        row = await self.fetch_one(
            f"""
            SELECT {select}
            FROM guild_config
            JOIN guild_emoji USING (guild_id)
            WHERE guild_id = ?;
            """,
            (guild_id,),
        )
        values = dict(zip(keys, row))

        def section(name: str | None) -> dict:
            return {key: v for (sec, key), v in values.items() if sec == name}

        return GuildConfig(
            emoji=Emoji(**section("emoji")),
            wood=Wood(**section("wood")),
            cringe=Cringe(**section("cringe")),
            delete_guard=DeleteGuard(**section("delete_guard")),
            **section(None),
        )

    async def set(self, guild_id: int, section: str | None, key: str, value):
        if (section, key) not in COLUMNS:
            raise KeyError(f"Unknown config key: {key}")

        # table and column come from COLUMNS, never from user input
        table, column = COLUMNS[(section, key)]

        await self.ensure(guild_id)
        await self.write(
            f"UPDATE {table} SET {column} = ? WHERE guild_id = ?;", (value, guild_id)
        )


class Config:
    _instances: dict[int, GuildConfig] = {}  # key is guild_id
    _lock: Lock = Lock()

    _dao = ConfigDao(db=db)

    @classmethod
    async def load(cls, guild_id: int) -> GuildConfig:
        async with cls._lock:
            if guild_id not in cls._instances:
                cls._instances[guild_id] = await cls._dao.load(guild_id)

            return cls._instances[guild_id]

    @classmethod
    async def update_db(cls, guild_id: int, db_name: str | None, key: str, value):
        """
        set one setting, e.g. update_db(guild_id, "wood", "threshold", 3).
        raises KeyError for unknown settings and sqlite3.IntegrityError for values of the wrong type
        """
        async with cls._lock:
            await cls._dao.set(guild_id, db_name, key, value)

            cached = cls._instances.get(guild_id)
            if cached is not None:
                target = getattr(cached, db_name) if db_name else cached
                setattr(target, key, value)
