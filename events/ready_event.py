import logging
from discord import Game
from discord.ext import commands


class ReadyEvent(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @commands.Cog.listener()
    async def on_ready(self):
        assert self.bot.user is not None

        self.logger.info(f"{self.bot.user.name} is ready to play music.")
        await self.bot.change_presence(activity=Game("Praise be to ;;toromi"))


async def setup(bot: commands.Bot):
    await bot.add_cog(ReadyEvent(bot))
