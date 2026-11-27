import logging
import re
from collections import OrderedDict
from math import floor

from discord import (
    Guild,
    HTTPException,
    Member,
    Message,
    NotFound,
    RawMessageUpdateEvent,
    TextChannel,
)
from discord.ext import commands

from base.database import db
from dao.edit_cfg_dao import EditCfgDAO

HANDLED_LIMIT = 1000


class EditEvent(commands.Cog):
    """
    Guards against content being edited into old messages.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dao = EditCfgDAO(db)

        # message id -> edited_timestamp of the last edit handled
        self.handled: OrderedDict[int, str] = OrderedDict()

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        assert self.bot.user is not None

        if payload.guild_id is None:
            return  # DMs

        # Since we are handling on_raw_message_edit, this handler is called for more than just
        # author edits such as:
        # - discord filling in a link preview
        # - message pinning
        # - a thread being started off of this message
        #
        # edited_timestamp is set by Discord and only changes when the author edits the message.
        # This is the only way the content of the message itself can change. What this means is that
        # when edited_timestamp is:
        # - None: the message has never been edited
        # - a known timestamp: we have already handled it
        # - a new timestamp: an author edit we don't know about yet

        edited = payload.data.get("edited_timestamp")
        if edited is None:
            return  # the message hasn't been edited by the author yet

        # NB: nothing between this check and the store below may await.
        # Updates for the same edit are concurrent
        if self.handled.get(payload.message_id) == edited:
            return  # we knew of the author edit and have dealt with it accordingly

        # NB: the store in question
        # at this point, we have established that ;;toromi has no memory of this author edit having occurred
        self.handled[payload.message_id] = edited
        self.handled.move_to_end(payload.message_id)

        if len(self.handled) > HANDLED_LIMIT:
            self.handled.popitem(last=False)  # oldest

        message = payload.message

        if message.author.id == self.bot.user.id:
            return  # we trust the edits ;;toromi makes

        if not may_add_content(payload.cached_message, message):
            return

        _config = await self.dao.get_guild_cfg(payload.guild_id)

        if _config is None or not _config.enabled:
            return

        if _config.report_channel_id is None:
            self.logger.error(f"Edit report channel for {payload.guild_id} not set.")
            return

        # At this point we have determined that content may have been added, and the Edit Window
        # has been properly set up

        edited_at = message.edited_at
        assert edited_at is not None  # edited_timestamp was checked above

        rule = _config.rule_for((edited_at - message.created_at).total_seconds())

        if rule is None:
            return

        guild = message.guild.name if message.guild else payload.guild_id
        author = message.author

        if (
            not isinstance(author, Member)
            and message.webhook_id is None
            and message.guild is not None
        ):
            # Didn't get any member info so lets look them up
            member = await fetch_member(message.guild, author.id)

            if member is None:
                self.logger.info(
                    f"[{guild}]: update to {author.name}'s message ignored, they've left"
                )
                return

            author = member

        if isinstance(author, Member):
            keep = bool({role.id for role in author.roles} & _config.exempt_role_ids)
        elif message.webhook_id is not None:
            keep = False  # anyone with the webhook's token can edit what it sent
        else:
            keep = True  # couldn't look them up: report it and leave it to the mods

        self.logger.warning(
            f"[{guild}]: {author.name}'s edit was outside the {rule.threshold_s}s window, "
            f"message will {'NOT ' if keep else ''}be deleted"
        )

        if not keep:
            try:
                await message.delete()
            except HTTPException:
                self.logger.exception(
                    f"[{guild}]: failed to delete {author.name}'s message"
                )

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


def may_add_content(before: Message | None, after: Message) -> bool:
    """
    returns true when the before/after indicates that content could have been added
    """

    if before is None:
        return True  # not cached, we can't say for sure

    if after.author.bot or after.webhook_id is not None:
        return True  # bots and webhooks can also edit in embeds and components

    if before.content != after.content:
        return True

    # check to see if there were any attachments added
    return not {a.id for a in after.attachments} <= {a.id for a in before.attachments}


async def fetch_member(guild: Guild, user_id: int) -> Member | None:
    """the member with this id, or None if they aren't in the server"""

    try:
        return guild.get_member(user_id) or await guild.fetch_member(user_id)
    except NotFound:
        return None


def sanitize(text: str) -> str:
    return re.sub(r"([\\`$])", r"\\\1", text)


async def setup(bot: commands.Bot):
    await bot.add_cog(EditEvent(bot))
