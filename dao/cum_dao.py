"""
CREATE TABLE cum (
    cummer_id INTEGER NOT NULL,
    cummed_on_id INTEGER NOT NULL
);
"""

import logging
from dao.dao import BaseDAO
from models.cum import Cumshot

# FIXME: rename cummed_on_id to cummee_id?
# FIXME: sender and receiver might be preferred as they're more obvious


class CumDAO(BaseDAO):
    def __init__(self, db):
        BaseDAO.__init__(self, db)
        self.logger = logging.getLogger(__name__)

    def add(self, model: Cumshot):
        self.write(
            "INSERT INTO cum (cummer_id, cummed_on_id) VALUES(?, ?);",
            (model.cummer_id, model.cummee_id),
        )

    def remove(self, model: Cumshot):
        self.write(
            "DELETE FROM cum WHERE cummer_id=? AND cummed_on_id=?",
            (
                model.cummer_id,
                model.cummee_id,
            ),
        )

    def get_all(self) -> list[Cumshot]:
        return list(
            map(lambda x: Cumshot(x[0], x[1]), self.fetch_all("SELECT * FROM cum;"))
        )

    def get_cummed_count(
        self, user_id: int
    ) -> int:  # How many times the user has cummed
        return len(self.fetch_all("SELECT * FROM cum WHERE cummer_id=?", (user_id,)))

    def get_cummed_on_count(
        self, user_id: int
    ) -> int:  # How many times the user has been cummed on
        return len(self.fetch_all("SELECT * FROM cum WHERE cummed_on_id=?", (user_id,)))

    def get_most_cummed_on_user(
        self, user_id
    ) -> (
        int | None
    ):  # person the user has cummed on the most, returns user_id the name should be fetched later
        data = self.fetch_all(
            """
                               SELECT cummed_on_id
                               FROM cum
                               WHERE cummer_id == ?
                               GROUP BY cummed_on_id
                               ORDER BY COUNT(cummed_on_id) DESC
                               LIMIT 1;
                              """,
            (user_id,),
        )
        data = data[0][0] if data else None
        return data

    def get_most_cummer_on_you(
        self, user_id
    ) -> (
        int | None
    ):  # person that has cummed on the user the most, returns user_id the name should be fetched later
        data = self.fetch_all(
            """
                               SELECT cummer_id
                               FROM cum
                               WHERE cummed_on_id == ?
                               GROUP BY cummer_id
                               ORDER BY COUNT(cummer_id) DESC
                               LIMIT 1;
                              """,
            (user_id,),
        )
        data = data[0][0] if data else None
        return data

    # is this gonna be required
    # def get_cummed_on_user_count(self, user_id: int, member_id: int): # How many times the user has cummed on a specific member
