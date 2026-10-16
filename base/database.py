import importlib
import logging
import os
import pkgutil
import sqlite3

import schemas


class Database:
    con: sqlite3.Connection

    @property
    def logger(self):
        return logging.getLogger(__name__)

    def __init__(self, path: str):
        self.con = sqlite3.connect(path)

    def setup(self):
        cur = self.con.cursor()

        for module in pkgutil.iter_modules(schemas.__path__):
            if module.name.startswith("_"):
                continue

            schema = importlib.import_module(
                    f"{schemas.__name__}.{module.name}"
                    )

            if not hasattr(schema, "SCHEMA"):
                continue

            try:
                cur.execute(schema.SCHEMA)
            except sqlite3.Error:
                self.logger.exception("Failed to execute schema: %s",
                                      module.name)
                print(schema.SCHEMA)
                raise

        self.con.commit()
        self.logger.info("setup complete")


db = Database(os.environ.get("TOROMI_DB_PATH", "persist/toromi.db"))
