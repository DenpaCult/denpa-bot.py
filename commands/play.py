import json
import logging
from operator import is_
import re
from discord.ext import commands

from models.music_player import YOUTUBE_PLAYLIST_REGEX, MusicPlayerSingleton
from base.config import Config

class PlayCommand(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.logger = logging.getLogger(__name__)
        self.config = Config.read_config()

    @commands.command()
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

        args = " ".join(args)

        music_player = MusicPlayerSingleton.get_guild_instance(ctx.guild, ctx.bot)
        await music_player.connect(ctx.author.voice.channel)

        
        is_youtube_playlist = bool(re.match(YOUTUBE_PLAYLIST_REGEX, args))
        if is_youtube_playlist:
            await music_player.add_playlist(args)
        else:
            await music_player.add_song(args)
        self.logger.info(music_player.queue)



async def setup(bot):
    await bot.add_cog(PlayCommand(bot))
