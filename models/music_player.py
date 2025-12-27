import attr
import json
import logging
import re
import asyncio
import requests

from discord import AudioSource, Embed, FFmpegOpusAudio, FFmpegPCMAudio, Guild, Optional, VoiceChannel, VoiceClient, VoiceProtocol
from discord.ext.commands import Bot

from base.stack import Stack
from base.utils import URL_REGEX

YOUTUBE_REGEX = "^https://(?:www.)?youtu(be.com|.be)/.+$"
YOUTUBE_PLAYLIST_REGEX = "^https://(?:www.)?youtu(be.com|.be)/.+list=.+$"


class SourceEnum:
    YOUTUBE_SOURCE = 0
    URL_SOURCE = 1

class YtDlp:
    logger = logging.getLogger(__name__)
    @staticmethod
    async def yt_dlp_url(query: str, playlist: bool = False, *yt_dlp_args) -> dict:
        _args = ("--format", "ba/ba") if not playlist else ("--flat-playlist",)
        process = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--dump-single-json",
            "--no-warnings",
            "--prefer-free-formats",
            "--skip-download",
            "--simulate",
            *_args,
            *yt_dlp_args,
            query,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    
        stdout, stderr = await process.communicate()
    
        if process.returncode != 0:
            YtDlp.logger.error(stderr.decode())
            raise Exception(f"yt-dlp failed {stderr.decode()}")
    
        data = json.loads(stdout.decode())
        return data



@attr.s(auto_attribs=True)
class TrackMetaData:
    title: Optional[str]
    url: str
    type: Optional[int]
    requester: str
    duration: Optional[int]


@attr.s(auto_attribs=True)
class Track:
    source: Optional[AudioSource]
    metadata: TrackMetaData

    logger = logging.getLogger(__name__)


    @classmethod
    async def fetch(cls, query: str, requester: str) -> "Track": # title and url
        # TODO: correct handeling of opus and non opus sources
        track = cls(None, TrackMetaData(None, query, None, requester, None))
        track = await Resolver.resolve(track)
        return track

    @classmethod
    async def playlist(cls, query: str, requester: str) -> list["Track"]:
        return await Resolver.resolve_playlist(query, requester)




class Resolver:
    logger = logging.getLogger(__name__)

    @classmethod
    async def resolve(cls, track: Track) -> Track:
        resolver = cls(track)
        resolver._get_track_type()

        before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        match(track.metadata.type):
            case SourceEnum.YOUTUBE_SOURCE:
                await resolver._youtube()
                resolver.track.source = FFmpegOpusAudio(resolver.track.metadata.url, before_options=before_options)
            case SourceEnum.URL_SOURCE:
                await resolver._url()
                resolver.track.source = FFmpegPCMAudio(resolver.track.metadata.url, before_options=before_options)
            case _:
                Track.logger.error(f"url is unknown {resolver.track.metadata.url}")
                raise Exception(f"query is unknown {resolver.track.metadata}")

        return resolver.track


    @classmethod
    async def resolve_playlist(cls, query: str, requester: str) -> list["Track"]:
        """
        source for each track needs to be resolved when the song is about to be played
        """
        cls.logger.warning("resolve_playlist called")
        tracks_data = await YtDlp.yt_dlp_url(query, True, "--cookies-from-browser", "firefox")

        cls.logger.warning(tracks_data)
        tracks = [Track(None, TrackMetaData(x["title"], x["url"], SourceEnum.YOUTUBE_SOURCE, requester, x["duration"])) for x in tracks_data["entries"]]

        return tracks

    def __init__(self, track: "Track"):
        self.track = track

    # privates
    def _get_track_type(self) -> Track:
        if re.match(YOUTUBE_REGEX, self.track.metadata.url):
            self.track.metadata.type = SourceEnum.YOUTUBE_SOURCE
            return self.track
        elif re.match(URL_REGEX, self.track.metadata.url):
            self.track.metadata.type = SourceEnum.URL_SOURCE
            return self.track
        else:
            return self.track

    async def _youtube(self) -> Track:
        data: dict = await YtDlp.yt_dlp_url(self.track.metadata.url, False, "--cookies-from-browser", "firefox")
        self.track.metadata = TrackMetaData(data["title"], data["url"], self.track.metadata.type, self.track.metadata.requester, data["duration"])
        return self.track
        

    #@staticmethod
    #async def _youtube_playlist(track: "Track") -> list["Track"]:
    #    pass

    async def _url(self) -> Track:
        """
        i need help finishing this
        for now ill just set the title to url
        """
        """
        headers = requests.get(self.track.metadata.url).headers
        title = headers.get("Content-Disposition")
        duration = headers.get("")
        self.track.metadata.title = re.match(r"filename:\"(?:.+)\"", headers.get("Content-Disposition")).groups[0] if  else self.track.metadata.url
        """
        self.track.metadata.title = self.track.metadata.url
        return self.track

    @staticmethod
    def _unknown(_: str) -> None:
        return

