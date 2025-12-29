from enum import Enum
import json

from attr import attrib, attrs
from typing import Deque, Dict, List, Literal, Self, Sequence, Tuple
import asyncio as aio

import logging

import audioop
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

from asyncio.subprocess import create_subprocess_exec, PIPE


@attrs(auto_attribs=True)
class SeekableAudioSource(AudioSource):
    real_source: FFmpegPCMAudio

    segments: List[bytes] = attrib(factory=list)  # Audio segments
    segment_indx: int = 0  # Audio progress in segments
    volume: float = 1.0  # Volume, 0 to 1

    def read(self):
        self.segment_indx += 1
        while self.segment_indx > len(self.segments):
            frame = self.real_source.read()
            # End of song
            if frame == b"":
                return b""
            self.segments.append(frame)

        # Assume stereo audio always
        return audioop.mul(self.segments[self.segment_indx - 1], 2, self.volume)

    def is_opus(self) -> bool:
        return self.real_source.is_opus()

    def cleanup(self) -> None:
        return self.real_source.cleanup()

    def seek(self, time: float):
        time = max(time, 0)
        self.segment_indx = int(time // 0.02)

    def set_volume(self, volume: float):
        self.volume = volume
        self.volume = min(max(self.volume, 0), 1)


@attrs(auto_attribs=True)
class Track:
    title: str
    url: str
    duration: int | None
    requested_by: Member

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
                        url=entry["url"],
                        duration=entry.get("duration"),
                        requested_by=requested_by,
                    )
                    for entry in metadata["entries"]
                ]
            else:
                result = cls(
                    title=metadata.get("title", "Unknown title"),
                    url=metadata["webpage_url"],
                    duration=metadata.get("duration"),
                    requested_by=requested_by,
                )
        except:
            logger.error("Incomplete data returned, missing URL")
            raise RuntimeError("yt-dlp returned incomplete data")

        return result

    async def get_source(self) -> SeekableAudioSource:
        try:
            process = await create_subprocess_exec(
                "yt-dlp",
                "--cookies-from-browser",
                "firefox",
                "--dump-single-json",
                "--simulate",
                "--no-warnings",
                "-x",
                "-f",
                "ba/ba",
                self.url,
                stdout=PIPE,
                stderr=PIPE,
            )
        except Exception as e:
            logging.getLogger("yt-dlp").exception("Failed to start yt-dlp")
            raise e

        assert process.stdout is not None

        result = json.loads((await process.stdout.read()).decode("utf-8"))
        streaming_url = result["url"]

        real_source = FFmpegPCMAudio(streaming_url)
        return SeekableAudioSource(real_source)


