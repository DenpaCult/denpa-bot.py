import re
import discord
from discord.ext.commands import Bot, Cog
from base.config import Config
from base.logger import Logger


class AutoReact(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = Logger.instance()
        self.config = Config.read_config()

        self.pairs: list[tuple[re.Pattern[str], str]] = [
            compile_regex(self.config, "take"),
            compile_regex(self.config, "same"),
        ]

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        for pat, emoji in self.pairs:
            if not pat.search(message.content):
                continue

            # TODO: log action here
            await message.add_reaction(emoji)


async def setup(bot: Bot):
    await bot.add_cog(AutoReact(bot))


def compile_regex(config: dict, text: str) -> tuple[re.Pattern[str], str]:
    m = re.compile(r"\W*".join(list(text)), re.IGNORECASE)
    return (m, config["emoji"][text])
