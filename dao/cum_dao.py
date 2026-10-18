import logging

from base.database import Database
from dao.dao import BaseDAO
from models.cum import Cum


class CumDAO(BaseDAO):
    def __init__(self, db: Database):
        BaseDAO.__init__(self, db)
        self.logger = logging.getLogger(__name__)

    async def add(self, model: Cum):
        await self.write(
            "INSERT INTO cum (guild_id, cummer_id, cummed_on_id, created_at_ms) VALUES (?, ?, ?, ?);",
            (model.guild_id, model.cummer_id, model.cummee_id, model.created_at_ms),
        )

    async def get_cummed_count(self, guild_id: int, user_id: int) -> int:
        """How many times user_id has cummed in guild_id"""
        return (
            await self.fetch_one(
                "SELECT COUNT(*) FROM cum WHERE guild_id = ? AND cummer_id = ?;",
                (guild_id, user_id),
            )
        )[0]

    async def get_cummed_on_count(self, guild_id: int, user_id: int) -> int:
        """How many times user_id has been cummed on in guild_id"""
        return (
            await self.fetch_one(
                "SELECT COUNT(*) FROM cum WHERE guild_id = ? AND cummed_on_id = ?;",
                (guild_id, user_id),
            )
        )[0]

    async def get_most_cummed_on_user(self, guild_id: int, user_id: int) -> int | None:
        """might return the id of the user that user_id has cummed on the most in guild_id"""
        row = await self.fetch_one(
            """
            SELECT cummed_on_id
            FROM cum
            WHERE guild_id = ? AND cummer_id = ?
            GROUP BY cummed_on_id
            ORDER BY COUNT(*) DESC
            LIMIT 1;
            """,
            (guild_id, user_id),
        )

        return row[0] if row else None

    async def get_most_cummer_on_you(self, guild_id: int, user_id: int) -> int | None:
        """might return the id of the user that has cummed on user_id the most in guild_id"""
        row = await self.fetch_one(
            """
            SELECT cummer_id
            FROM cum
            WHERE guild_id = ? AND cummed_on_id = ?
            GROUP BY cummer_id
            ORDER BY COUNT(*) DESC
            LIMIT 1;
            """,
            (guild_id, user_id),
        )

        return row[0] if row else None
