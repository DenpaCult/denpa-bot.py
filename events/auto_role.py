from discord.ext import commands
import discord
from config.config import config
from logger.logger import logger


class auto_role(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.logger = logger.instance()
        self.config = config.read_config()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        roles = await member.guild.fetch_roles()
        new_role =  list(filter(lambda x: x.name == self.config["defaultrole"], roles))[0]
        await member.add_roles(new_role)
        self.logger.log(f'added role {new_role} to {member.name}')

async def setup(bot):
    await bot.add_cog(auto_role(bot))
