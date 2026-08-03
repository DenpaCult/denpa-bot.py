from datetime import UTC, datetime
import logging
from math import floor
from sqlite3 import OperationalError
from discord import Member, Message, RawMessageUpdateEvent, TextChannel
from discord.ext import commands

from dao.edit_cfg_dao import EditCfgDAO
from base.database import db


class EditEvent(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dao = EditCfgDAO(db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        assert self.bot.user is not None
        assert payload.guild_id

        _config = None
        try: 
            _config = await self.dao.get_guild_cfg(payload.guild_id)
        except OperationalError as _:
            self.logger.error("Message edit listenr db error, editcfg table/row might not exist in the database")
            return

        if not _config:
            self.logger.error(f"Message edit config for {payload.guild_id} not found.")

        channel = self.bot.get_channel(payload.channel_id)

        assert type(channel) is TextChannel

        message: Message = await channel.fetch_message(payload.message_id)

        assert type(message.author) is Member

        if set([role.id for role in message.author.roles]).intersection(_config.ignore_roles):
            return


        if (datetime.now(tz=UTC) - message.created_at).total_seconds() * 3600 > _config.time_limit_h:
            report_channel = self.bot.get_channel(_config.report_channel_id)
            assert type(report_channel) is TextChannel
            await report_channel.send(
                    f"{[f"<@{i}>" for i in _config.mention_list] if _config.mention_list else ""}\n{message.author.name} edited a [message]({message.jump_url}) that was posted <t:{floor(message.created_at.timestamp())}:R>.\n{f"# Before:\n```{payload.cached_message.content}```\n" if payload.cached_message else "\n"}# After:\n```{message.content}```"
            )



async def setup(bot: commands.Bot):
    await bot.add_cog(EditEvent(bot))
