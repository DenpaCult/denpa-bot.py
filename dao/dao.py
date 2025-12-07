from sqlite3 import Cursor
from database import Database
from models.blacklist import BlacklistRole


class BaseDAO:
    def __init__(self, db: Database):
        self.db = db

    def write(self, query: str, params=()) -> Cursor:
        cur = self.db.con.cursor()
        cur.execute(query, params)
        self.db.con.commit()

        return cur

    def read(self, query: str, params=()) -> Cursor:
        cur = self.db.con.cursor()
        cur.execute(query, params)

        return cur

    def fetch_one(self, query, params=()):
        return self.read(query, params).fetchone()

    def fetch_all(self, query, params=()):
        return self.read(query, params).fetchall()
