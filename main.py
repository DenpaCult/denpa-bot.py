from dotenv import load_dotenv
from discord.ext import commands
import discord
from base.config import Config
import os
from dao.dao import BaseDAO, Database
import logging
import logging.config
import traceback

logging.config.fileConfig("logging.ini")
logger = logging.getLogger(__name__)

load_dotenv()

cfg = Config.read_config("config.json")
bot = commands.Bot(
    command_prefix=cfg["prefix"], intents=discord.Intents.all(), max_messages=1000
)


async def load_extentions(folder: str):
    """
    load everything in the {folder} folder as a command and/or event
    - commands and events should be a class that inherit commands.Cog
    - same name as the file
    - methods in the class that define the command, they have the @commands.command() decorator (@commands.Cog.listener for events)
      are async, self and ctx as arguments, the name of the method is the name of the command in discord
      ex: def Ping -> {prefix}ping
    - an async setup function should be in the file outside of the class with a bot argument
      it's job is to ayncronisly add the cog to the bot
    - an example is below:

    class test_command(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        @commands.command() # command
        async def ping(self, ctx):
            await ctx.send("Pong!")


        @commands.Cog.listener() # event
        async def on_ready(self):
            print(self.bot.user.name)



    async def setup(bot):
        await bot.add_cog(test_command(bot))
    """
    for filename in os.listdir(folder):
        if filename.endswith(".py") and filename != "__init__.py":
            extension = f"{folder}.{filename[:-3]}"
            try:
                await bot.load_extension(extension)
                logger.info(f"Loaded {extension}")
            except Exception as e:
                logger.warning(f"Failed to load {extension}: {e}")


@bot.event
async def on_command_error(ctx, error):
    traceback.print_exception(type(error), error, error.__traceback__)

    # Optional: send the error to Discord
    await ctx.send(f"⚠️ Error: {error}")


async def main():
    async with bot:
        await load_extentions("events")
        await load_extentions("commands")
        await bot.start(os.environ["TOKEN"])


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
