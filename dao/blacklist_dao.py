from base.database import Database
from dao.dao import BaseDAO
import logging
from models.blacklist import BlacklistRole


# FIXME(kajo): this isn't the responsibility of the DAO
# TODO(kajo): figure out how we're going to do migrations or whatever
"""
CREATE TABLE blacklist (
	role_name TEXT NOT NULL,
);
"""


class BlacklistDAO(BaseDAO):
    def __init__(self, db: Database = Database("toromi.db")):
        BaseDAO.__init__(self, db)
        self.logger = logging.getLogger(__name__)

    def add(self, model: BlacklistRole):    
        self.write("INSERT INTO blacklist (role_name) VALUES(?);", (model.name,))

    def remove(self, model: BlacklistRole):
        self.write("DELETE FROM blacklist WHERE role_name=?", (model.name,))

    def get_all(self) -> list[BlacklistRole]:
        return list(map(lambda x: BlacklistRole(x[0]),self.fetch_all("SELECT * FROM blacklist;"))) # fetch_all returns [('streamer',)] for some reason

