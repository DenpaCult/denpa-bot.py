from discord.ext import commands
import discord
from config.config import read_config
import os
from dao.dao import BaseDAO, Database

cfg = read_config("test.json")
bot = commands.Bot(command_prefix=cfg['prefix'], intents=discord.Intents.all())

async def load_extensions():
    '''
    load everything in the commands/ folder as a command
    - commands should be a class that inherit commands.Cog
    - same name as the file
    - methods in the class that define the command, they have the @commands.command() decorator
      are async, self and ctx as arguments, the name of the method is the name of the command in discord
      ex: def Ping -> {prefix}ping
    - an async setup function should be in the file outside of the class with a bot argument
      it's job is to ayncronisly add the cog to the bot
    - an example is below:

    class test_command(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong!")

    async def setup(bot):
        await bot.add_cog(test_command(bot))
    '''
    for filename in os.listdir("./commands"):
        if filename.endswith(".py") and filename != "__init__.py":
            extension = f"commands.{filename[:-3]}"
            try:
                await bot.load_extension(extension)
                print(f"Loaded {extension}")
            except Exception as e:
                print(f"Failed to load {extension}: {e}")

async def main():
    db = Database(cfg["sqlite_file"])
    d = BaseDAO(db)
    d.execute("INSERT INTO test VALUES(2,1,1)")
    print(d.fetch_all("SELECT * FROM test"))
    async with bot:
        await load_extensions()
        await bot.start(cfg['token'])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
