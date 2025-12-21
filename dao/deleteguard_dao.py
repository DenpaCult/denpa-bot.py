"""
CREATE TABLE IF NOT EXISTS deleteguard (
	user_id INTEGER NOT NULL
);
"""
import logging
from base.database import Database
from dao.dao import BaseDAO
from models.delete_guard import DeleteGuard


class DeleteGuardDAO(BaseDAO):
    def __init__(self, db: Database = Database("toromi.db")):
        BaseDAO.__init__(self, db)
        self.logger = logging.getLogger(__name__)

    def add(self, model: DeleteGuard):    
        self.write("INSERT INTO deleteguard (user_id) VALUES(?);", (model.id,))

    def remove(self, model: DeleteGuard):
        self.write("DELETE FROM deleteguard WHERE user_id=?", (model.id,))

    def get_all(self) -> list[DeleteGuard]:
        return list(map(lambda x: DeleteGuard.from_database(x),self.fetch_all("SELECT * FROM deleteguard;"))) # fetch_all returns [('streamer',)] for some reason

    def get_one(self, model: DeleteGuard) -> DeleteGuard:
        return self.fetch_one("SELECT * FROM deleteguard WHERE user_id=?", (model.id,))

    def exists(self, model: DeleteGuard) -> bool:
        return bool(self.fetch_one("SELECT * FROM deleteguard WHERE user_id=?", (model.id,)))

