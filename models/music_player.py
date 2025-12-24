from asyncio import Queue
import json
import logging
import re
import subprocess
import asyncio

from discord import AudioSource, Enum, Guild, VoiceChannel, VoiceClient, VoiceProtocol, voice_client
import discord
from discord.ext.commands import Bot

from base.utils import URL_REGEX

YOUTUBE_REGEX = "^https://(?:www.)?youtu(be.com|.be)/.+$"
YOUTUBE_PLAYLIST_REGEX = "^https://(?:www.)?youtu(be.com|.be)/.+list=.+$"

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
        self.queue: asyncio.Queue[str] = Queue()
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

        if self.voice_client.is_playing:
            await self.queue.put(query)
            return

        source = await self.get_source(query)

        await self.play_source(self.on_song_ended, source)

    async def add_playlist(self, query: str):
        if not isinstance(self.voice_client, VoiceClient):
             # if not connected to vc
             self.logger.warning(f"add_playlist used before connecting to voice channel")
             return
        urls = await self.yt_dlp_playlist(query)

        self.logger.info(urls)

        source = await self.get_source(urls[0])
        await self.play_source(self.on_song_ended, source)
        for url in urls[1:]:
            await self.queue.put(url)




    def on_song_ended(self, error):
        # this function runs whenever a song finishes either by ending or error
        if not self.queue.empty():
            asyncio.run_coroutine_threadsafe( self.play_queue(self.on_song_ended), self.loop)


    async def play_source(self, after, source: AudioSource):
        # TODO: return embed to reply when play command is used
        if isinstance(self.voice_client, VoiceClient):
            self.logger.info("playing")
            self.voice_client.play(source, after=after)

    async def play_queue(self, after):
        # TODO: return embed to reply when play command is used
        if isinstance(self.voice_client, VoiceClient):
            self.logger.info("playing next queue song")
            query = await self.queue.get()
            source = await self.get_source(query)
            self.voice_client.play(source, after=after)


    async def get_source(self, query: str) -> AudioSource:
        # TODO: correct handeling of opus and non opus sources
        classified = self.classify_query(query)
        before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        match(classified):
            case SourceEnum.YOUTUBE_SOURCE:
                return discord.FFmpegOpusAudio((await self.yt_dlp_url(query)), before_options=before_options)
            case SourceEnum.URL_SOURCE:
                return discord.FFmpegPCMAudio(query, before_options=before_options)
            case SourceEnum.UNKNOWN|_:
                self.logger.error("query is unknown")
                raise Exception("query is unknown")


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
            raise Exception("yt-dlp not found")

        result = subprocess.run(["yt-dlp" ,"--dump-single-json", "--no-warnings", "--prefer-free-formats", "--skip-download", "--simulate", "--format", "ba/ba", query], capture_output=True, text=True).stdout

        _json: dict = json.loads(result)

        self.logger.info(_json["url"])

        return _json["url"]

    async def yt_dlp_playlist(self, query: str) -> list[str]:
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            self.logger.error("yt-dlp executable was not found")
            raise Exception("yt-dlp not found")

        
        result = subprocess.run(["yt-dlp" , "--flat-playlist", "--dump-single-json", "--no-warnings", "--prefer-free-formats", "--skip-download", "--simulate", "--format", "ba/ba", query], capture_output=True, text=True).stdout

        _json: dict = json.loads(result)

        return list(map(lambda x: x["url"], _json["entries"]))



