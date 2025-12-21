from datetime import timedelta, datetime, timezone
import logging
import traceback
from discord.ext.commands import Bot, Cog
from discord import RawReactionActionEvent
from base.config import Config
from dao.cringe_dao import CringeDAO
from models.cringe import Cringe
from base.utils import parse_message_into_embed


class CringeEvent(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.config = Config.read_config()
        self.dao = CringeDAO()

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent): # on_reaction_add doesnt get invoked when reacting to older messages before the bot was started
        """
        TODO: media support
        keeping the try/catch for debugging until its finished
        """
        try:
            cringe_emoji = self.config["emoji"]["cringe"]
            reaction_emoji = str(payload.emoji)
            if reaction_emoji != cringe_emoji:
                return
            
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            if message.author.id == payload.member.id:
                await message.remove_reaction(reaction_emoji, message.author) # same user can't react
                return
            
            
            if (datetime.now(tz=timezone.utc) - message.created_at).seconds > self.config["defaultCringeConfig"]["expireTime"] * 60: # created_at returns time in utc
                return 
            
            already_cringed = self.dao.get_one(Cringe.from_message(message))
            if already_cringed:
                return
            
            cringe_count = list(filter(lambda x: str(x.emoji) == cringe_emoji, message.reactions))[0].count
            
            if cringe_count >= self.config["Cringe"]["threshold"]:
                await message.author.timeout(timedelta(minutes=cringe_config["timeoutTime"]))
                self.dao.add(Cringe.from_message(message))
                self.logger.info(f"{message.author} has been timed out for {self.config['defaultCringeConfig']['timeoutTime']} minutes")

                _embeds = parse_message_into_embed(message, 0xe8b693, (f"{message.author.name} posted cringe", message.author.display_avatar.url), f"ID: {message.id}")

                await channel.send(embeds=_embeds)
        except Exception as e:
            self.logger.error(traceback.format_exc())
            
            



async def setup(bot: Bot):
    await bot.add_cog(CringeEvent(bot))
