import sqlite3
from config.config import config


class Database:
    def __init__(self, path: str):
        self.con = sqlite3.connect(path)


db = Database(config.read_config()["sqlite_file"])
