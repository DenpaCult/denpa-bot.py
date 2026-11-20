import logging
import re
from datetime import UTC, datetime
from math import floor

from discord import HTTPException, Member, Message, RawMessageUpdateEvent, TextChannel
from discord.ext import commands

from base.database import db
from base.utils import message_channel
from dao.edit_cfg_dao import EditCfgDAO


class EditEvent(commands.Cog):
    """
    When a message is edited after the largest configured rule threshold has passed, it is
    deleted (unless the message author is exempt by role) and the event is reported. 
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dao = EditCfgDAO(db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        assert self.bot.user is not None

        if payload.guild_id is None:
            return  # DMs

        # FIXME(kajo): The idea is that discord sends an update when it fills in a link preview,
        # however since this isn't an edit by the author, the event won't have an edited_timestamp.
        #
        # We prefer this over checking for embeds since that might rule out any message that has a
        # link in it which would be a problem!
        if payload.data.get("edited_timestamp") is None:
            return

        _config = await self.dao.get_guild_cfg(payload.guild_id)

        if _config is None or not _config.enabled:
            return

        if _config.report_channel_id is None:
            self.logger.error(f"Message edit report channel for {payload.guild_id} not set.")
            return

        channel = await message_channel(self.bot, payload.channel_id)
        if channel is None:
            return

        message: Message = await channel.fetch_message(payload.message_id)

        if message.author.id == self.bot.user.id:
            return

        edited_at = message.edited_at or datetime.now(tz=UTC)
        rule = _config.rule_for((edited_at - message.created_at).total_seconds())

        if rule is None:
            return

        guild = message.guild.name if message.guild else payload.guild_id
        author = message.author

        # Handle webhooks and users who have left (reported but not deleted)
        if isinstance(author, Member):
            keep = bool({role.id for role in author.roles} & _config.exempt_role_ids)
        else:
            keep = True

        self.logger.warning(
            f"[{guild}]: {author.name}'s edit was outside the {rule.threshold_s}s window, "
            f"message will {'NOT ' if keep else ''}be deleted"
        )

        if not keep:
            try:
                await message.delete()
            except HTTPException:
                self.logger.exception(f"[{guild}]: failed to delete {author.name}'s message")

        report_channel = self.bot.get_channel(_config.report_channel_id)
        assert type(report_channel) is TextChannel

        ping = " ".join(f"<@&{role_id}>" for role_id in rule.role_ids)
        before = payload.cached_message.content if payload.cached_message else None

        report = (
            f"{ping} <@{author.id}> ({author.name}) edited [a message]({message.jump_url}) "
            f"that was posted <t:{floor(message.created_at.timestamp())}:R>.\n"
        )
        if before:
            report += f"### Before\n```\n{sanitize(before)}\n```\n"
        report += f"### After\n```\n{sanitize(message.content)}\n```"

        await report_channel.send(report.strip())


def sanitize(text: str) -> str:
    return re.sub(r"([\\`$])", r"\\\1", text)


async def setup(bot: commands.Bot):
    await bot.add_cog(EditEvent(bot))
