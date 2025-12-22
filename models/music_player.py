import json
import logging
import re
import subprocess
from typing import Deque
import asyncio

from discord import AudioSource, Enum, Guild, VoiceChannel, VoiceClient, VoiceProtocol, voice_client
import discord
from discord.ext.commands import Bot

from base.utils import URL_REGEX

YOUTUBE_REGEX = "^https://(?:www.)?youtube.com/.+$"

class SourceEnum(Enum):
    UNKNOWN = -1
    YOUTUBE_SOURCE = 0
    URL_SOURCE = 1
    # add more later

class MusicPlayerSingleton:

    _instances: dict[int, "MusicPlayerSingleton"] = {}

    @classmethod
    def get_guild_instance(cls, guild: Guild, bot: Bot|None = None) -> "MusicPlayerSingleton":
        if guild.id not in cls._instances.keys():
            cls._instances[guild.id] = cls(guild, bot.loop)
        
        return cls._instances[guild.id]

    def __init__(self, guild: Guild, loop):
        self.queue: Deque[AudioSource] = Deque()
        self.voice_client: VoiceClient | VoiceProtocol | None = guild.voice_client
        self.loop = loop
        self.guild = guild
        self.logger = logging.getLogger(__name__)
        

    async def connect(self, channel: VoiceChannel):
        if not self.voice_client:
            self.logger.info(self.voice_client)
            await channel.connect()
            self.voice_client = self.guild.voice_client

    async def disconnect(self):
        if isinstance(self.voice_client, VoiceClient|VoiceProtocol):
            await self.voice_client.disconnect()

    async def add_song(self, query: str):
        if not isinstance(self.voice_client, VoiceClient):
             # if not connected to vc
             self.logger.warning(f"add_song used before connecting to voice channel")
             return

        source = await self.get_source(query)

        # if queue is empty play immediately
        self.logger.info("line 55")
        await self.play(source, after=self.on_song_ended)

    def on_song_ended(self, error):
        # this function runs whenever a song finishes either by ending or error
        if self.queue:
            asyncio.run_coroutine_threadsafe( self.play(self.queue.pop(), after=self.on_song_ended), self.loop)


    async def play(self, source: AudioSource, after):
        if isinstance(self.voice_client, VoiceClient):
            if not self.voice_client.is_playing():
                self.logger.info("playing")
                self.voice_client.play(source, after=after)
            else:
                self.queue.append(source)
                self.logger.error(f"tried to play song while another one was playing")


    async def get_source(self, query: str) -> AudioSource:
        # TODO: add ffmpeh reconnect options
        classified = self.classify_query(query)
        match(classified):
            case SourceEnum.UNKNOWN:
                self.logger.error("query is unknown")
                raise Exception("query is unknown")
            case SourceEnum.YOUTUBE_SOURCE:
                return discord.FFmpegOpusAudio((await self.yt_dlp_url(query)))
            case SourceEnum.URL_SOURCE:
                return discord.FFmpegPCMAudio(query)


    def classify_query(self, query: str) -> SourceEnum:
        # return query_type
        if re.match(YOUTUBE_REGEX, query):
            return SourceEnum.YOUTUBE_SOURCE
        elif re.match(URL_REGEX, query):
            return SourceEnum.URL_SOURCE
        else:
            return SourceEnum.UNKNOWN

    async def yt_dlp_url(self, query: str) -> str:
        # check if exists
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            self.logger.error("yt-dlp executable was not found")
            # TODO: raise some exception instead
            raise Exception("yt-dlp not found")

        # TODO: handle playlists
        result = subprocess.run(["yt-dlp" ,"--dump-single-json", "--no-warnings", "--prefer-free-formats", "--skip-download", "--simulate", "--format", "ba/ba", query], capture_output=True, text=True).stdout

        return json.loads(result)["url"]




