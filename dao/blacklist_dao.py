import logging

from base.database import Database
from dao.dao import BaseDAO
from models.blacklist import BlacklistRole


class BlacklistDAO(BaseDAO):
    def __init__(self, db: Database):
        BaseDAO.__init__(self, db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    async def add(self, model: BlacklistRole) -> bool:
        """returns False if the role was already blacklisted"""
        cur = await self.write(
            "INSERT OR IGNORE INTO blacklist (role_id, guild_id) VALUES (?, ?);",
            (model.id, model.guild_id),
        )

        return cur.rowcount == 1

    async def remove(self, model: BlacklistRole) -> bool:
        """returns False if the role wasn't blacklisted"""
        cur = await self.write("DELETE FROM blacklist WHERE role_id = ?;", (model.id,))

        return cur.rowcount == 1

    async def get_all(self, guild_id: int) -> list[BlacklistRole]:
        rows = await self.fetch_all(
            "SELECT role_id, guild_id FROM blacklist WHERE guild_id = ?;", (guild_id,)
        )

        return [BlacklistRole(id=role_id, guild_id=guild_id) for role_id, guild_id in rows]
