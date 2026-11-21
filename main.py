import logging
import os

import discord
from discord import Guild
from discord.ext import commands
from dotenv import load_dotenv

from base.database import db

discord.utils.setup_logging()
logger = logging.getLogger(__name__)

load_dotenv()

intents = discord.Intents.none()
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
intents.members = True
intents.message_content = True
intents.emojis = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix=os.environ["TOROMI_PREFIX"], intents=intents, max_messages=1000
)


async def load_extensions(folder: str):
    """
    load every module in {folder} as an extension. each module defines a commands.Cog
    and an `async def setup(bot)` that adds it, see commands/test_command.py
    """
    for filename in os.listdir(folder):
        if filename.endswith(".py") and filename != "__init__.py":
            extension = f"{folder}.{filename[:-3]}"
            try:
                await bot.load_extension(extension)
                logger.info(f"Loaded {extension}")
            except Exception as e:
                logger.warning(f"Failed to load {extension}: {e}")


@bot.check
async def ignore_dms(ctx: commands.Context) -> bool:
    """Fires CheckFailure when command comes from outside a guild"""
    return ctx.guild is not None


@bot.event
async def on_command_error(ctx: commands.Context, error):
    if ctx.guild is None:
        return  # ignore commands from DMs

    await ctx.send(f":warning: {error}")
    name = f"[{ctx.guild.name}]: " if isinstance(ctx.guild, Guild) else ""

    # If user mistake, report as info, not error
    if isinstance(
        error,
        (commands.CommandNotFound, commands.UserInputError, commands.CheckFailure),
    ):
        logger.info(f"{name}{ctx.author} {ctx.message.content!r}: {error}")
        return

    logger.error(f"{name}command {ctx.prefix}{ctx.command} failed", exc_info=error)


@bot.event
async def on_error(event_method: str, *args, **kwargs):
    name = f"[{args[0].name}]: " if args and isinstance(args[0], Guild) else ""
    logger.exception(f"{name}event {event_method} failed")


async def main():
    db.setup()  # TODO(kajo): remove this out of async

    async with bot:
        await load_extensions("events")
        await load_extensions("commands")
        await bot.start(os.environ["TOROMI_TOKEN"])


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
