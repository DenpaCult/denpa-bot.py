import logging
import re
from discord import Embed, Member
from discord.ext import commands

from models.music_player import YOUTUBE_PLAYLIST_REGEX, MusicPlayerSingleton
from base.config import Config

class PlayCommand(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.logger = logging.getLogger(__name__)
        self.config = Config.read_config()

    @commands.command(aliases=["p"])
    @commands.guild_only()
    async def play(self, ctx: commands.Context, *args):
        """
        add a song to the queue
        if queue is empty, play immediately
        TODO: figure out how we are going to globally store the queue and other stuff across comands
              playlist support
              check if queue is empty or not
        """
        if not ctx.guild:
            return

        if not ctx.author.voice: # stupid python warnings if guild_only is on the author is a member not a user
            await ctx.send(embed=Embed(color=0xffffff, title="You are not connected to a voice channel"))
            return

        args = " ".join(args)

        music_player = MusicPlayerSingleton.get_guild_instance(ctx.guild, ctx.bot)
        is_connected = await music_player.is_connected()
        if not is_connected:
            await music_player.connect(ctx.author.voice.channel)

        
        is_youtube_playlist = bool(re.match(YOUTUBE_PLAYLIST_REGEX, args))
        if is_youtube_playlist:
            await music_player.add_playlist(args, ctx.author.name)
        else:
            await music_player.add_song(args, ctx.author.name)
        self.logger.info(music_player.queue)



async def setup(bot):
    await bot.add_cog(PlayCommand(bot))
