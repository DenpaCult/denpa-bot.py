import logging

from discord import RawReactionActionEvent, TextChannel
from discord.ext.commands import Bot, Cog

from base.config import Config
from base.database import db
from base.utils import message_channel, msg_embed
from dao.wood_dao import WoodDAO
from models.wood import WoodMessage


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
        if payload.guild_id is None:
            return  # DMs

        cfg = await Config.load(payload.guild_id)

        target_emoji = cfg.emoji.wood
        reaction_emoji = str(payload.emoji)

        if reaction_emoji != target_emoji:
            return  # not a wood event

        if cfg.wood.channel_id is None:
            self.logger.warning(
                f"[{payload.guild_id}]: wood reaction ignored, no woodboard channel. "
                "an admin can run `;;config set wood channel_id <channel_id>`"
            )
            return

        if payload.channel_id == cfg.wood.channel_id:
            return  # reposts on the woodboard don't count

        msg_ch = await message_channel(self.bot, payload.channel_id)
        if msg_ch is None:
            return

        log_ch = await self.bot.fetch_channel(cfg.wood.channel_id)
        assert isinstance(log_ch, TextChannel)

        message = await msg_ch.fetch_message(payload.message_id)

        wood_count = next(
            filter(lambda x: str(x.emoji) == target_emoji, message.reactions)
        ).count

        if wood_count >= cfg.wood.threshold:
            if not await self.dao.add(WoodMessage.from_message(message)):
                return

            name = f"[{message.guild.name}]" if message.guild else "[NOT GUILD]"
            self.logger.info(
                f"{name}: {message.id} by {message.author} has been added to woodboard"
            )

            await log_ch.send(
                embeds=msg_embed(message, f"{message.author.name} | 🦈 tbh")
            )


async def setup(bot: Bot):
    await bot.add_cog(WoodEvent(bot))
