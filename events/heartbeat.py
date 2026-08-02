import time
import logging
import os
from discord.ext import tasks
from discord.ext.commands import Bot, Cog


class Heartbeat(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    def cog_load(self):
        self.heartbeat.start()

    def cog_unload(self):
        self.heartbeat.cancel()

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @tasks.loop(seconds=30)
    async def heartbeat(self):
        if os.name == "nt":
            return

        with open("/tmp/health", "w") as f:
            f.write(str(int(time.time())))


async def setup(bot: Bot):
    await bot.add_cog(Heartbeat(bot))
