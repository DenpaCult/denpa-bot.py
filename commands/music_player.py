import asyncio as aio
import datetime
import logging
import os
import random
import re
from collections import deque
from collections.abc import Sequence
from enum import Enum
from io import StringIO
from math import ceil
from pathlib import Path
from time import perf_counter
from typing import Literal, Self

import audioop
import yt_dlp
from attr import attrib, attrs
from discord import (
    AudioSource,
    ClientException,
    FFmpegPCMAudio,
    Guild,
    Member,
    TextChannel,
    VoiceChannel,
    VoiceClient,
)
from discord.ext import commands
from discord.ext.commands.bot import Bot
from yt_dlp.utils import DownloadError

from models.reply_embeds import ReplyEmbed

COOKIES_ENV = "TOROMI_COOKIES_FILE"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
STREAM_TTL = 3600  # seconds a resolved stream URL is considered fresh


def _clean_err(err: object) -> str:
    """Strip ANSI escape codes so errors render cleanly in Discord."""
    return ANSI_RE.sub("", str(err))


def _ydl_opts(*, flat: bool) -> dict:
    """yt-dlp options; uses a shipped cookies.txt when present."""
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "color": "never",
        "format": "bestaudio/best",
        "extract_flat": "in_playlist" if flat else False,
        "logger": logging.getLogger("yt-dlp"),
    }

    cookies = os.environ.get(COOKIES_ENV)
    if cookies and Path(cookies).is_file():
        opts["cookiefile"] = cookies

    return opts


@attrs(auto_attribs=True)
class SeekableAudioSource(AudioSource):
    real_source: FFmpegPCMAudio = attrib(repr=False)
    volume: float = 1.0  # Volume, 0 to 2

    play_location: float = 0.0  # Where are we roughly playing at?

    def read(self):
        result = self.real_source.read()

        self.play_location += 0.02

        return audioop.mul(result, 2, self.volume)

    def is_opus(self) -> bool:
        return self.real_source.is_opus()

    def cleanup(self) -> None:
        return self.real_source.cleanup()


@attrs(auto_attribs=True)
class Track:
    title: str
    webpage_url: str
    duration: int | None
    requested_by: Member = attrib(repr=False)

    streaming_url: str | None = attrib(repr=False, default=None)
    memoized_stream: SeekableAudioSource | None = attrib(
                                                        init=False,
                                                        default=None
                                                        )
    already_played: bool = attrib(repr=False, default=False)
    stream_timestamp: float = attrib(init=False, repr=False, default=0.0)

    @classmethod
    async def try_from_url(
            cls,
            url: str,
            requested_by: Member
            ) -> Self | list[Self]:
        logger = logging.getLogger("yt-dlp")

        def _extract():
            with yt_dlp.YoutubeDL(_ydl_opts(flat=True)) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            metadata = await aio.to_thread(_extract)
        except DownloadError as e:
            logger.error(f"Error while running yt-dlp: {e}")
            raise RuntimeError(f"yt-dlp error: {_clean_err(e)}") from e

        if not metadata:
            logger.error("yt-dlp returned no data")
            raise RuntimeError("yt-dlp returned no data")

        # To determine if this is a playlist,
        # we just check if `entries` exist or not.
        try:
            if "entries" in metadata:
                result = [
                    cls(
                        title=entry.get("title") or "Unknown title",
                        webpage_url=entry.get("webpage_url") or entry["url"],
                        duration=entry.get("duration"),
                        requested_by=requested_by,
                        streaming_url=None,
                    )
                    for entry in metadata["entries"]
                    if entry
                ]
            else:
                result = cls(
                    title=metadata.get("title") or "Unknown title",
                    webpage_url=metadata["webpage_url"],
                    streaming_url=metadata["url"],
                    duration=metadata.get("duration"),
                    requested_by=requested_by,
                )
        except KeyError:
            logger.error("Incomplete data returned, missing URL")
            raise RuntimeError("yt-dlp returned incomplete data")

        return result

    async def fetch_source(self):
        if self.streaming_url is None:
            def _extract():
                with yt_dlp.YoutubeDL(_ydl_opts(flat=False)) as ydl:
                    return ydl.extract_info(self.webpage_url, download=False)

            try:
                result = await aio.to_thread(_extract)
            except DownloadError as e:
                logging.getLogger("yt-dlp").error(
                    "Error while running yt-dlp: %s", e
                )
                return _clean_err(e)

            if not result:
                return "yt-dlp returned no data"

            self.streaming_url = result["url"]

        assert self.streaming_url is not None
        real_source = FFmpegPCMAudio(self.streaming_url)
        source = SeekableAudioSource(real_source)

        self.memoized_stream = source
        self.stream_timestamp = perf_counter()

    async def get_stream(self):
        if (
            self.memoized_stream is not None
            and perf_counter() - self.stream_timestamp < STREAM_TTL
            and not self.already_played
        ):
            return self.memoized_stream, None

        # A memoized source past its TTL likely points at an expired URL;
        # drop it so fetch_source re-resolves a fresh one.
        if (
            self.memoized_stream is not None
            and perf_counter() - self.stream_timestamp >= STREAM_TTL
        ):
            self.streaming_url = None

        if err := await self.fetch_source():
            return (None, err)

        assert self.memoized_stream is not None
        self.already_played = False

        return self.memoized_stream, None

    async def make_source(self, seek_time: float = 0.0) -> SeekableAudioSource:
        assert self.streaming_url is not None

        before_options = f"-ss {seek_time}" if seek_time > 0 else None
        source = SeekableAudioSource(
            FFmpegPCMAudio(self.streaming_url, before_options=before_options)
        )
        source.play_location = max(seek_time, 0.0)

        # Keep the memoized source in sync so it is the one cleaned up
        # when playback ends (and so the TTL reflects this source).
        self.memoized_stream = source
        self.stream_timestamp = perf_counter()

        return source


