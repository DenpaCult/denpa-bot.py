from discord.ext import commands

class test_event(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(self.bot.user.name)

async def setup(bot):
    await bot.add_cog(test_event(bot))
