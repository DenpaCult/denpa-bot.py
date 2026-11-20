import logging
import random

from discord import Colour, Guild
from discord.ext import tasks
from discord.ext.commands import Bot, Cog

from base.config import Config


class KokoRainbow(Cog):
    """
    Each server's koko role receives a new colour every 10 minutes

    The Idea is we have one loop that shares a lifetime with the bot and then
    in the loop we check every 10min. This prevents network issues from messing
    with the loop
    """

    def __init__(self, bot: Bot):
        self.bot = bot

    async def cog_load(self):
        self.loop.start()

    async def cog_unload(self):
        self.loop.cancel()

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @tasks.loop(minutes=10)
    async def loop(self):
        for guild in self.bot.guilds:
            try:
                await self.tick_guild(guild)
            except Exception:
                self.logger.exception(
                    f"[{guild.name}]: failed to change the koko role's colour"
                )

    @loop.before_loop
    async def wait_until_ready(self):
        await self.bot.wait_until_ready()

    async def tick_guild(self, guild: Guild):
        if guild.unavailable:
            return

        cfg = await Config.load(guild.id)
        if cfg.koko_role is None:
            return

        role = guild.get_role(cfg.koko_role)
        if role is None:
            self.logger.warning(
                f"[{guild.name}]: koko role {cfg.koko_role} doesn't exist"
            )
            return

        r, g, b = hsv_to_rgb(random.uniform(0, 360), normal_approx(), 1)
        await role.edit(colour=Colour((r << 16) | (g << 8) | b))


async def setup(bot: Bot):
    await bot.add_cog(KokoRainbow(bot))


# https://stackoverflow.com/a/54024653/
def hsv_to_rgb(h, s, v) -> tuple[int, int, int]:
    def f(n):
        k = (n + h / 60.0) % 6
        return v - v * s * max(min(k, 4 - k, 1), 0)

    return (round(f(5) * 255), round(f(3) * 255), round(f(1) * 255))


# central limit theorem, ignore the clamping please....
def normal_approx(peak=0.5):
    samples = 6

    total = sum(random.random() for _ in range(samples))
    return max(0, min(1, (total / samples) - 0.5 + peak))
