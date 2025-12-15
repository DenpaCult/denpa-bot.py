"""
"CREATE TABLE cum (
	cummer_id INTEGER NOT NULL,
	cummed_on_id INTEGER NOT NULL
);
"""
import logging
from base.database import Database
from dao.dao import BaseDAO
from models.cum import Cum


class CumDAO(BaseDAO):
    def __init__(self, db: Database = Database("toromi.db")):
        BaseDAO.__init__(self, db)
        self.logger = logging.getLogger(__name__)

    def add(self, model: Cum):    
        self.write("INSERT INTO cum (cummer_id, cummed_on_id) VALUES(?, ?);", (model.cummer_id, model.cummee_id))

    def remove(self, model: Cum):
        self.write("DELETE FROM cum WHERE cummer_id=? AND cummed_on_id=?", (model.cummer_id, model.cummee_id,))

    def get_all(self) -> list[Cum]:
        return list(map(lambda x: Cum(x[0],x[1]),self.fetch_all("SELECT * FROM cum;")))

    def get_cummed_count(self, user_id: int): # How many times the user has cummed
        data = self.fetch_all("SELECT * FROM cum WHERE cummer_id=?", (user_id,))
        return len(list(map(lambda x: (x[0],x[1]) , data)))

    def get_cummed_on_count(self, user_id: int): # How many times the user has been cummed on
        data = self.fetch_all("SELECT * FROM cum WHERE cummed_on_id=?", (user_id,))
        return len(list(map(lambda x: (x[0],x[1]) , data)))

    # is this gonna be required
    # def get_cummed_on_user_count(self, user_id: int, member_id: int): # How many times the user has cummed on a specific member