@attrs(auto_attribs=True, hash=True)
class MusicPlaying(commands.Cog):
    """Denpa music player."""

    bot: commands.bot.Bot

    @attrs(auto_attribs=True)
    class Player:
        @attrs(auto_attribs=True)
        class QueueMutex:
            queue: Deque[Track] = attrib(init=False, factory=Deque)
            queue_lock: aio.Lock = attrib(init=False, factory=aio.Lock)

            async def __aenter__(self):
                await self.queue_lock.acquire()

                return self.queue

            async def __aexit__(self, _, __, ___):
                self.queue_lock.release()

        class LoopMode(Enum):
            NoLoop = 0
            LoopCurrent = 1
            LoopQueue = 2

        guild: Guild
        backreport_channel: TextChannel
        voice_client: VoiceClient

        history: Deque[Track] = attrib(init=False, factory=Deque)
        queue_mutex: QueueMutex = attrib(init=False, factory=QueueMutex)
        player_task: aio.Task[None] = attrib(init=False)
        next_song_event: aio.Event = attrib(init=False, factory=aio.Event)
        cur_source: SeekableAudioSource | None = attrib(init=False, default=None)

        loop_mode: LoopMode = attrib(init=False, default=LoopMode.NoLoop)
        is_shuffle: bool = attrib(init=False, default=False)

        @property
        def logger(self):
            return logging.getLogger(f"GuildState[{self.guild.id}]")

        def __attrs_post_init__(self):
            self.player_task = aio.create_task(self.song_player_task())

        def on_song_end_cb(self, err):
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

        async def song_player_task(self):
            while True:
                await aio.sleep(0.1)

                async with self.queue_mutex as queue:
                    if not queue:
                        continue

                    next_track = queue.popleft()

                try:
                    source = await next_track.get_source()
                except Exception as e:
                    await self.backreport_channel.send(
                        f"Unable to obtain audio for {next_track.title} ({next_track.url}), error: {e}, skipping..."
                    )
                    continue
                else:
                    self.cur_source = source

                self.next_song_event.clear()
                self.voice_client.play(
                    source,
                    bitrate=192,
                    application="audio",
                    signal_type="music",
                    after=self.on_song_end_cb,
                )
                self.history.append(next_track)
                await self.backreport_channel.send(
                    f"Playing {next_track.title} ({next_track.url}), requested by {next_track.requested_by.display_name}."
                )

                await self.next_song_event.wait()

                match (self.loop_mode):
                    case self.LoopMode.NoLoop:
                        ...
                    case self.LoopMode.LoopCurrent:
                        async with self.queue_mutex as queue:
                            queue.appendleft(next_track)
                    case self.LoopMode.LoopQueue:
                        queue.append(next_track)

        async def stop(self):
            self.player_task.cancel()
            await self.voice_client.disconnect(force=True)

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
        """Add song to queue"""
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

        async with player.queue_mutex as queue:
            if isinstance(result, Sequence):
                await text_channel.send(
                    f"Added {len(result)} songs to the queue, requested by {invoker.display_name}."
                )
                queue.extend(result)
            else:
                await text_channel.send(
                    f"Added {result.title} to the queue, requested by {invoker.display_name}"
                )
                queue.append(result)

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

        async with player.queue_mutex as queue:
            cur_song = queue.popleft()
            if isinstance(result, Sequence):
                await text_channel.send(
                    f"Added {len(result)} songs to the queue to play next, requested by {invoker.display_name}."
                )
                queue.extendleft(result)
            else:
                await text_channel.send(
                    f"Added {result.title} to the queue to play next, requested by {invoker.display_name}"
                )
                queue.appendleft(result)

            queue.appendleft(cur_song)

    @commands.command(aliases=["prev"])
    @commands.guild_only()
    async def previous(self, ctx: commands.Context):
        """Play previously played song next"""
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        if not len(player.history):
            await text_channel.send("No song had been played previously.")
            return

        prev_track = player.history[-1]
        await self.play_next(ctx, url=prev_track.url)

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
    async def skip(self, ctx: commands.Context, to_skip_str: str):
        """Skip songs in the queue. Accepts following formats:

        skip -- skip current song
        skip n -- skip n-th playing song, starting from 1
        skip x-y -- skip songs #x through #y."""
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        skip_from = 0
        skip_to = 1

        try:
            if to_skip_str == "":
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

        async with player.queue_mutex as queue:
            if len(queue) == 0:
                await text_channel.send("Nothing to skip.")
                return

            new_queue = [*queue]
            try:
                del new_queue[skip_from:skip_to]
            except:
                await text_channel.send("Trying to skip non-existent entries")
                return

            queue.clear()
            queue.extend(new_queue)

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

        if player.cur_source is None:
            await text_channel.send("Nothing is playing currently.")
            return

        player.cur_source.seek(target_second)
        await text_channel.send(f"Seeking to {target_second:.0}s")

    @commands.command()
    @commands.guild_only()
    async def volume(self, ctx: commands.Context, *, volume: int):
        """Set volume of current song from 0 to 100."""
        assert ctx.guild is not None

        if (triplet := await self.vc_guard(ctx)) is not None:
            _, text_channel, player = triplet
        else:
            return

        if player.cur_source is None:
            await text_channel.send("Nothing is playing currently.")
            return

        player.cur_source.set_volume(volume / 100)
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


async def setup(bot):
    await bot.add_cog(MusicPlaying(bot))
