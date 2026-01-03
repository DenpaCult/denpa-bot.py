import logging
import re
import discord
from discord.ext.commands import Bot, Cog
from base.config import Config


class AutoReact(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.config = Config.read_config()

        self.pairs: list[tuple[re.Pattern[str], str]] = [
            compile_regex(self.config, "take"),
            compile_regex(self.config, "same"),
        ]

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        assert message.guild is not None

        for pat, emoji in self.pairs:
            if not pat.search(message.content):
                continue

            await message.add_reaction(emoji)
            self.logger.info(
                f"[{message.guild.name}] reacted with {emoji} to {message.author.name}'s message"
            )


async def setup(bot: Bot):
    await bot.add_cog(AutoReact(bot))


def compile_regex(config: dict, text: str) -> tuple[re.Pattern[str], str]:
    m = re.compile(r"\W*".join(list(text)), re.IGNORECASE)
    return (m, config["emoji"][text])
