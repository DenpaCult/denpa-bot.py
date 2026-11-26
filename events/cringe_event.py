import logging
import traceback
from datetime import UTC, datetime, timedelta

from discord import (
    Forbidden,
    HTTPException,
    Member,
    RawReactionActionEvent,
    TextChannel,
)
from discord.ext.commands import Bot, Cog

from base.config import Config
from base.database import db
from base.utils import message_channel, msg_embed
from dao.cringe_dao import CringeDAO
from models.cringe import CringeMessage

# TODO: DRY. Make ;;wood and ;;cringe reuse a decent amt. of code


class CringeEvent(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.dao = CringeDAO(db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    # NB: on_reaction_add doesnt get invoked when reacting to older messages before the bot was started
    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if payload.guild_id is None:
            return  # DMs

        cfg = await Config.load(payload.guild_id)

        target_emoji: str = cfg.emoji.cringe
        reacted_emoji = str(payload.emoji)

        if reacted_emoji != target_emoji:
            return

        if cfg.cringe.channel_id is None:
            self.logger.warning(
                f"[{payload.guild_id}]: cringe reaction ignored, no cringe channel. "
                "an admin can run `;;config set cringe channel_id <channel_id>`"
            )
            return

        if payload.channel_id == cfg.cringe.channel_id:
            return  # reposts in the cringe channel don't count

        msg_ch = await message_channel(self.bot, payload.channel_id)
        if msg_ch is None:
            return

        log_ch = await self.bot.fetch_channel(cfg.cringe.channel_id)
        assert isinstance(log_ch, TextChannel)

        message = await msg_ch.fetch_message(payload.message_id)
        guild = f"[{message.guild.name}]" if message.guild else "[NOT GUILD]"

        if not isinstance(message.author, Member):
            # webhooks and users who already left can't be timed out
            self.logger.info(
                f"{guild}: cringe reaction on {message.author.name}'s message ignored, not a member"
            )
            return

        assert payload.member is not None

        if message.author.id == payload.member.id:
            await message.remove_reaction(reacted_emoji, message.author)
            self.logger.info(f"{guild}: {message.author.name} tried muting themselves")
            return

        elapsed_s = (datetime.now(tz=UTC) - message.created_at).total_seconds()

        if elapsed_s >= cfg.cringe.expire_time:
            self.logger.info(
                f"{guild}: reaction to {message.author.name}'s message outside window: {elapsed_s:.0f}s elapsed"
            )
            return

        self.logger.info(
            f"{guild}: {payload.member.name} thinks {message.author.name} is cringe"
        )

        cringe_count = next(
            filter(lambda x: str(x.emoji) == target_emoji, message.reactions)
        ).count

        if cringe_count >= cfg.cringe.threshold:
            # counted before add() so the current message isn't included
            offences = await self.dao.count(payload.guild_id, message.author.id)

            if not await self.dao.add(CringeMessage.from_message(message)):
                return

            base = timedelta(seconds=cfg.cringe.timeout_time)
            multiplier = max((offences + 1) - 5, 0)  # current past 5
            total = base + timedelta(seconds=2 * multiplier)

            try:
                await message.author.timeout(total)
            except (Forbidden, HTTPException, TypeError, ValueError):
                # e.g. admins, or anyone above the bot's top role.
                self.logger.error(
                    f"{guild}: failed to time out {message.author}\n{traceback.format_exc()}"
                )
            else:
                self.logger.info(
                    f"{guild}: offence #{offences + 1}. timed out {message.author} for {total.total_seconds():.0f}s"
                )
                await message.reply(
                    f"{message.author.name.upper()} WAS MUTED FOR THIS POST",
                    mention_author=True,
                )

            await log_ch.send(
                embeds=await msg_embed(
                    message, f"{message.author.name} posted cringe", allow_nsfw=True
                )
            )


async def setup(bot: Bot):
    await bot.add_cog(CringeEvent(bot))
