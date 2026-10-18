"""
"CREATE TABLE cum (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    cummer_id INTEGER NOT NULL,
    cummed_on_id INTEGER NOT NULL
);
"""
import logging

from base.database import Database
from dao.dao import BaseDAO
from models.cum import Cum


class CumDAO(BaseDAO):

    def __init__(self, db: Database):
        BaseDAO.__init__(self, db)
        self.logger = logging.getLogger(__name__)

    async def add(self, model: Cum):    
        await self.write("""
                         INSERT INTO cum (
                         guild_id,
                         cummer_id,
                         cummed_on_id)
                         VALUES(?, ?, ?);
                         """, (
                             model.guild_id,
                             model.cummer_id,
                             model.cummee_id
                             )
                         )

    async def remove(self, model: Cum):
        await self.write("""
                         DELETE FROM cum
                         WHERE guild_id=?
                         AND cummed_on_id=?
                         AND cummer_id=?
                         """, (
                             model.guild_id,
                             model.cummer_id,
                             model.cummee_id,
                             )
                         )

    async def get_all(self) -> list[Cum]:
        return [Cum(x[0], x[1], x[2])
                for x in await self.fetch_all("""
                                              SELECT (
                                              guild_id, cummed_on_id, cummer_id
                                              ) FROM cum;
                                              """)]

    async def get_cummed_count(self, user_id: int, guild_id: int) -> int:
        # How many times the user has cummed
        data = await self.fetch_all("""
                                    SELECT COUNT(*) FROM cum
                                    WHERE cummer_id=?
                                    AND guild_id=?""", (user_id, guild_id))
        return data[0][0]

    async def get_cummed_on_count(self, user_id: int, guild_id: int) -> int:
        # How many times the user has been cummed on
        data = await self.fetch_all("""
                                    SELECT COUNT(*) FROM cum
                                    WHERE cummed_on_id=?
                                    AND guild_id=?
                                    """, (user_id, guild_id)
                                    )
        return data[0][0]

    async def get_most_cummed_on_user(self, user_id, guild_id) -> int | None:
        # person the user has cummed on the most
        # returns user_id the name should be fetched later
        data = await self.fetch_all("""
                               SELECT cummed_on_id
                               FROM cum
                               WHERE cummer_id = ?
                               AND guild_id = ?
                               GROUP BY cummed_on_id
                               ORDER BY COUNT(cummed_on_id) DESC
                               LIMIT 1;
                              """, (user_id, guild_id))
        data = data[0][0] if data else None
        return data

    async def get_most_cummer_on_you(self, user_id, guild_id) -> int | None:
        # person that has cummed on the user the most
        # returns user_id the name should be fetched later
        data = await self.fetch_all("""
                               SELECT cummer_id
                               FROM cum
                               WHERE cummed_on_id = ?
                               AND guild_id = ?
                               GROUP BY cummer_id
                               ORDER BY COUNT(cummer_id) DESC
                               LIMIT 1;
                              """, (user_id, guild_id))
        data = data[0][0] if data else None
        return data

    # is this gonna be required
    # def get_cummed_on_user_count(self, user_id: int, member_id: int):
    # How many times the user has cummed on a specific member
