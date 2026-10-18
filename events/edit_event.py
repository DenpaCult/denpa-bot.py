import logging
import re
from datetime import UTC, datetime
from math import floor

from discord import HTTPException, Member, Message, RawMessageUpdateEvent, TextChannel
from discord.ext import commands

from base.database import db
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
    @commands.guild_only()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        assert self.bot.user is not None
        assert payload.guild_id

        data = payload.data

        # TODO(kajo): ask hoog why this is a concern
        # for distinguishing between discord embed server-side edits
        if data["embeds"]:
            return

        _config = await self.dao.get_guild_cfg(payload.guild_id)

        if _config is None or not _config.enabled:
            return

        if _config.report_channel_id is None:
            self.logger.error(f"Message edit report channel for {payload.guild_id} not set.")
            return

        channel = self.bot.get_channel(payload.channel_id)

        assert type(channel) is TextChannel

        message: Message = await channel.fetch_message(payload.message_id)

        assert type(message.author) is Member

        if message.author.id == self.bot.user.id:
            return

        edited_at = message.edited_at or datetime.now(tz=UTC)
        rule = _config.rule_for((edited_at - message.created_at).total_seconds())

        if rule is None:
            return

        guild = message.guild.name if message.guild else payload.guild_id
        author = message.author
        self.logger.warning(f"[{guild}]: {author.name}'s edit was outside {rule.threshold_s}s window")

        is_exempt = bool({role.id for role in author.roles} & _config.exempt_role_ids)
        self.logger.warning(
            f"[{guild}]: {author.name}'s message will {'NOT ' if is_exempt else ''}be deleted"
        )

        if not is_exempt:
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
