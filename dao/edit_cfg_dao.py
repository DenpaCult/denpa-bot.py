import logging

from base.database import Database
from dao.dao import BaseDAO
from models.edit_cfg import EditCfg, EditRule


class EditCfgDAO(BaseDAO):
    def __init__(self, db: Database):
        BaseDAO.__init__(self, db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    async def set_config(self, guild_id: int, enabled: bool, report_channel_id: int | None):
        await self.write(
            """
            INSERT INTO edit_config (guild_id, enabled, report_channel_id) VALUES (?, ?, ?)
            ON CONFLICT (guild_id) DO UPDATE SET
                enabled = excluded.enabled,
                report_channel_id = excluded.report_channel_id;
            """,
            (guild_id, int(enabled), report_channel_id),
        )

    async def add_rule(self, guild_id: int, threshold_s: int, role_id: int) -> bool:
        """returns False if the role was already pinged at this threshold"""
        cur = await self.write(
            "INSERT OR IGNORE INTO edit_rule (guild_id, threshold_s, role_id) VALUES (?, ?, ?);",
            (guild_id, threshold_s, role_id),
        )

        return cur.rowcount == 1

    async def remove_rule(self, guild_id: int, threshold_s: int):
        await self.write(
            "DELETE FROM edit_rule WHERE guild_id = ? AND threshold_s = ?;",
            (guild_id, threshold_s),
        )

    async def add_exempt_role(self, guild_id: int, role_id: int) -> bool:
        """returns False if the role was already exempt"""
        cur = await self.write(
            "INSERT OR IGNORE INTO edit_exempt_role (guild_id, role_id) VALUES (?, ?);",
            (guild_id, role_id),
        )

        return cur.rowcount == 1

    async def remove_exempt_role(self, guild_id: int, role_id: int):
        await self.write(
            "DELETE FROM edit_exempt_role WHERE guild_id = ? AND role_id = ?;",
            (guild_id, role_id),
        )

    async def get_guild_cfg(self, guild_id: int) -> EditCfg | None:
        """None if edit window monitoring was never configured for this server"""
        row = await self.fetch_one(
            "SELECT enabled, report_channel_id FROM edit_config WHERE guild_id = ?;",
            (guild_id,),
        )
        if row is None:
            return None

        enabled, report_channel_id = row

        rules: dict[int, EditRule] = {}
        for threshold_s, role_id in await self.fetch_all(
            "SELECT threshold_s, role_id FROM edit_rule WHERE guild_id = ? ORDER BY threshold_s;",
            (guild_id,),
        ):
            rules.setdefault(threshold_s, EditRule(threshold_s)).role_ids.append(role_id)

        exempt = await self.fetch_all(
            "SELECT role_id FROM edit_exempt_role WHERE guild_id = ?;", (guild_id,)
        )

        return EditCfg(
            guild_id=guild_id,
            enabled=bool(enabled),
            report_channel_id=report_channel_id,
            rules=list(rules.values()),
            exempt_role_ids={role_id for (role_id,) in exempt},
        )
