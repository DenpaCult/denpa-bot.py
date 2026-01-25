import logging
import re
import discord
from discord.ext.commands import Bot, Cog
from base.config import Config


class AutoReact(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)


    @Cog.listener()
    async def on_message(self, message: discord.Message):
        assert message.guild

        cfg = await Config.load(message.guild.id)

        pairs: list[tuple[re.Pattern[str], str]] = [
            compile_regex("take", cfg.emoji.take),
            compile_regex("same", cfg.emoji.same),
        ]
        assert message.guild is not None

        for pat, emoji in pairs:
            if not pat.search(message.content):
                continue

            await message.add_reaction(emoji)
            self.logger.info(
                f"[{message.guild.name}] reacted with {emoji} to {message.author.name}'s message"
            )


async def setup(bot: Bot):
    await bot.add_cog(AutoReact(bot))


def compile_regex(text: str, emoji: str) -> tuple[re.Pattern[str], str]:
    m = re.compile(r"\W*".join(list(text)), re.IGNORECASE)
    return (m, emoji)
