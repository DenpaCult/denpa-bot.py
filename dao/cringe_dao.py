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

    async def add(self, model: CringeMessage) -> bool:
        """returns False if the message was already marked as cringe"""
        cur = await self.write(
            "INSERT OR IGNORE INTO cringe (message_id, guild_id, author_id) VALUES (?, ?, ?);",
            (model.id, model.guild_id, model.author_id),
        )

        return cur.rowcount == 1

    async def count(self, guild_id: int, user_id: int) -> int:
        """number of the user's messages that have been marked as cringe"""
        return (await self.fetch_one(
            "SELECT COUNT(*) FROM cringe WHERE guild_id = ? AND author_id = ?;",
            (guild_id, user_id),
        ))[0]
