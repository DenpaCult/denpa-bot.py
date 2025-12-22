import json
import logging
import re
import subprocess
import discord
from discord.ext import commands
from discord.voice_client import VoiceClient

from base import utils
from models.music_player import MusicPlayerSingleton
from base.config import Config

YOUTUBE_REGEX = "^https://(?:www.)?youtube.com/.+$"
URL_REGEX = utils.URL_REGEX

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

        music_player = MusicPlayerSingleton.get_guild_instance(ctx.guild, ctx.bot)
        await music_player.connect(ctx.author.voice.channel)
        await music_player.add_song(" ".join(args))
        self.logger.info(music_player.queue)



async def setup(bot):
    await bot.add_cog(PlayCommand(bot))
