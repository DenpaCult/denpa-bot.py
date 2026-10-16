import logging

from base.database import Database
from dao.dao import BaseDAO
from models.edit_cfg import EditCfg


class EditCfgDAO(BaseDAO):
    def __init__(self, db: Database):
        BaseDAO.__init__(self, db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    async def add(self, model: EditCfg):
        await self.write(
            "INSERT INTO editcfg (guild_id, time_limit_h, report_channel_id, mention_list, ignore_roles) VALUES(?, ?, ?, ?, ?);",
            (
                model.guild_id,
                model.time_limit_h,
                model.report_channel_id,
                ", ".join(model.mention_list),
                ", ".join(model.ignore_roles)
            ),
        )

    async def remove(self, model: EditCfg):
        await self.write("DELETE FROM editcfg WHERE id=?", (model.id,))

    async def exists(self, model: EditCfg) -> bool:
        return bool(
            await self.fetch_one(
                "SELECT * FROM editcfg WHERE guild_id=?",
                (model.guild_id),
            )
        )

    async def update_guild_cfg(self, model: EditCfg):
        # exists?
        if not await self.exists(model):
            await self.add(model)
            return

        await self.write(
                "UPDATE editcfg SET time_limit_h=?, report_channel_id=?, mention_list=?, ignore_roles=? where guild_id=?",
                (
                    model.time_limit_h,
                    model.report_channel_id,
                    ", ".join(model.mention_list),
                    ", ".join(model.ignore_roles),
                    model.guild_id
                    ),
                )


    async def get_guild_cfg(self, guild_id: int) -> EditCfg:
        return EditCfg.from_database(await self.fetch_one(
            "SELECT * FROM editcfg WHERE guild_id=?",
            (guild_id,),
        ))

