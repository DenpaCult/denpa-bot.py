from discord.ext import commands

class test_command(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong!")

async def setup(bot):
    await bot.add_cog(test_command(bot))
