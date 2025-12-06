from discord.ext import commands
from dao.blacklist_dao import BlackListDao
from models.blacklist import BlackList

class role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['broadcast', 'syntonize', 'roles', 'role'])
    async def Role(self, ctx):
        dao = BlackListDao()
        bl = BlackList("test", 1)
        dao.newBlackList(bl)


async def setup(bot):
    await bot.add_cog(role(bot))

