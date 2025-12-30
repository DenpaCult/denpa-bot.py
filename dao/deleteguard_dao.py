import logging

from base.database import Database
from dao.dao import BaseDAO
from models.delete_guard import GuardedUser

"""
CREATE TABLE IF NOT EXISTS deleteguard (
        user_id INTEGER NOT NULL,
        guild_id INTEGER NOT NULL
);
"""


class DeleteGuardDAO(BaseDAO):
    def __init__(self, db: Database):
        BaseDAO.__init__(self, db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    def add(self, model: GuardedUser):
        self.write(
            "INSERT INTO deleteguard (user_id, guild_id) VALUES(?, ?);",
            (model.id, model.guild_id),
        )

    def remove(self, model: GuardedUser):
        self.write("DELETE FROM deleteguard WHERE user_id=?", (model.id,))

    def get_all(self, guild_id: int) -> list[GuardedUser]:
        return list(
            map(
                lambda x: GuardedUser.from_database(x),
                self.fetch_all(
                    "SELECT * FROM deleteguard WHERE guild_id=?;", (guild_id,)
                ),
            )
        )

    def get_one(self, model: GuardedUser) -> GuardedUser:
        return self.fetch_one(
            "SELECT * FROM deleteguard WHERE user_id=? AND guild_id=?",
            (model.id, model.guild_id),
        )

    def exists(self, model: GuardedUser) -> bool:
        return bool(
            self.fetch_one(
                "SELECT * FROM deleteguard WHERE user_id=? AND guild_id=?",
                (model.id, model.guild_id),
            )
        )
