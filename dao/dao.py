import sqlite3

class Database:
    def __init__(self, path: str):
        self.path = path

    def connect(self):
        return sqlite3.connect(self.path)


class BaseDAO:
    def __init__(self, db: Database):
        self.db = db

    def execute(self, query, params=()):
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            return cur

    def fetch_one(self, query, params=()):
        cur = self.execute(query, params)
        return cur.fetchone()

    def fetch_all(self, query, params=()):
        cur = self.execute(query, params)
        return cur.fetchall()

