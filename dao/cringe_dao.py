import logging
from base.database import Database
from dao.dao import BaseDAO
from models.cringe import CringeMessage


class CringeDAO(BaseDAO):
    def __init__(self, db: Database):
        BaseDAO.__init__(self, db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    async def add(self, model: CringeMessage):
        await self.write(
            "INSERT INTO cringe (message_id, author_id, guild_id) VALUES(?, ?, ?);",
            (model.id, model.author_id, model.guild_id),
        )

    async def remove(self, model: CringeMessage):
        await self.write("DELETE FROM cringe WHERE message_id=?", (model.id,))

    async def get_all(self, guild_id: int) -> list[CringeMessage]:
        return list(
            map(
                lambda x: CringeMessage.from_database(x),
                await self.fetch_all("SELECT * FROM cringe WHERE guild_id=?;", (guild_id,)),
            )
        )

    async def get_one(self, model: CringeMessage) -> CringeMessage:
        return await self.fetch_one("SELECT * FROM cringe WHERE message_id=?", (model.id,))

    async def count(self, guild_id: int, user_id: int) -> int:
        return (await self.fetch_one(
            "SELECT COUNT(*) FROM cringe WHERE guild_id=? AND author_id=?;",
            (guild_id, user_id),
        ))[0]
