from dao.dao import BaseDAO
from models.wood import WoodMessage


class WoodDAO(BaseDAO):
    async def add(self, model: WoodMessage) -> bool:
        """returns False if the message was already on the woodboard"""
        cur = await self.write(
            "INSERT OR IGNORE INTO wood (message_id, guild_id) VALUES (?, ?);",
            (model.id, model.guild_id),
        )

        return cur.rowcount == 1
