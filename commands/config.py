import logging
from discord import Embed
from discord.ext import commands

from base.config import Config

class Config_cmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    @commands.command(aliases=["con", "cfg"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def config(self, ctx, action: str, *args):
        """
        directly changes config.json
        """
        match(action):
            case "help":
                await ctx.send(embed=Config_cmd.help_menu(args))
            case "cringe":
                await ctx.send(embed=Config_cmd.update_cringe(args))

    @staticmethod
    def help_menu(args) -> Embed:
        if args:
            args = args[0]

        _embed = Embed(color=0x0099ff, description=" ", title="admin config menu")
        match(args):
            case ():
                _embed.description = "use with args below to show more info"
                _embed.add_field(name="cringe", value="", inline=False)
            case "cringe":
                _embed.add_field(name="threshold",value="",inline=False)
                _embed.add_field(name="timeouttime",value="",inline=False)
                _embed.add_field(name="expiretime",value="",inline=False)
                _embed.add_field(name="channelid",value="",inline=False)

        return _embed

    @staticmethod
    def update_cringe(args):
        _embed = Embed(color=0x0099ff, description="Invalid arguments")
        _config = Config.read_config()
        logger = logging.getLogger(__name__)
        logger.info(len(args))
        if len(args) < 2:
            return _embed

        if args[0] in ["threshold", "timeouttime", "expiretime", "channelid"]:
            try:
                _val = int(args[1])
                _config["defaultCringeConfig"][args[0]] = _val
                Config.update_config(_config)
                _embed.description = f"updated cringe {args[0]} to {_val}"
                return _embed
            except:
                return _embed

        return _embed





async def setup(bot):
    await bot.add_cog(Config_cmd(bot))
