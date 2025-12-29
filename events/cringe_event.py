import traceback
import logging

from datetime import timedelta, datetime, timezone
from discord.ext.commands import Bot, Cog
from discord import RawReactionActionEvent, TextChannel, Member
from base.config import Config
from base.database import db
from dao.cringe_dao import CringeDAO
from models.cringe import CringeMessage
from base.utils import cringe_embed

# TODO: DRY. Make ;;wood and ;;cringe reuse a decent amt. of code


class CringeEvent(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.config = Config.read_config()
        self.dao = CringeDAO(db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    # on_reaction_add doesnt get invoked when reacting to older messages before the bot was started
    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        target_emoji: str = self.config["emoji"]["cringe"]
        reacted_emoji = str(payload.emoji)

        if reacted_emoji != target_emoji:
            return

        guild = await guild_name(self.bot, payload)

        msg_ch = await self.bot.fetch_channel(payload.channel_id)
        if not isinstance(msg_ch, TextChannel):
            return

        log_ch = await self.bot.fetch_channel(self.config["cringe"]["channelId"])
        if not isinstance(log_ch, TextChannel):
            self.logger.error(f"{guild}: config.cringe.channelId should be TextChannel")
            return

        message = await msg_ch.fetch_message(payload.message_id)
        if not isinstance(message.author, Member):
            return

        if payload.member is None:
            self.logger.error("invariant: expected payload.member != None")
            return

        if message.author.id == payload.member.id:
            await message.remove_reaction(reacted_emoji, message.author)
            self.logger.info(f"{guild}: {message.author.name} tried muting themselves")
            return

        elapsed = datetime.now(tz=timezone.utc) - message.created_at
        expireTime = self.config["cringe"]["expireTime"] * 60

        if elapsed.seconds >= expireTime:  # created_at returns time in utc
            self.logger.info(
                f"{guild}: reaction to {message.author.name}'s message outside window: {elapsed.seconds}s elapsed'"
            )
            return

        self.logger.info(
            f"{guild}: {payload.member.name} thinks {message.author.name} is cringe"
        )

        already_cringed = self.dao.get_one(CringeMessage.from_message(message))
        if already_cringed:
            return

        cringe_count = list(
            filter(lambda x: str(x.emoji) == target_emoji, message.reactions)
        )[0].count

        if cringe_count >= self.config["cringe"]["threshold"]:
            duration = timedelta(minutes=self.config["cringe"]["timeoutTime"])

            try:
                await message.author.timeout(duration)
            except Exception as _:
                self.logger.error(traceback.format_exc())

            self.dao.add(CringeMessage.from_message(message))
            self.logger.info(
                f"{guild}: timed out {message.author} for {duration.seconds}s"
            )

            await message.reply(
                f"{message.author.name.upper()} WAS MUTED FOR THIS POST",
                mention_author=True,
            )

            await log_ch.send(embeds=cringe_embed(message))


async def setup(bot: Bot):
    await bot.add_cog(CringeEvent(bot))


async def guild_name(bot: Bot, payload: RawReactionActionEvent) -> str:
    if payload.guild_id is not None:
        return f"[{(await bot.fetch_guild(payload.guild_id)).name}]"
    else:
        return str("[NOT GUILD]")
