import logging
from discord.ext import commands

from models.music_player import MusicPlayerSingleton
from base.config import Config

class LeaveCommand(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.logger = logging.getLogger(__name__)
        self.config = Config.read_config()

    @commands.command()
    @commands.guild_only()
    async def leave(self, ctx: commands.Context):
        """
        leave vc
        """
        if not ctx.guild:
            return

        music_player = MusicPlayerSingleton.get_guild_instance(ctx.guild, ctx.bot)

        await ctx.send(embed=await music_player.disconnect())




async def setup(bot):
    await bot.add_cog(LeaveCommand(bot))
