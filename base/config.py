from asyncio import Lock
from pathlib import Path

from attr import define, field, fields, has

from base.database import Database, db
from dao.dao import BaseDAO


class ConfigDao(BaseDAO):
    def __init__(self, db: Database):
        BaseDAO.__init__(self, db)

    async def load(self, guild_id: int) -> "GuildConfig":
        # unless we switch to ORM I can't think of a better way
        query = await self.fetch_one(
            """
            SELECT
                g.tplaylist,
                g.koko_role,
                e.play,
                e.stop,
                e.queue,
                e.success,
                e.repeat,
                e.error,
                e.denpabot,
                e.wood,
                e.same,
                e.take,
                e.cat1,
                e.uwu,
                e.cunny,
                e.cringe,
                w.threshold,
                w.channel_id,
                c.threshold,
                c.channel_id,
                c.expire_time,
                c.timeout_time,
                d.channel_id
            FROM guildcfg AS g
            JOIN emojicfg AS e ON g.guild_id = e.guild_id
            JOIN woodcfg AS w ON g.guild_id = w.guild_id
            JOIN cringecfg AS c ON g.guild_id = c.guild_id
            JOIN deleteguardcfg as d on g.guild_id = d.guild_id
            WHERE g.guild_id = ?;
                                """,
            (guild_id,),
        )

        return GuildConfig(
            emoji=Emoji(*query[2:16]),
            tplaylist=query[0],
            koko_role=query[1],
            wood=Wood(*query[16:18]),
            cringe=Cringe(*query[18:22]),
            delete_guard=DeleteGuard(query[22]),
        )


@define
class Emoji:
    play: str = field(default="▶️")
    stop: str = field(default="⏹️")
    queue: str = field(default="📄")
    success: str = field(default="☑️")
    repeat: str = field(default="🔁")
    error: str = field(default="❌")
    denpabot: str = field(default=":satellite:")
    wood: str = field(default="🪵")
    same: str = field(default="🦈")
    take: str = field(default="🎍")
    cat1: str = field(default="<:cat1:856666094277361745>")
    uwu: str = field(default="<:UwU:856664498094342205>")
    cunny: str = field(default="<:Cunny:856666244006281256>")
    cringe: str = field(default="🔴")


@define
class Wood:
    threshold: int = field(default=5)
    channel_id: int | None = field(default=None)


@define
class Cringe:
    threshold: int = field(default=5)
    channel_id: int | None = field(default=None)
    expire_time: int = field(default=20 * 60)  # s
    timeout_time: float = field(default=10 * 60 + 6)  # s


@define
class DeleteGuard:
    channel_id: int | None = field(default=None)


@define
class GuildConfig:
    emoji: Emoji = field(factory=Emoji)

    tplaylist: str = field(default="PLb1JKHu_D4MTBXu-8MCFBJ855RpoUuYTf")
    koko_role: int | None = field(default=None)

    wood: Wood = field(factory=Wood)
    cringe: Cringe = field(factory=Cringe)
    delete_guard: DeleteGuard = field(factory=DeleteGuard)


class Config:
    _instances: dict[int, GuildConfig] = {}  # key is guild_id
    _locks: dict[int, Lock] = {}
    _lock: Lock = Lock()

    _base_path = Path("persist/config")
    _dao = ConfigDao(db=db)

    _TABLE_MAP = {
        "guildcfg": "guildcfg",
        "emoji": "emojicfg",
        "wood": "woodcfg",
        "cringe": "cringecfg",
        "delete_guard": "deleteguardcfg",
    }

    @classmethod
    async def load(cls, guild_id: int) -> GuildConfig:
        # TODO: init the config dbs if they don't exist
        async with cls._lock:
            if guild_id in cls._instances:
                return cls._instances[guild_id]

        cfg = await cls._dao.load(guild_id)

        cls._instances[guild_id] = cfg

        return cfg

    @classmethod
    async def update_db(
        cls, guild_id: int, db_name: str | None, key: str | None, value: str | None
    ):
        async with cls._lock:
            cfg = cls._instances.get(guild_id, GuildConfig())
            if db_name:
                cfg = getattr(cfg, db_name)

            if key is not None and value is not None:
                cols = {
                    f.name
                    for f in fields(type(cfg))
                    if not has(type(getattr(cfg, f.name)))
                }
                if key not in cols:
                    raise KeyError(f"Unknown config key: {key}")

                table = cls._TABLE_MAP[db_name or "guildcfg"]
                await cls._dao.write(
                    f"UPDATE {table} SET {key} = ? WHERE guild_id = ?",
                    (value, guild_id),
                )
                return

            await cls._upsert_section(guild_id, db_name or "guildcfg", cfg)

    @classmethod
    async def _upsert_section(cls, guild_id: int, db_name: str, cfg) -> None:
        table = cls._TABLE_MAP[db_name]

        cols: list[str] = []
        vals: list = []
        for f in fields(type(cfg)):
            v = getattr(cfg, f.name)
            if has(type(v)):
                continue
            cols.append(f.name)
            vals.append(v)

        placeholders = ", ".join("?" for _ in cols)
        updates = ", ".join(f"{c} = excluded.{c}" for c in cols)
        await cls._dao.write(
            f"""
            INSERT INTO {table} (guild_id, {", ".join(cols)})
            VALUES (?, {placeholders})
            ON CONFLICT(guild_id) DO UPDATE SET {updates}
            """,
            (guild_id, *vals),
        )

        for f in fields(type(cfg)):
            v = getattr(cfg, f.name)
            if has(type(v)):
                await cls._upsert_section(guild_id, f.name, v)

    @classmethod
    def _lock_(cls, guild_id: int) -> Lock:
        if guild_id not in cls._locks:
            cls._locks[guild_id] = Lock()
        return cls._locks[guild_id]

    @staticmethod
    def _guild_from_dict(data: dict) -> GuildConfig:
        return GuildConfig(
            emoji=Emoji(**data.get("emoji", Emoji())),
            tplaylist=data.get("tplaylist", "PLb1JKHu_D4MTBXu-8MCFBJ855RpoUuYTf"),
            koko_role=data.get("koko_role", None),
            wood=Wood(**data.get("wood", Wood())),
            cringe=Cringe(**data.get("cringe", Cringe())),
            delete_guard=DeleteGuard(**data.get("delete_guard", DeleteGuard())),
        )
