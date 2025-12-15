from datetime import timedelta, datetime, timezone
import logging
import traceback
from discord import RawReactionActionEvent
from discord.ext.commands import Bot, Cog
from base.config import Config
from dao.wood_dao import WoodDAO
from models.wood import Wood
from base.utils import parse_message_into_embed


class WoodEvent(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.config = Config.read_config()
        self.dao = WoodDAO()

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent): # on_reaction_add doesnt get invoked when reacting to older messages before the bot was started
        """
        TODO: media support
        keeping the try/catch for debugging until its finished
        """
        try:
            wood_emoji = self.config["emoji"]["wood"]
            reaction_emoji = str(payload.emoji)
            if reaction_emoji != wood_emoji:
                return
            
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            
            already_would = self.dao.get_one(Wood.from_message(message))
            if already_would:
                return
            
            wood_count = list(filter(lambda x: str(x.emoji) == wood_emoji, message.reactions))[0].count
            
            if wood_count >= self.config["defaultWoodConfig"]["threshold"]:
                self.dao.add(Wood.from_message(message))
                self.logger.info(f"{message.id} has been wooded")

                _embeds = parse_message_into_embed(message, 0xe8b693, (f"{message.author.name} | 🦈 tbh", message.author.display_avatar.url), f"ID: {message.id}")

                wood_chan = await self.bot.fetch_channel(self.config["defaultWoodConfig"]["channelId"])
                await wood_chan.send(embeds=_embeds)
        except Exception as e:
            self.logger.error(traceback.format_exc())
            
            



async def setup(bot: Bot):
    await bot.add_cog(WoodEvent(bot))
