import logging

from discord import RawReactionActionEvent, TextChannel, Member
from discord.ext.commands import Bot, Cog
from base.config import Config
from base.database import db
from dao.wood_dao import WoodDAO
from events.cringe_event import guild_name
from models.wood import WoodMessage
from base.utils import msg_embed


class WoodEvent(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.dao = WoodDAO(db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    # we dont use on_reaction_add because it doesnt get invoked when reacting to older messages before the bot was started
    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        assert payload.guild_id

        cfg = await Config.load(payload.guild_id)

        target_emoji = cfg.emoji.wood
        reaction_emoji = str(payload.emoji)

        if reaction_emoji != target_emoji:
            return

        guild = await guild_name(self.bot, payload)

        msg_ch = await self.bot.fetch_channel(payload.channel_id)
        assert isinstance(msg_ch, TextChannel)

        log_ch = await self.bot.fetch_channel(cfg.wood.channelId)
        assert isinstance(log_ch, TextChannel)

        message = await msg_ch.fetch_message(payload.message_id)
        assert isinstance(message.author, Member)

        already_would = self.dao.get_one(WoodMessage.from_message(message))
        if already_would:
            return

        wood_count = list(
            filter(lambda x: str(x.emoji) == target_emoji, message.reactions)
        )[0].count

        if wood_count >= cfg.wood.threshold:
            self.dao.add(WoodMessage.from_message(message))
            self.logger.info(
                f"{guild}: {message.id} by {message.author} has been added to woodboard"
            )

            await log_ch.send(
                embeds=msg_embed(message, f"{message.author.name} | 🦈 tbh")
            )


async def setup(bot: Bot):
    await bot.add_cog(WoodEvent(bot))
