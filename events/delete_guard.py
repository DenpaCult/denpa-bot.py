import traceback
from discord import Message
from discord.ext import commands
import logging

from base import utils
from base.config import Config
from dao.deleteguard_dao import DeleteGuardDAO
from models.delete_guard import DeleteGuard

class deleteguard_event(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.logger = logging.getLogger(__name__)
        self.dao = DeleteGuardDAO()
        self.config = Config.read_config()
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: Message): 
      try:  
        if not self.dao.exists(DeleteGuard.from_user(message.author)):
            return

        _embed = utils.parse_message_into_embed(message, 
                                                color=0xecdca8,
                                                author=(message.author.name,message.author.display_avatar.url),
                                                footer=f"ID: {message.id}",
                                                content_override=True,
                                                extra_fields=[
                                                    ("Deleted Message", message.content, False),
                                                    ]
                                                )

        # channel = await self.bot.fetch_channel(self.config["DeleteGuard"]["channelId"]) # send to deleteguard channel
        # await channel.send(embeds=_embed)
        await message.channel.send(embeds=_embed)
      except Exception as e:
          self.logger.error(traceback.format_exc())

    @commands.Cog.listener()
    async def on_message_edit(self, before: Message, _: Message):
        if not self.dao.exists(DeleteGuard.from_user(before.author)):
            return

        _embed = utils.parse_message_into_embed(before, 
                                                color=0xecdca8,
                                                author=(before.author.name,before.author.display_avatar.url),
                                                footer=f"ID: {before.id}",
                                                content_override=True,
                                                extra_fields=[
                                                    ("Old Message Content", before.content, False),
                                                    ]
                                                )

        channel = await self.bot.fetch_channel(self.config["DeleteGuard"]["channelId"]) # send to deleteguard channel
        if not channel:
            self.logger.error("Error in fetching from the discord API")

        await channel.send(embeds=_embed) # send to deleteguard channel
        






async def setup(bot):
    await bot.add_cog(deleteguard_event(bot))
