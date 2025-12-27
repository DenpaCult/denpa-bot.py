import json
import logging
import re
import asyncio

from discord import AudioSource, Embed, Enum, FFmpegOpusAudio, Guild, VoiceChannel, VoiceClient, VoiceProtocol
import discord
from discord.ext.commands import Bot

from base.stack import Stack
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
        self.hist: Stack[tuple[str, str]] = Stack([]) # contains the current playing song to get the last song you have to get the n-2th element
        self.voice_client: VoiceClient | VoiceProtocol | None = guild.voice_client
        self.loop = loop
        self.guild = guild
        self.logger = logging.getLogger(__name__)
        self.lock = asyncio.Lock()
        

    async def connect(self, channel: VoiceChannel) -> Embed:
        if not self.voice_client:
            self.logger.info(self.voice_client)
            await channel.connect()
            self.voice_client = self.guild.voice_client
            return Embed(color=0xffffff, title=f"Connected to `{channel.name}`")
        
        return Embed(color=0xffffff, title=f"Already connected")

    async def disconnect(self) -> Embed:
        if self.is_connected():
            del self.queue
            self.queue = asyncio.Queue() # any better ways to clear the queue?
            await self.voice_client.disconnect()
            return Embed(color=0xffffff, title="Disconnected from the voice channel")

        return Embed(color=0xffffff, title="Not connected to a voice channel")

    async def is_connected(self) -> bool:
        return isinstance(self.voice_client, VoiceClient) and self.voice_client.is_connected()


    async def add_song(self, query: str, skip: bool = False) -> Embed:
        """
        play song immediatly if not playing anythong
        add to queue otherwise
        this is the main startpoint that should be called outside
        the bot should be connected to a voice channel for this to work
        skip: whether to skip the current playing song
        """
        if not isinstance(self.voice_client, VoiceClient):
             # if not connected to vc
             self.logger.warning(f"add_song used before connecting to voice channel")
             return Embed(color=0xffffff, title="add_playlist used before connecting to voice channel")

        title = url = ""
        match(self._classify_query(query)):
            case SourceEnum.YOUTUBE_SOURCE:
                title, url = await self._yt_dlp_url(query, "--skip-download")
            case SourceEnum.URL_SOURCE:
                title = url = query
            case _:
                return Embed(color=0xffffff, title="Unknown source")

        if not skip and ( self.voice_client.is_playing() or self.voice_client.source ): # idk how to properly do this
            await self.queue.put((title, url))
            return Embed(color=0xffffff, title=f"{query} added to queue")

        source_title_url = await self._get_source(query)

        await self._play_source(*source_title_url, self._on_song_ended)
        
        return Embed(color=0xffffff, title=f"Playing {source_title_url[1]}")


    async def add_playlist(self, query: str, skip: bool = False) -> Embed:
        """
        skip: whether to skip the current playing song
        """
        if not isinstance(self.voice_client, VoiceClient):
             # if not connected to vc
             self.logger.warning(f"add_playlist used before connecting to voice channel")
             return Embed(color=0xffffff, title="add_playlist used before connecting to voice channel")
        urls_titles = await self._yt_dlp_playlist(query)

        self.logger.info(urls_titles)

        first_url = urls_titles.pop(0)[1]   # url of each element is at index 1

        _embed = await self.add_song(first_url, skip)
        for item in urls_titles:
            await self.queue.put(item)
        return _embed

    async def previous(self) -> Embed:
        if not self.is_connected():
            return Embed(color=0xffffff, title="Not connected to a voice channel")

        if self.hist.size() < 2:
            return Embed(color=0xffffff, title="No previous songs")
        current = self.hist.pop()
        prev = self.hist.pop()
        # optional: add current song back to hist
        # self.hist.push(current)
        return await self.add_song(prev[1], True)
        


    # privates 🫢
    def _on_song_ended(self, error):
        # this function runs whenever a song finishes either by ending or error
        if not self.queue.empty():
            asyncio.run_coroutine_threadsafe(self._play_queue(self._on_song_ended), self.loop)


    async def _play_source(self,source: AudioSource, title, url, after):
        # TODO: return embed to reply when play command is used
        if isinstance(self.voice_client, VoiceClient):
            self.logger.info("playing")
            self.voice_client.stop()
            self.voice_client.play(source, after=after)
            async with self.lock:
                self.hist.push((title, url))

    async def _play_queue(self, after):
        # TODO: return embed to reply when play command is used
        if isinstance(self.voice_client, VoiceClient):
            self.logger.info("playing next queue song")
            title, url = await self.queue.get()
            
            source = await self._get_source(url)
            if self.voice_client.is_playing():
                self.voice_client.stop()
            self.voice_client.play(source[0], after=after)

            async with self.lock:
                self.hist.push((title, url))


    async def _get_source(self, query: str) -> tuple[AudioSource, str, str]: # title and url
        # TODO: correct handeling of opus and non opus sources
        classified = self._classify_query(query)
        before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        match(classified):
            case SourceEnum.YOUTUBE_SOURCE:
                title, url = await self._yt_dlp_url(query)
                return FFmpegOpusAudio(url, before_options=before_options), title, url
            case SourceEnum.URL_SOURCE:
                return discord.FFmpegPCMAudio(query, before_options=before_options), query, query
            case SourceEnum.UNKNOWN|_:
                self.logger.error("query is unknown")
                raise Exception(f"query is unknown {query}")


    def _classify_query(self, query: str) -> SourceEnum:
        # return query_type
        if re.match(YOUTUBE_REGEX, query):
            return SourceEnum.YOUTUBE_SOURCE
        elif re.match(URL_REGEX, query):
            return SourceEnum.URL_SOURCE
        else:
            return SourceEnum.UNKNOWN

    async def _yt_dlp_url(self, query: str, *yt_dlp_args) -> tuple[str, str]:
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

    async def _yt_dlp_playlist(self, query: str) -> list[tuple[str, str]]:
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
                        [f"{i}: `{v[0]}`" for i, v in (self.hist.reveresed())][1:]
                        )
                    )
                )
        return _embed




