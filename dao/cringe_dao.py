import logging
from base.database import Database
from dao.dao import BaseDAO
from models.cringe import Cringe

"""
CREATE TABLE cringe (
	message_id INTEGER NOT NULL
);
"""


class CringeDAO(BaseDAO):
    def __init__(self, db: Database = Database("toromi.db")):
        BaseDAO.__init__(self, db)
        self.logger = logging.getLogger(__name__)

    def add(self, model: Cringe):    
        self.write("INSERT INTO cringe (message_id) VALUES(?);", (model.id,))

    def remove(self, model: Cringe):
        self.write("DELETE FROM cringe WHERE message_id=?", (model.id,))

    def get_all(self) -> list[Cringe]:
        return list(map(lambda x: Cringe.from_database(x),self.fetch_all("SELECT * FROM cringe;"))) # fetch_all returns [('streamer',)] for some reason

    def get_one(self, model: Cringe) -> Cringe:
        return self.fetch_one("SELECT * FROM cringe WHERE message_id=?", (model.id,))

