import sqlite3
from base.config import Config


class Database:
    def __init__(self, path: str):
        self.con = sqlite3.connect(path)

# TODO: load from env
db = Database("toromi.db")
