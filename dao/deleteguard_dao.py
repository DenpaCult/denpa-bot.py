import logging

from base.database import Database
from dao.dao import BaseDAO
from models.delete_guard import GuardedUser


class DeleteGuardDAO(BaseDAO):
    def __init__(self, db: Database):
        BaseDAO.__init__(self, db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    async def add(self, model: GuardedUser):
        await self.write(
            "INSERT INTO deleteguard (user_id, guild_id) VALUES(?, ?);",
            (model.id, model.guild_id),
        )

    async def remove(self, model: GuardedUser):
        await self.write("DELETE FROM deleteguard WHERE user_id=?", (model.id,))

    async def get_all(self, guild_id: int) -> list[GuardedUser]:
        return list(
            map(
                lambda x: GuardedUser.from_database(x),
                await self.fetch_all(
                    "SELECT * FROM deleteguard WHERE guild_id=?;", (guild_id,)
                ),
            )
        )

    async def get_one(self, model: GuardedUser) -> GuardedUser:
        return await self.fetch_one(
            "SELECT * FROM deleteguard WHERE user_id=? AND guild_id=?",
            (model.id, model.guild_id),
        )

    async def exists(self, model: GuardedUser) -> bool:
        return bool(
            await self.fetch_one(
                "SELECT * FROM deleteguard WHERE user_id=? AND guild_id=?",
                (model.id, model.guild_id),
            )
        )
