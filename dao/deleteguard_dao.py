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

    async def add(self, model: GuardedUser) -> bool:
        """returns False if the user was already guarded"""
        cur = await self.write(
            "INSERT OR IGNORE INTO deleteguard (guild_id, user_id) VALUES (?, ?);",
            (model.guild_id, model.id),
        )

        return cur.rowcount == 1

    async def remove(self, model: GuardedUser) -> bool:
        """returns False if the user wasn't guarded"""
        cur = await self.write(
            "DELETE FROM deleteguard WHERE guild_id = ? AND user_id = ?;",
            (model.guild_id, model.id),
        )

        return cur.rowcount == 1

    async def get_all(self, guild_id: int) -> list[GuardedUser]:
        rows = await self.fetch_all(
            "SELECT user_id, guild_id FROM deleteguard WHERE guild_id = ?;", (guild_id,)
        )

        return [GuardedUser(id=user_id, guild_id=guild_id) for user_id, guild_id in rows]

    async def exists(self, model: GuardedUser) -> bool:
        return bool(
            await self.fetch_one(
                "SELECT 1 FROM deleteguard WHERE guild_id = ? AND user_id = ?;",
                (model.guild_id, model.id),
            )
        )
