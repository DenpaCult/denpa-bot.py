import logging

from base.database import Database
from dao.dao import BaseDAO
from models.wood import WoodMessage


class WoodDAO(BaseDAO):
    def __init__(self, db: Database):
        BaseDAO.__init__(self, db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    def add(self, model: WoodMessage):
        self.write(
            "INSERT INTO wood (message_id, guild_id) VALUES(?, ?);",
            (model.id, model.guild_id),
        )

    def remove(self, model: WoodMessage):
        self.write("DELETE FROM wood WHERE message_id=?", (model.id,))

    def get_all(self, guild_id: int) -> list[WoodMessage]:
        return list(
            map(
                lambda x: WoodMessage.from_database(x),
                self.fetch_all("SELECT * FROM wood WHERE guild_id=?;", (guild_id,)),
            )
        )

    def get_one(self, model: WoodMessage) -> WoodMessage:
        return self.fetch_one("SELECT * FROM wood WHERE message_id=?", (model.id,))
