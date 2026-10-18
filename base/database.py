"""
Schema History lives in migrations/. Should be NNNN_description.sql. 

Rules:
- never edit a migration once it has run on prod (so once a commit hits main)
- each migration runs in a transaction, don't put BEGIN or COMMIT in it.
- See SQLite's ALTER TABLE, but changing a column's type requires rebuilding a table
"""

import logging
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


@dataclass
class Migration:
    version: int
    name: str
    sql: str


def load_migrations() -> list[Migration]:
    """every migration in migrations/, in order"""
    found: list[Migration] = []

    for file in MIGRATIONS_DIR.glob("*.sql"):
        match = re.fullmatch(r"(\d{4})_\w+", file.stem)
        if match is None:
            raise RuntimeError(f"migration {file.name} isn't named NNNN_description.sql")

        found.append(Migration(int(match[1]), file.stem, file.read_text(encoding="utf-8")))

    found.sort(key=lambda m: m.version)

    expected = list(range(1, len(found) + 1))
    if [m.version for m in found] != expected:
        raise RuntimeError(
            f"migrations must be numbered 0001, 0002, ... with no gaps or duplicates, found: {[m.name for m in found]}"
        )

    return found


class Database:
    con: sqlite3.Connection

    @property
    def logger(self):
        return logging.getLogger(__name__)

    def __init__(self, path: str):
        self.con = sqlite3.connect(path)

    @property
    def version(self) -> int:
        return self.con.execute("PRAGMA user_version;").fetchone()[0]

    def setup(self):
        """bring the database up to the latest schema version"""
        pending = load_migrations()
        latest = pending[-1].version if pending else 0
        current = self.version

        if current > latest:
            raise RuntimeError(
                f"database is at schema version {current}, but this code only knows up to {latest}. "
                "is an older version of the bot running against a newer database?"
            )

        for migration in pending:
            if migration.version <= current:
                continue

            self.logger.info(f"applying migration {migration.name}")

            try:
                # the version bump is inside the transaction, so a failure leaves both untouched
                self.con.executescript(
                    f"BEGIN;\n{migration.sql}\nPRAGMA user_version = {migration.version};\nCOMMIT;"
                )
            except sqlite3.Error:
                if self.con.in_transaction:
                    self.con.rollback()

                self.logger.exception(f"migration {migration.name} failed, database left at version {self.version}")
                raise

        self.logger.info(f"setup complete, schema version {self.version}")


db = Database(os.environ.get("TOROMI_DB_PATH", "persist/toromi.db"))