class MusicPlayerSingleton:

    _instances: dict[int, "MusicPlayerSingleton"] = {}

    @classmethod
    def get_guild_instance(cls, guild: Guild, bot: Bot|None = None) -> "MusicPlayerSingleton":
        if guild.id not in cls._instances.keys():
            cls._instances[guild.id] = cls(guild, bot.loop)
        
        return cls._instances[guild.id]

    def __init__(self, guild: Guild, loop):
        self.queue: asyncio.Queue[Track] = asyncio.Queue() # title and url
        self.hist: Stack[Track] = Stack([]) # contains the current playing song to get the last song you have to get the n-2th element
        self.voice_client: VoiceClient | VoiceProtocol | None = guild.voice_client
        self.loop = loop
        self.guild = guild
        self.logger = logging.getLogger(__name__)
        

    async def connect(self, channel: VoiceChannel) -> Embed:
        if not await self.is_connected():
            await channel.connect()
            self.voice_client = self.guild.voice_client
            return Embed(color=0xffffff, title=f"Connected to `{channel.name}`")
        
        return Embed(color=0xffffff, title=f"Already connected")

    async def disconnect(self) -> Embed:
        if await self.is_connected():
            del self.queue
            self.queue = asyncio.Queue() # any better ways to clear the queue?
            await self.voice_client.disconnect()
            return Embed(color=0xffffff, title="Disconnected from the voice channel")

        return Embed(color=0xffffff, title="Not connected to a voice channel")

    async def is_connected(self) -> bool:
        """
        this sometimes returns false even if the bot is connected kms
        """
        return isinstance(self.voice_client, VoiceClient) and self.voice_client.is_connected()


    async def add_song(self, query: str|Track, requester: str, skip: bool = False) -> Embed:
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

        track = await Track.fetch(query, requester) if isinstance(query, str) else query

        if not skip and ( self.voice_client.is_playing() or self.voice_client.source ): # idk how to properly do this
            await self.queue.put(track)
            return Embed(color=0xffffff, title=f"{query} added to queue")

        await self._play_track(track, self._on_song_ended)
        
        return Embed(color=0xffffff, title=f"Playing {track.metadata.title}")


    async def add_playlist(self, query: str, requester: str , skip: bool = False) -> Embed:
        """
        skip: whether to skip the current playing song
        """
        if not isinstance(self.voice_client, VoiceClient):
             # if not connected to vc
             self.logger.warning(f"add_playlist used before connecting to voice channel")
             return Embed(color=0xffffff, title="add_playlist used before connecting to voice channel")

        tracks = await Track.playlist(query, requester)

        first_track = tracks.pop(0)   # url of each element is at index 1

        await self.add_song(first_track, first_track.metadata.requester, skip)
        for track in tracks:
            await self.queue.put(track)
        return Embed(color=0xffffff, title=f"added playlist: {query} to queue")

    async def previous(self) -> Embed:
        if not await self.is_connected():
            return Embed(color=0xffffff, title="Not connected to a voice channel")

        if self.hist.size() < 2:
            return Embed(color=0xffffff, title="No previous songs")
        current = self.hist.pop()
        prev = self.hist.pop()
        # optional: add current song back to hist
        # self.hist.push(current)
        await self._play_track(prev, True)
        return Embed(color=0xffffff, title=f"Playing previous song:{prev.metadata.title}")
        


    # privates 🫢
    def _on_song_ended(self, error):
        # this function runs whenever a song finishes either by ending or error
        if not self.queue.empty():
            asyncio.run_coroutine_threadsafe(self._play_queue(self._on_song_ended), self.loop)


    async def _play_track(self,track: Track, after):
        if isinstance(self.voice_client, VoiceClient):
            self.logger.info(f"playing {track.metadata.title}")
            self.voice_client.stop()
            if not track.source:
                track = await track.fetch(track.metadata.url, track.metadata.requester)
            self.voice_client.play(track.source, after=after)
            self.hist.push(track)

    async def _play_queue(self, after):
        # TODO: return embed to reply when play command is used
        if isinstance(self.voice_client, VoiceClient):
            self.logger.info("playing next queue song")
            track = await self.queue.get()
            
            track = await track.fetch(track.metadata.url, track.metadata.requester)
            if self.voice_client.is_playing():
                self.voice_client.stop()
            self.voice_client.play(track.source, after=after)

            self.hist.push(track)



    """
    async def _yt_dlp_url(self, query: str, *yt_dlp_args) -> tuple[str, str, str]:
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
        return data["title"], data["url"], data["duration"]

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
    """

    async def history(self) -> Embed:
        _embed = Embed(
                color=0xff0000, 
                title="Song History", 
                description=(
                    "\n".join(
                        [f"{i}: `{v.metadata.title}`" for i, v in enumerate(self.hist.reveresed())][1:]
                        )
                    )
                )
        return _embed




