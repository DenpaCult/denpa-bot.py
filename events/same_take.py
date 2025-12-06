from discord.ext import commands
import discord
from config.config import config
from logger.logger import logger


class same_take(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.logger = logger.instance()
        self.config = config.read_config()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        sametakes: dict = self.config["sametakes"]
        for k,v in sametakes.items():
            if k in message.content:
                await message.add_reaction(v)
                # self.logger.log(f'reacted to {message}')

async def setup(bot):
    await bot.add_cog(same_take(bot))
