from dao.dao import BaseDAO, Database
import logging
from models.blacklist import BlacklistRole


# FIXME(kajo): this isn't the responsibility of the DAO
# TODO(kajo): figure out how we're going to do migrations or whatever
init = """
CREATE TABLE blacklists (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	role_name TEXT NOT NULL,
	role_id INTEGER NOT NULL
);
"""


class BlacklistDAO(BaseDAO):
    def __init__(self, db: Database = Database("toromi.db")):
        BaseDAO.__init__(self, db)
        self.logger = logging.getLogger(__name__)

    def add(self, model: BlacklistRole):
        self.write("INSERT INTO blacklist (role_id) VALUES(?);", (model.id,))

    # TODO(kajo): make these BlacklistRoles
    def get_all(self):
        return self.fetch_all("SELECT * FROM blacklist;")

    # def newBlackList(self, blacklist: BlackList):
    #     res = self.fetch_one("SELECT * FROM blacklists WHERE role_name = ? AND role_id = ?;", (blacklist.name, blacklist.id))
    #     if res:
    #         self.logger.warn(f"role {blacklist.name} already exists: {res}")
    #         return

    #     self.logger.log("inserting")
    #     self.execute("INSERT INTO blacklists (role_name, role_id) VALUES(?, ?);", (blacklist.name, blacklist.id))