@attrs(auto_attribs=True, hash=True)
class MusicPlaying(commands.Cog):
    """Denpa music player."""

    bot: commands.bot.Bot

    @attrs(auto_attribs=True)
    class Player:
        class LoopMode(Enum):
            NoLoop = 0
            LoopCurrent = 1
            LoopQueue = 2

        bot: Bot
        guild: Guild
        backreport_channel: TextChannel
        voice_client: VoiceClient

        history: deque[Track] = attrib(init=False, factory=deque)
        now_playing: Track | None = attrib(init=False, default=None)
        queue: deque[Track] = attrib(init=False, factory=deque)
        queue_lock: aio.Lock = attrib(init=False, factory=aio.Lock)
        player_task: aio.Task[None] | None = attrib(init=False, default=None)
        next_song_event: aio.Event = attrib(init=False, factory=aio.Event)
        cur_source: SeekableAudioSource | None = attrib(
                                                init=False,
                                                default=None
                                                )

        loop_mode: LoopMode = attrib(init=False, default=LoopMode.NoLoop)
        is_shuffle: bool = attrib(init=False, default=False)

        @property
        def logger(self):
            return logging.getLogger(f"GuildState[{self.guild.id}]")

        def on_song_end_cb(self, err):
            loop = self.bot.loop

            def _handle_end():
                self.now_playing = None

                if not self.next_song_event.is_set():
                    self.next_song_event.set()

                if err:
                    if self.history:
                        self.history.pop()

                    self.logger.error(f"Err on play: {err}")

                    aio.create_task(
                        self.backreport_channel.send(
                            f"Error during play: {err}"
                            )
                    )
                    aio.create_task(self.stop())
                    aio.create_task(self.disconnect())

            loop.call_soon_threadsafe(_handle_end)

        async def song_player_task(self):
            """
            main loop of the song player
            awaits the event next_song_event to play the next song
            """
            while True:
                next_track = None
                if not self.queue:
                    return
                async with self.queue_lock:
                    next_track = self.queue.popleft()
                try:
                    source, err = await next_track.get_stream()
                # TODO: limit the exeptions to satisfy linter BLE001
                except Exception as e:
                    await self.backreport_channel.send(
                        f"Unable to obtain audio for {
                            next_track.title
                        } ({next_track.webpage_url}), error: {e}, skipping..."
                    )
                    continue
                else:
                    self.cur_source = source

                if err:
                    await self.backreport_channel.send(err)

                assert source
                self.voice_client.play(
                    source,
                    bitrate=192,
                    application="audio",
                    signal_type="music",
                    after=self.on_song_end_cb,
                )
                self.now_playing = next_track
                self.history.append(next_track)

                await self.backreport_channel.send(
                    f"Playing {
                        next_track.title
                        } ({
                        next_track.webpage_url
                        }), requested by {
                        next_track.requested_by.display_name
                        }."
                )

                prefetch_track = None
                if self.queue:
                    async with self.queue_lock:
                        prefetch_track = self.queue[0]
                        aio.create_task(prefetch_track.fetch_source())

                await self.next_song_event.wait()
                next_track.already_played = True
                self.next_song_event.clear()
                while self.voice_client.is_playing():
                    await aio.sleep(0.05)
                match (self.loop_mode):
                    case self.LoopMode.NoLoop:
                        ...
                    case self.LoopMode.LoopCurrent:
                        async with self.queue_lock:
                            self.queue.appendleft(next_track)
                    case self.LoopMode.LoopQueue:
                        async with self.queue_lock:
                            self.queue.append(next_track)

        async def start(self):
            if self.player_task is not None:
                return

            self.player_task = aio.create_task(self.song_player_task())

            def _(_):
                self.player_task = None

                if len(self.queue):
                    # Start another run of song playing once we're done
                    aio.create_task(self.start())

            self.player_task.add_done_callback(_)

        async def stop(self):

            if self.player_task is None:
                return

            self.player_task.cancel()

        async def seek(self, seconds: float):
            track = self.now_playing
            if track is None:
                raise ValueError("Nothing is playing currently.")

            if track.streaming_url is None:
                if err := await track.fetch_source():
                    raise RuntimeError(err)

            source = await track.make_source(seconds)

            # Thread-safe swap: discord.py pauses, replaces the source, then
            # resumes under the audio player's lock, instead of mutating the
            # live source's real_source from another thread.
            self.voice_client.source = source
            self.cur_source = source

        async def disconnect(self):
            aio.create_task(self.voice_client.disconnect(force=True))

    guild_players: dict[int, Player] = attrib(
                                            init=False,
                                            factory=dict,
                                            hash=False
                                            )

    def get_player(self, guild: Guild):
        if guild.id not in self.guild_players:
            raise ValueError("Inactive player")

        return self.guild_players[guild.id]

    @staticmethod
    def logger():
        return logging.getLogger("MusicPlayer")

    async def vc_guard(
        self, ctx: commands.Context
    ) -> tuple[Member, TextChannel, "MusicPlaying.Player"] | None:
        assert ctx.guild is not None

        invoker = ctx.author
        assert isinstance(invoker, Member)

        text_channel = ctx.channel
        assert isinstance(text_channel, TextChannel)

        try:
            player = self.get_player(ctx.guild)
        except ValueError:
            await text_channel.send("Must join first.")
            return None

        return (invoker, text_channel, player)

    @commands.command()
    @commands.guild_only()
    async def join(self, ctx: commands.Context):
        """Join VC where the user is."""
        assert ctx.guild is not None

        invoker = ctx.author
        assert isinstance(invoker, Member)

        text_channel = ctx.channel
        assert isinstance(text_channel, TextChannel)

        voice_channel = invoker.voice and invoker.voice.channel or None
        assert voice_channel is None or isinstance(voice_channel, VoiceChannel)

        if voice_channel is None:
            await text_channel.send("You must be in a voice channel!")
            return
        try:
            voice_client = await voice_channel.connect(
                                                    timeout=5.0,
                                                    reconnect=True
                                                    )
        except TimeoutError:
            # Log timeout error here
            self.logger().error("Timeout error when trying to join VC.")
            return
        except ClientException:
            return

        if ctx.guild.id not in self.guild_players:
            new_player = self.Player(
                    ctx.bot,
                    ctx.guild,
                    text_channel,
                    voice_client)
            self.guild_players[ctx.guild.id] = new_player

    @commands.command()
    @commands.guild_only()
    async def leave(self, ctx: commands.Context):
        """Leave VC, resetting the queue."""
        assert ctx.guild is not None

        invoker = ctx.author
        assert isinstance(invoker, Member)

        text_channel = ctx.channel
        assert isinstance(text_channel, TextChannel)

        try:
            player = self.get_player(ctx.guild)
        except ValueError:
            if ctx.guild.voice_client is not None:
                await text_channel.send(
                    "Leaving VC even though we should not"
                    " be present there to begin with... this is a bug"
                )
                await ctx.guild.voice_client.disconnect(force=True)
            else:
                await text_channel.send("Already not in VC.")
            return

        await player.stop()
        await player.disconnect()
        del self.guild_players[ctx.guild.id]

        await text_channel.send("Left VC")

    @commands.command(aliases=["p"])
    @commands.guild_only()
    async def play(self, ctx: commands.Context, *, url: str):
        """Add song to the queue."""
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            invoker, text_channel, player = triplet
        else:
            return

        try:
            result = await Track.try_from_url(url, invoker)

        # TODO: limit the exeptions to satisfy linter BLE001
        except Exception as e:
            await text_channel.send(f"Failed to add song to queue: {e}.")
            return

        if isinstance(result, Sequence):
            async with player.queue_lock:
                player.queue.extend(result)
            await player.start()

            await text_channel.send(
                f"Added {
                    len(result)
                } songs to the queue, requested by {
                    invoker.display_name
                }."
            )
        else:
            async with player.queue_lock:
                player.queue.append(result)
            await player.start()

            await text_channel.send(
                f"Added {
                    result.title
                    } to the queue, requested by {
                        invoker.display_name
                    }"
            )

    @commands.command(aliases=["pn"])
    @commands.guild_only()
    async def play_next(self, ctx: commands.Context, *, url: str):
        """Play song next"""
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            invoker, text_channel, player = triplet
        else:
            return

        try:
            result = await Track.try_from_url(url, invoker)

        # TODO: limit the exeptions to satisfy linter BLE001
        except Exception as e:
            await text_channel.send(f"Failed to add song to queue: {e}.")
            return

        if isinstance(result, Sequence):
            await text_channel.send(
                f"Added {len(result)} songs to the"
                f" queue to play next, requested by {invoker.display_name}."
            )
            async with player.queue_lock:
                player.queue.extendleft(result)
            await player.start()
        else:
            await text_channel.send(
                f"Added {result.title} to the"
                f" queue to play next, requested by {invoker.display_name}"
            )
            async with player.queue_lock:
                player.queue.appendleft(result)
            await player.start()

    @commands.command(aliases=["prev", "last", "back"])
    @commands.guild_only()
    async def previous(self, ctx: commands.Context):
        """Play previously played song next"""
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        if len(player.history) < 2:
            await text_channel.send("No song had been played previously.")
            return

        prev_track = player.history[-2]
        await self.play_next(ctx, url=prev_track.webpage_url)

    @commands.command()
    @commands.guild_only()
    async def pause(self, ctx: commands.Context):
        """Pause player"""
        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        if player.voice_client.is_paused():
            await text_channel.send("Already paused.")
            return

        player.voice_client.pause()

    @commands.command(aliases=["up"])
    @commands.guild_only()
    async def unpause(self, ctx: commands.Context):
        """Unpause player"""
        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        if not player.voice_client.is_paused():
            await text_channel.send("Already playing.")
            return

        player.voice_client.resume()

    @commands.command(aliases=["s", "next"])
    @commands.guild_only()
    async def skip(self, ctx: commands.Context, to_skip_str: str | None):
        """Skip songs in the queue. Accepts ranges like 2-10."""
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        skip_from = 0
        skip_to = -1

        try:
            if not to_skip_str:
                skip_from = 0
            else:
                try:
                    skip_from = int(to_skip_str) - 1
                    if skip_from < 0:
                        raise ValueError
                    skip_to = skip_from + 1
                except ValueError:
                    skip_from, skip_to = map(int, to_skip_str.split("-"))
                    if skip_from < 1 or skip_to < 1 or skip_from >= skip_to:
                        raise ValueError
                    skip_from -= 1
                    skip_to += 1
        except ValueError:
            await text_channel.send("Invalid argument")
            return

        if len(player.queue) == 0:
            await text_channel.send("Nothing to skip.")
            return

        async with player.queue_lock:
            new_queue = [*player.queue]
            try:
                if skip_to != -1:
                    del new_queue[skip_from:skip_to]
            except TypeError:
                await text_channel.send("Trying to skip non-existent entries")
                return
            player.voice_client.stop()
            player.queue.clear()
            player.queue.extend(new_queue)

            if skip_from == 0:
                # We've skipped current song
                player.next_song_event.set()

    @commands.command()
    @commands.guild_only()
    async def seek(self, ctx: commands.Context, *, target_time: str):
        """Seek playback in the song to specified time"""
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        if player.now_playing is None:
            await text_channel.send("Nothing is playing currently.")
            return

        # convert target_time to seconds
        splt = target_time.split(":")
        target_seconds = 0
        match(len(splt)):
            case 1:
                try:
                    target_seconds = int(splt[0])
                except ValueError:
                    await text_channel.send("Not a valid time")
                    return
            case 2:

                try:
                    m, s = [int(x) for x in splt]
                    if s > 59 or m > 59:
                        await text_channel.send("Not a valid time")
                        return
                    target_seconds = m * 60 + s
                except ValueError:
                    await text_channel.send("Not a valid time")
                    return
            case _:
                await text_channel.send("Not a valid time")
                return
            
        target_second = max(target_seconds, 0)

        try:
            await player.seek(target_second)
        except (ValueError, RuntimeError) as e:
            await text_channel.send(f"Unable to seek: {e}")
            return

        await text_channel.send(f"Seeking to {target_second:.0f}s")

    @commands.command(aliases=["v"])
    @commands.guild_only()
    async def volume(self, ctx: commands.Context, *, volume: int):
        """Set volume of current song from 0 to 200."""
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        if player.cur_source is None:
            await text_channel.send("Nothing is playing currently.")
            return

        player.cur_source.volume = min(max(0, volume / 100), 2)
        await text_channel.send("Volume set to"
                                f" {player.cur_source.volume:.0%}")

    @commands.command()
    @commands.guild_only()
    async def loop(
        self,
        ctx: commands.Context,
        *,
        mode: Literal["off", "current", "queue"],
    ):
        """Set looping mode. Values are off, current and queue."""
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        match (mode):
            case "off":
                player.loop_mode = MusicPlaying.Player.LoopMode.NoLoop
                await text_channel.send("Not looping anymore.")
            case "current":
                player.loop_mode = MusicPlaying.Player.LoopMode.LoopCurrent
                await text_channel.send("Looping current song...")
            case "queue":
                player.loop_mode = MusicPlaying.Player.LoopMode.LoopQueue
                await text_channel.send("Looping the queue now...")

    @commands.command(aliases=["np"])
    @commands.guild_only()
    async def nowplaying(self, ctx: commands.Context):
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        if player.now_playing is None:
            await text_channel.send("Nothing is playing currently.")
            return

        assert len(player.history)
        assert player.cur_source

        cur_time_sec = int(player.cur_source.play_location)
        maybe_dur = player.now_playing.duration

        time_string = None
        played_time_str = f"{datetime.timedelta(seconds=cur_time_sec)}"
        if maybe_dur is None:
            # Unknown duration
            time_string = played_time_str.removeprefix("0:")
        else:
            dur_string = f"{datetime.timedelta(seconds=int(maybe_dur))}"
            if maybe_dur < 3600:
                time_string = f"{
                                  played_time_str.removeprefix('0:')
                                }/{
                                  dur_string.removeprefix('0:')
                                }"
            else:
                time_string = f"{played_time_str}/{dur_string}"

        await text_channel.send(
            f"Now playing {player.now_playing.title} ({time_string})"
            f", requested by {player.now_playing.requested_by.display_name}."
        )

    @commands.command(aliases=["q"])
    @commands.guild_only()
    async def queue(self, ctx: commands.Context, *, page: int | None):
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        page = 1 if page is None else page
        if page < 1:
            await text_channel.send("Invalid page number.")
            return

        queue_text_segments = []
        per_page = 10

        def make_queue_line(track: Track, track_num: int) -> str:
            if track.duration:
                dur_string = (
                    f"{datetime.timedelta(seconds=int(track.duration))}"
                )
                if track.duration < 3600:
                    dur_string = dur_string.removeprefix("0:")

                return (f"{track_num + (per_page * (page - 1))}: [{track.title}]"
                        f"({track.webpage_url}) ~ {dur_string} ~ "
                        f"{track.requested_by.mention}")

            return (f"{track_num + per_page * page}: [{track.title}]"
                    f"({track.webpage_url}) ~ {track.requested_by.mention}")

        _embed = ReplyEmbed(
                title="Queue"
                ).add_field(
                        name="",
                        value=f"page: {
                          page
                        }/{
                          max(ceil(len(player.queue) / per_page), 1)
                        }",
                        )

        if page == 1 and player.now_playing is not None:
            queue_text_segments.append(make_queue_line(player.now_playing, 1))

            queue_list = [*player.queue]

            for i, track in enumerate(queue_list[:10], start=2):
                queue_text_segments.append(make_queue_line(track, i))
        else:
            queue_list = [*player.queue]

            start_indx = 10 * (page - 1)
            for i, track in enumerate(
                queue_list[start_indx: start_indx + 10], start=1
            ):
                queue_text_segments.append(make_queue_line(track, i))

        if not queue_text_segments:
            await text_channel.send("emty!!")
            return

        _embed.set_description("\n".join(queue_text_segments))

        await text_channel.send(embed=_embed)

    @commands.command(aliases=["h", "hist"])
    @commands.guild_only()
    async def history(self, ctx: commands.Context, *, page: int | None):
        HISTORY_LENGTH = 10

        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        page = 1 if page is None else page
        if page < 1:
            await text_channel.send("Invalid page number.")
            return

        page -= 1

        historyEmbed = ReplyEmbed(
                title="Song History"
                )

        # delta made history upside down
        _history = list(reversed(player.history))
        # empty check
        if len(_history) == 0:
            await text_channel.send(embed=ReplyEmbed(title="emty!!"))
            return

        _desc = ""

        for i, track in enumerate(
                _history[
                    page*HISTORY_LENGTH:page*HISTORY_LENGTH+HISTORY_LENGTH
                    ]
                ):
            # add a field for each song between page * defined length
            # to page * defined length + 10
            _desc += f"{
              "current" if i == 0 else i
            }: [{track.title}]({track.webpage_url})\n"

        if len(_history) > page*HISTORY_LENGTH+HISTORY_LENGTH:
            # description will be number off songs after this page
            _desc += f"and {
                  len(_history) - page*HISTORY_LENGTH+HISTORY_LENGTH
                } more!"

        historyEmbed.set_description(_desc)

        await text_channel.send(embed=historyEmbed)

    @commands.command(aliases=["random"])
    @commands.guild_only()
    async def shuffle(self, ctx: commands.Context):
        assert ctx.guild
        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        async with player.queue_lock:
            random.shuffle(player.queue)

        await text_channel.send(
                embed=ReplyEmbed(
                    description="Shuffled songs in the queue"
                    )
                )

    @commands.command()
    @commands.guild_only()
    async def debug(self, ctx: commands.Context):
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, _ = triplet
        else:
            return

        response = repr(self)
        response = StringIO(response)

        while next_ := response.read(2000):
            await text_channel.send(next_)

    @commands.command()
    @commands.guild_only()
    async def debug2(self, ctx: commands.Context):
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        await text_channel.send(str(list(player.history)))

    @commands.command()
    async def version(self, ctx: commands.Context):
        await ctx.reply(yt_dlp.version.__version__)


async def setup(bot):
    await bot.add_cog(MusicPlaying(bot))
