import os
import logging
import sqlite3

from schemas.wood import SCHEMA as WOOD_SCHEMA
from schemas.cringe import SCHEMA as CRINGE_SCHEMA
from schemas.blacklist import SCHEMA as BLACKLIST_SCHEMA
from schemas.deleteguard import SCHEMA as DELETEGUARD_SCHEMA

class Database:
    con: sqlite3.Connection

    @property
    def logger(self):
        return logging.getLogger(__name__)

    def __init__(self, path: str):
        self.con = sqlite3.connect(path)

    def setup(self):
        schemas = [
            WOOD_SCHEMA,
            CRINGE_SCHEMA,
            BLACKLIST_SCHEMA,
            DELETEGUARD_SCHEMA,
        ]

        cur = self.con.cursor()
        for schema in schemas:
            cur.execute(schema)

        self.con.commit()
        self.logger.info("setup complete")

db = Database(os.environ.get("TOROMI_DB_PATH", "persist/toromi.db"))
