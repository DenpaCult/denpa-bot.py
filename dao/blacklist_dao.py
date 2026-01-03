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

    def add(self, model: BlacklistRole):
        self.write("INSERT INTO blacklist (role_id) VALUES(?);", (model.id,))

    def remove(self, model: BlacklistRole):
        self.write("DELETE FROM blacklist WHERE role_id=?", (model.id,))

    def get_all(self) -> list[BlacklistRole]:
        return list(
            map(
                lambda x: BlacklistRole(x[0]),
                self.fetch_all("SELECT * FROM blacklist;"),
            )
        )  # fetch_all returns [('streamer',)] for some reason
