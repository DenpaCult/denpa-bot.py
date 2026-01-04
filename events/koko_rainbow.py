import asyncio
import logging
import random
from discord.ext.commands import Bot, Cog
from discord import Guild, Role, Colour
from base.config import Config


class KokoRainbow(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.task: asyncio.Task | None = None

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @Cog.listener()
    async def on_guild_available(self, guild: Guild):
        cfg = await Config.load(guild.id)
        role_id: int = cfg.koko_role
        koko_role: list[Role] = list(filter(lambda r: r.id == role_id, guild.roles))
        count = len(koko_role)

        if count != 1:
            self.logger.error(f"[{guild.name}]: found {count} != 1 koko roles")
            return

        self.logger.info(f"[{guild.name}]: koko role update_colour task start")
        self.task = asyncio.create_task(update_colour(koko_role[0]))


async def setup(bot: Bot):
    await bot.add_cog(KokoRainbow(bot))


async def update_colour(role: Role):
    seconds_per_minute = 60
    interval_in_minutes = 10

    while True:
        r, g, b = hsv_to_rgb(random.uniform(0, 360), normal_approx(), 1)

        await role.edit(colour=Colour((r << 16) | (g << 8) | b))
        await asyncio.sleep(interval_in_minutes * seconds_per_minute)


# https://stackoverflow.com/a/54024653/
def hsv_to_rgb(h, s, v) -> tuple[int, int, int]:
    def f(n):
        k = (n + h / 60.0) % 6
        return v - v * s * max(min(k, 4 - k, 1), 0)

    return (int(round(f(5) * 255)), int(round(f(3) * 255)), int(round(f(1) * 255)))


# central limit theorem, ignore the clamping please....
def normal_approx(peak=0.5):
    samples = 6

    total = sum(random.random() for _ in range(samples))
    return max(0, min(1, (total / samples) - 0.5 + peak))
