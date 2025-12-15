from discord import Game
from discord.ext import commands
import logging
logger = logging.getLogger(__name__)

class test_event(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.bot.user.name} is ready to play music.")
        await self.bot.change_presence(activity=Game("Praise be to ;;toromi"))

async def setup(bot):
    await bot.add_cog(test_event(bot))
