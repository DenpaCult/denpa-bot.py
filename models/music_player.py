import json
import logging
import re
import subprocess
import asyncio

from discord import AudioSource, Embed, Enum, FFmpegOpusAudio, Guild, VoiceChannel, VoiceClient, VoiceProtocol
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
        self.queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue() # title and url
        self.hist: list[tuple[str, str]] = [] # contains the current playing song to get the last song you have to get the n-2th element
        self.voice_client: VoiceClient | VoiceProtocol | None = guild.voice_client
        self.loop = loop
        self.guild = guild
        self.logger = logging.getLogger(__name__)
        self.lock = asyncio.Lock()
        

    async def connect(self, channel: VoiceChannel):
        if not self.voice_client:
            self.logger.info(self.voice_client)
            await channel.connect()
            self.voice_client = self.guild.voice_client

    async def disconnect(self):
        if isinstance(self.voice_client, (VoiceClient, VoiceProtocol)):
            await self.voice_client.disconnect()

    async def add_song(self, query: str):
        """
        play song immediatly if not playing anythong
        add to queue otherwise
        this is the main startpoint that should be called outside
        the bot should be connected to a voice channel for this to work
        """
        if not isinstance(self.voice_client, VoiceClient):
             # if not connected to vc
             self.logger.warning(f"add_song used before connecting to voice channel")
             return

        title = url = ""
        match(self.classify_query(query)):
            case SourceEnum.YOUTUBE_SOURCE:
                title, url = await self.yt_dlp_url(query, "--skip-download")
            case SourceEnum.URL_SOURCE:
                title = url = query


        if self.voice_client.is_playing():
            await self.queue.put((title, url))
            return 

        source_title_url = await self.get_source(query)

        await self.play_source(*source_title_url, self.on_song_ended)

    async def add_playlist(self, query: str):
        if not isinstance(self.voice_client, VoiceClient):
             # if not connected to vc
             self.logger.warning(f"add_playlist used before connecting to voice channel")
             return
        urls_titles = await self.yt_dlp_playlist(query)

        self.logger.info(urls_titles)

        first_url = urls_titles.pop(0)[1]   # url of each element is at index 1

        await self.add_song(first_url)
        for item in urls_titles:
            await self.queue.put(item)




    def on_song_ended(self, error):
        # this function runs whenever a song finishes either by ending or error
        if not self.queue.empty():
            asyncio.run_coroutine_threadsafe( self.play_queue(self.on_song_ended), self.loop)


    async def play_source(self,source: AudioSource, title, url, after):
        # TODO: return embed to reply when play command is used
        if isinstance(self.voice_client, VoiceClient):
            self.logger.info("playing")
            self.voice_client.play(source, after=after)
            async with self.lock:
                self.hist.append((title, url))

    async def play_queue(self, after):
        # TODO: return embed to reply when play command is used
        if isinstance(self.voice_client, VoiceClient):
            self.logger.info("playing next queue song")
            title, url = await self.queue.get()
            
            source = await self.get_source(url)
            if self.voice_client.is_playing():
                self.voice_client.stop()
            self.voice_client.play(source[0], after=after)

            async with self.lock:
                self.hist.append((title, url))


    async def get_source(self, query: str) -> tuple[AudioSource, str, str]: # title and url
        # TODO: correct handeling of opus and non opus sources
        classified = self.classify_query(query)
        before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        match(classified):
            case SourceEnum.YOUTUBE_SOURCE:
                title, url = await self.yt_dlp_url(query)
                return FFmpegOpusAudio(url, before_options=before_options), title, url
            case SourceEnum.URL_SOURCE:
                return discord.FFmpegPCMAudio(query, before_options=before_options), query, query
            case SourceEnum.UNKNOWN|_:
                self.logger.error("query is unknown")
                raise Exception(f"query is unknown {query}")


    def classify_query(self, query: str) -> SourceEnum:
        # return query_type
        if re.match(YOUTUBE_REGEX, query):
            return SourceEnum.YOUTUBE_SOURCE
        elif re.match(URL_REGEX, query):
            return SourceEnum.URL_SOURCE
        else:
            return SourceEnum.UNKNOWN

    async def yt_dlp_url(self, query: str, *yt_dlp_args) -> tuple[str, str]:
        process = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--dump-single-json",
            "--no-warnings",
            "--prefer-free-formats",
            "--skip-download",
            "--simulate",
            "--format", "ba/ba",
            *yt_dlp_args,
            query,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    
        stdout, stderr = await process.communicate()
    
        if process.returncode != 0:
            self.logger.error(stderr.decode())
            raise Exception("yt-dlp failed")
    
        data = json.loads(stdout.decode())
        return data["title"], data["url"]

    async def yt_dlp_playlist(self, query: str) -> list[tuple[str, str]]:
        process = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--flat-playlist",
            "--dump-single-json",
            "--no-warnings",
            "--skip-download",
            "--simulate",
            query,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    
        stdout, stderr = await process.communicate()
    
        if process.returncode != 0:
            self.logger.error(stderr.decode())
            raise Exception("yt-dlp failed")
    
        data = json.loads(stdout.decode())
        return [(e["title"], e["url"]) for e in data["entries"]]


    async def history(self) -> Embed:
        _embed = Embed(
                color=0xff0000, 
                title="Song History", 
                description=(
                    "\n".join(
                        [f"{i}: `{v[0]}`" for i, v in enumerate(reversed(self.hist))][1:]
                        )
                    )
                )
        return _embed




