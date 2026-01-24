import json
import logging
from os import makedirs, replace
from pathlib import Path
from attr import define, field, asdict, attrs
from asyncio import Lock

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
    channel_id: int = field(default=1090086858635096086)

@define
class Cringe:
    threshold: int = field(default=0)
    channel_id: int = field(default=1090086858635096086)
    expire_time: int = field(default=20)
    timeout_time: int = field(default=10)


@define
class DeleteGuard:
    channel_id: int = field(default=1090086858635096086)


@define
class GuildConfig:
    prefix: str = field(default=";;")
    emoji: Emoji = field(factory=Emoji)

    tplaylist: str = field(default="PLb1JKHu_D4MTBXu-8MCFBJ855RpoUuYTf")
    default_roles: list[int] = field(default=[987793980227985518])
    koko_role: int = field(default=856669801005711401)

    wood: Wood = field(factory=Wood)
    cringe: Cringe = field(factory=Cringe)
    delete_guard: DeleteGuard = field(factory=DeleteGuard)


class Config:
    _instances: dict[int, GuildConfig] = {} # key is guild_id
    _locks: dict[int, Lock] = {}

    _base_path = Path("persist/config")


    @classmethod
    async def load(cls, guild_id: int) -> GuildConfig:
        async with cls._lock(guild_id):
            if guild_id in cls._instances:
                return cls._instances[guild_id]

        path = cls._base_path / f"{guild_id}.json"

        if not path.exists():
            cfg = GuildConfig()
            async with cls._lock(guild_id):
                cls._instances[guild_id] = cfg
            await cls.save(guild_id)
            return cfg

        async with cls._lock(guild_id):
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            
            cfg = cls._guild_from_dict(raw)           
            cls._instances[guild_id] = cfg

        return cfg

    @classmethod
    async def save(cls, guild_id: int):
        async with cls._lock(guild_id):
            if guild_id not in cls._instances:
                raise KeyError("Guild config not loaded")
            
            cfg = cls._instances[guild_id]
            path = cls._base_path / f"{guild_id}.json"
            tmp = path.with_suffix(".json.tmp")
            
            makedirs(cls._base_path, exist_ok=True)
            
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(
                    asdict(cfg),
                    f,
                    indent=4,
                    ensure_ascii=False
                )
            
            replace(tmp, path)

    @classmethod
    def _lock(cls, guild_id: int) -> Lock:
        if guild_id not in cls._locks:
            cls._locks[guild_id] = Lock()
        return cls._locks[guild_id]


    @staticmethod
    def _guild_from_dict(data: dict) -> GuildConfig:
        return GuildConfig(
            prefix=data.get("prefix", ";;"),
            emoji=Emoji(**data.get("emoji", Emoji())),
            tplaylist=data.get("tplaylist", "PLb1JKHu_D4MTBXu-8MCFBJ855RpoUuYTf"),
            default_roles=data.get("default_roles", [987793980227985518]),
            koko_role=data.get("koko_role", 856669801005711401),
            wood=Wood(**data.get("wood", Wood())),
            cringe=Cringe(**data.get("cringe", Cringe())),
            delete_guard=DeleteGuard(**data.get("delete_guard", DeleteGuard())),
        )


