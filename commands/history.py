from discord.ext import commands

from models.music_player import MusicPlayerSingleton

class History(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["hist"])
    @commands.guild_only()
    async def history(self, ctx):
        music_player = MusicPlayerSingleton.get_guild_instance(ctx.guild, ctx.bot)
        await ctx.send(embeds=[await music_player.history()])

async def setup(bot):
    await bot.add_cog(History(bot))
