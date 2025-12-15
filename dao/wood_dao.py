
# putting the init codes in the daos so we can combine them later in a sql file
"""
CREATE TABLE IF NOT EXISTS wood (
	message_id INTEGER NOT NULL
);
"""
import logging
from base.database import Database
from dao.dao import BaseDAO
from models.wood import Wood

"""
CREATE TABLE wood (
	message_id INTEGER NOT NULL
);
"""


class WoodDAO(BaseDAO):
    def __init__(self, db: Database = Database("toromi.db")):
        BaseDAO.__init__(self, db)
        self.logger = logging.getLogger(__name__)

    def add(self, model: Wood):    
        self.write("INSERT INTO wood (message_id) VALUES(?);", (model.id,))

    def remove(self, model: Wood):
        self.write("DELETE FROM wood WHERE message_id=?", (model.id,))

    def get_all(self) -> list[Wood]:
        return list(map(lambda x: Wood.from_database(x),self.fetch_all("SELECT * FROM wood;")))

    def get_one(self, model: Wood) -> Wood:
        return self.fetch_one("SELECT * FROM wood WHERE message_id=?", (model.id,))

