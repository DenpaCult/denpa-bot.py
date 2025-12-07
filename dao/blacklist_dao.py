from dao.dao import BaseDAO, Database
import logging
from models.blacklist import BlackList


init = '''
CREATE TABLE blacklists (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	role_name TEXT NOT NULL,
	role_id INTEGER NOT NULL
);
'''


class BlackListDao(BaseDAO):
    def __init__(self, db: Database = Database("toromi.db")):
        BaseDAO.__init__(self, db)
        self.logger = logging.getLogger()

    def newBlackList(self, blacklist: BlackList):
        res = self.fetch_one("SELECT * FROM blacklists WHERE role_name = ? AND role_id = ?;", (blacklist.name, blacklist.id))
        if res:
            self.logger.warn(f"role {blacklist.name} already exists: {res}")
            return
        
        self.logger.info("inserting")
        self.execute("INSERT INTO blacklists (role_name, role_id) VALUES(?, ?);", (blacklist.name, blacklist.id))
