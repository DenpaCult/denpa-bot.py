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

    async def add(self, model: BlacklistRole):
        await self.write("INSERT INTO blacklist (role_id) VALUES(?);", (model.id,))

    async def remove(self, model: BlacklistRole):
        await self.write("DELETE FROM blacklist WHERE role_id=?", (model.id,))

    async def get_all(self) -> list[BlacklistRole]:
        return list(
            map(
                lambda x: BlacklistRole(x[0]),
                await self.fetch_all("SELECT * FROM blacklist;"),
            )
        )
