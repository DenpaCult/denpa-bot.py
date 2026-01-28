from asyncio import Lock
from sqlite3 import Cursor
from base.database import Database

class BaseDAO:
    def __init__(self, db: Database):
        self.db = db
        self.lock = Lock()

    async def write(self, query: str, params=()) -> Cursor:
        async with self.lock:
            cur = self.db.con.cursor()
            cur.execute(query, params)
            self.db.con.commit()

        return cur

    async def read(self, query: str, params=()) -> Cursor:
        async with self.lock:
            cur = self.db.con.cursor()
            cur.execute(query, params)

        return cur

    async def fetch_one(self, query, params=()):
        return (await self.read(query, params)).fetchone()

    async def fetch_all(self, query, params=()) -> list:
        return (await self.read(query, params)).fetchall()
