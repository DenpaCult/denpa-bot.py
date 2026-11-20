from sqlite3 import Cursor

from base.database import Database


class BaseDAO:
    # NB: No lock is needed because sqlite3 calls are async and nothing here awaits.
    def __init__(self, db: Database):
        self.db = db

    async def write(self, query: str, params=()) -> Cursor:
        cur = self.db.con.execute(query, params)
        self.db.con.commit()

        return cur

    async def read(self, query: str, params=()) -> Cursor:
        return self.db.con.execute(query, params)

    async def fetch_one(self, query, params=()):
        return (await self.read(query, params)).fetchone()

    async def fetch_all(self, query, params=()) -> list:
        return (await self.read(query, params)).fetchall()
