import datetime
from enum import Enum
from io import StringIO
import json
from time import perf_counter

from attr import attrib, attrs
from typing import Deque, Dict, List, Literal, Self, Sequence, Tuple
import asyncio as aio

import logging

import audioop
from discord import (
    AudioSource,
    ClientException,
    FFmpegOpusAudio,
    FFmpegPCMAudio,
    Guild,
    Member,
    TextChannel,
    VoiceChannel,
    VoiceClient,
)
from discord.ext import commands

from asyncio.subprocess import create_subprocess_exec, PIPE


@attrs(auto_attribs=True)
class SeekableAudioSource(AudioSource):
    real_source: FFmpegPCMAudio = attrib(repr=False)
    volume: float = 1.0  # Volume, 0 to 2
    
    play_location: float = 0.0 # Where are we roughly playing at?

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
    memoized_stream: SeekableAudioSource | None = attrib(init=False, default=None)
    stream_timestamp: float = attrib(init=False, repr=False, default=0.0)

    @classmethod
    async def try_from_url(cls, url: str, requested_by: Member) -> Self | List[Self]:
        logger = logging.getLogger("yt-dlp")

        try:
            process = await create_subprocess_exec(
                "yt-dlp",
                "--dump-single-json",
                "--no-warnings",
                "--simulate",
                "--prefer-free-formats",
                "--skip-download",
                "--cookies-from-browser",
                "firefox",
                "-f",
                "ba/ba",
                "--flat-playlist",
                url,
                stdout=PIPE,
                stderr=PIPE,
            )
        except Exception as e:
            logging.getLogger("yt-dlp").exception("Failed to start yt-dlp")
            raise e

        assert process.stdout is not None
        assert process.stderr is not None

        output = (await process.stdout.read()).decode("utf-8")
        if output == "":
            # Error
            error_dump = (await process.stderr.read()).decode("utf-8")
            logger.error(f"Error while running yt-dlp: {error_dump}")
            raise RuntimeError("yt-dlp error", error_dump)

        # To determine if this is a playlist, we just check if `entries` exist or not.
        metadata = json.loads(output)
        is_playlist = "entries" in metadata

        try:
            if is_playlist:
                result = [
                    cls(
                        title=entry.get("title", "Unknown title"),
                        webpage_url=entry["url"],
                        duration=entry.get("duration"),
                        requested_by=requested_by,
                        streaming_url=None,
                    )
                    for entry in metadata["entries"]
                ]
            else:
                result = cls(
                    title=metadata.get("title", "Unknown title"),
                    webpage_url=metadata["webpage_url"],
                    streaming_url=metadata["url"],
                    duration=metadata.get("duration"),
                    requested_by=requested_by,
                )
        except:
            logger.error("Incomplete data returned, missing URL")
            raise RuntimeError("yt-dlp returned incomplete data")

        return result

    async def fetch_source(self):
        if self.streaming_url is None:
            try:
                process = await create_subprocess_exec(
                    "yt-dlp",
                    "--cookies-from-browser",
                    "firefox",
                    "--dump-single-json",
                    "--simulate",
                    "--no-warnings",
                    "-x",
                    "--audio-format",
                    "opus",
                    "-f",
                    "ba/ba",
                    self.webpage_url,
                    stdout=PIPE,
                    stderr=PIPE,
                )
            except Exception as e:
                logging.getLogger("yt-dlp").exception("Failed to start yt-dlp")
                raise e

            assert process.stdout is not None

            result = json.loads((await process.stdout.read()).decode("utf-8"))
            self.streaming_url = result["url"]

        assert self.streaming_url is not None
        real_source = FFmpegPCMAudio(self.streaming_url)
        source = SeekableAudioSource(real_source)

        self.memoized_stream = source
        self.stream_timestamp = perf_counter()

    async def get_stream(self):
        if (
            self.memoized_stream is not None
            and self.stream_timestamp - perf_counter() < 3600
        ):
            return self.memoized_stream

        await self.fetch_source()
        assert self.memoized_stream is not None

        return self.memoized_stream

    async def seek(self, seek_time=0.0):
        target = await self.get_stream()
        assert self.streaming_url is not None

        # Live replace of source is fairly dangerous, but...
        target.real_source = FFmpegPCMAudio(
            self.streaming_url, before_options=f"-ss {seek_time}"
        )
        target.play_location = seek_time


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

        guild: Guild
        backreport_channel: TextChannel
        voice_client: VoiceClient

        history: Deque[Track] = attrib(init=False, factory=Deque)
        now_playing: Track | None = attrib(init=False, default=None)
        queue: Deque[Track] = attrib(init=False, factory=Deque)
        player_task: aio.Task[None] | None = attrib(init=False, default=None)
        next_song_event: aio.Event = attrib(init=False, factory=aio.Event)
        cur_source: SeekableAudioSource | None = attrib(init=False, default=None)

        loop_mode: LoopMode = attrib(init=False, default=LoopMode.NoLoop)
        is_shuffle: bool = attrib(init=False, default=False)

        @property
        def logger(self):
            return logging.getLogger(f"GuildState[{self.guild.id}]")

        def on_song_end_cb(self, err):
            self.now_playing = None
            self.next_song_event.set()

            # TODO: Update DB history

            if err:
                # This _should_ be the same song as we tried to play,
                #   but we failed, so we remove it from history
                self.history.pop()
                self.logger.error(f"Err on play: {err}")

                aio.create_task(
                    self.backreport_channel.send(f"Error during play: {err}")
                )
                aio.create_task(self.stop())

        async def song_player_task(self):
            if not self.queue:
                return

            next_track = self.queue.popleft()

            try:
                source = await next_track.get_stream()
            except Exception as e:
                await self.backreport_channel.send(
                    f"Unable to obtain audio for {next_track.title} ({next_track.webpage_url}), error: {e}, skipping..."
                )
                return
            else:
                self.cur_source = source

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
                f"Playing {next_track.title} ({next_track.webpage_url}), requested by {next_track.requested_by.display_name}."
            )

            prefetch_track = None
            if self.queue:
                prefetch_track = self.queue[0]
                aio.create_task(prefetch_track.fetch_source())

            await self.next_song_event.wait()
            self.voice_client.stop()
            self.next_song_event.clear()

            match (self.loop_mode):
                case self.LoopMode.NoLoop:
                    ...
                case self.LoopMode.LoopCurrent:
                    self.queue.appendleft(next_track)
                case self.LoopMode.LoopQueue:
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
            aio.create_task(self.voice_client.disconnect(force=True))

            if self.player_task is None:
                return

            self.player_task.cancel()

    guild_players: Dict[int, Player] = attrib(init=False, factory=dict, hash=False)

    def get_player(self, guild: Guild):
        if guild.id not in self.guild_players:
            raise ValueError("Inactive player")

        return self.guild_players[guild.id]

    @staticmethod
    def logger():
        return logging.getLogger("MusicPlayer")

    async def vc_guard(
        self, ctx: commands.Context
    ) -> Tuple[Member, TextChannel, "MusicPlaying.Player"] | None:
        assert ctx.guild is not None

        invoker = ctx.author
        assert isinstance(invoker, Member)

        text_channel = ctx.channel
        assert isinstance(text_channel, TextChannel)

        try:
            player = self.get_player(ctx.guild)
        except:
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
            voice_client = await voice_channel.connect(timeout=5.0, reconnect=True)
        except aio.TimeoutError:
            # Log timeout error here
            self.logger.error("Timeout error when trying to join VC.")
            return
        except ClientException:
            return

        if ctx.guild.id not in self.guild_players:
            new_player = self.Player(ctx.guild, text_channel, voice_client)
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
        except:
            if ctx.guild.voice_client is not None:
                await text_channel.send(
                    "Leaving VC even though we should not be present there to begin with... this is a bug"
                )
                await ctx.guild.voice_client.disconnect(force=True)
            else:
                await text_channel.send("Already not in VC.")
            return

        await player.stop()
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
        except Exception as e:
            await text_channel.send(f"Failed to add song to queue: {e}.")
            return

        if isinstance(result, Sequence):
            player.queue.extend(result)
            await player.start()

            await text_channel.send(
                f"Added {len(result)} songs to the queue, requested by {invoker.display_name}."
            )
        else:
            player.queue.append(result)
            await player.start()

            await text_channel.send(
                f"Added {result.title} to the queue, requested by {invoker.display_name}"
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
        except Exception as e:
            await text_channel.send(f"Failed to add song to queue: {e}.")
            return

        if isinstance(result, Sequence):
            await text_channel.send(
                f"Added {len(result)} songs to the queue to play next, requested by {invoker.display_name}."
            )
            player.queue.extendleft(result)
            await player.start()
        else:
            await text_channel.send(
                f"Added {result.title} to the queue to play next, requested by {invoker.display_name}"
            )
            player.queue.appendleft(result)
            await player.start()

    @commands.command(aliases=["prev"])
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

    @commands.command()
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

    @commands.command(aliases=["s"])
    @commands.guild_only()
    async def skip(self, ctx: commands.Context, to_skip_str: str | None):
        """Skip songs in the queue. Accepts ranges like 2-10."""
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        skip_from = 0
        skip_to = 1

        try:
            if not to_skip_str:
                skip_from = 0
            else:
                try:
                    skip_from = int(to_skip_str) - 1
                    if skip_from < 0:
                        raise ValueError
                    skip_to = skip_from + 1
                except:
                    skip_from, skip_to = map(int, to_skip_str.split("-"))
                    if skip_from < 1 or skip_to < 1 or skip_from >= skip_to:
                        raise ValueError
                    skip_from -= 1
                    skip_to += 1
        except:
            await text_channel.send("Invalid argument")
            return

        if len(player.queue) == 0:
            await text_channel.send("Nothing to skip.")
            return

        new_queue = [*player.queue]
        try:
            del new_queue[skip_from:skip_to]
        except:
            await text_channel.send("Trying to skip non-existent entries")
            return

        player.queue.clear()
        player.queue.extend(new_queue)
        await player.start()

        if skip_from == 0:
            # We've skipped current song
            player.next_song_event.set()

    @commands.command()
    @commands.guild_only()
    async def seek(self, ctx: commands.Context, *, target_second: float):
        """Seek playback in the song to specified second"""
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        if player.now_playing is None:
            await text_channel.send("Nothing is playing currently.")
            return

        target_second = max(target_second, 0)

        await player.now_playing.seek(target_second)
        await text_channel.send(f"Seeking to {target_second:.0f}s")

    @commands.command()
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
        await text_channel.send(f"Volume set to {player.cur_source.volume:.0%}")

    @commands.command()
    @commands.guild_only()
    async def loop(
        self,
        ctx: commands.Context,
        *,
        mode: Literal["off"] | Literal["current"] | Literal["queue"],
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
                time_string = f"{played_time_str.removeprefix('0:')}/{dur_string.removeprefix('0:')}"
            else:
                time_string = f"{played_time_str}/{dur_string}"

        await text_channel.send(
            f"Now playing {player.now_playing.title} ({time_string}), requested by {player.now_playing.requested_by.display_name}."
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

        def make_queue_line(track: Track, track_num: int):
            if track.duration:
                dur_string = dur_string = (
                    f"{datetime.timedelta(seconds=int(track.duration))}"
                )
                if track.duration < 3600:
                    dur_string = dur_string.removeprefix("0:")

                return f"{track_num}. {track.title} ({dur_string}): ({track.requested_by.display_name})"
            return f"{track_num}. {track.title}: ({track.requested_by.display_name})"

        if page == 1 and player.now_playing is not None:
            queue_text_segments.append(make_queue_line(player.now_playing, 1))

            queue_list = [*player.queue]

            for i, track in enumerate(queue_list[:10], start=2):
                queue_text_segments.append(make_queue_line(track, i))
        else:
            queue_list = [*player.queue]

            start_indx = 10 * (page - 1)
            for i, track in enumerate(
                queue_list[start_indx : start_indx + 10], start=1
            ):
                queue_text_segments.append(make_queue_line(track, i))

        await text_channel.send("\n".join(queue_text_segments))

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


async def setup(bot):
    await bot.add_cog(MusicPlaying(bot))
