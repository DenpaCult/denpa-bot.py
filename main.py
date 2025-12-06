from discord.ext import commands
import discord
from config.config import read_config
import os


cfg = read_config("test.json")
bot = commands.Bot(command_prefix=cfg['prefix'], intents=discord.Intents.all())

async def load_extensions():
    for filename in os.listdir("./commands"):
        if filename.endswith(".py") and filename != "__init__.py":
            extension = f"commands.{filename[:-3]}"
            try:
                await bot.load_extension(extension)
                print(f"Loaded {extension}")
            except Exception as e:
                print(f"Failed to load {extension}: {e}")

async def main():

    async with bot:
        await load_extensions()
        await bot.start(cfg['token'])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
