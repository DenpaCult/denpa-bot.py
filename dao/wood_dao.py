
# putting the init codes in the daos so we can combine them later in a sql file
"""
CREATE TABLE IF NOT EXISTS wood (
	message_id INTEGER NOT NULL
);
"""

from dao.dao import BaseDAO, Database
import logging


class WoodDAO(BaseDAO):
    def __init__(self, db: Database = Database("toromi.db")):
        BaseDAO.__init__(self, db)
        self.logger = logging.getLogger(__name__)

    # ill start working on the DAOs when kajon is finished with the BaseDAO -hoog
