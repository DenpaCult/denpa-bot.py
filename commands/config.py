import logging
from discord import Embed
from discord.ext import commands

from base.config import Config

class Config_cmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._config = Config.read_config()
        self.logger = logging.getLogger(__name__)

    @commands.command(aliases=["con", "cfg"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def config(self, ctx, action: str, *args):
        """
        directly changes config.json
        """
        match(action.lower()):
            case "help":
                await ctx.send(embed=self.help_menu(args))
            case "cringe":
                await ctx.send(embed=self.update_val("Cringe", args))
            case "wood":
                await ctx.send(embed=self.update_val("Wood", args))

    def help_menu(self, args) -> Embed:
        if args:
            args = args[0]
        else:
            args = ""

        _embed = Embed(color=0x0099ff, description=" ", title="admin config menu")
        match(args.lower()):
            case "":
                _embed.description = "use with args below to show more info"
                _embed.add_field(name="cringe", value="", inline=False)
                _embed.add_field(name="wood", value="", inline=False)
            case "cringe"|"wood":
                for name in self._config[args.lower().capitalize()].keys():
                    _embed.add_field(name=name,value="",inline=False)

        return _embed

    def update_val(self, name, args) -> Embed:
        _embed = Embed(color=0x0099ff, description="Invalid arguments")
        if len(args) < 2:
            return _embed

        if args[0] in self._config[name].keys():
            try:
                _val = int(args[1])
                self._config[name][args[0]] = _val
                Config.update_config(self._config)
                _embed.description = f"updated {name} {args[0]} to {_val}"
                return _embed
            except:
                return _embed

        return _embed





async def setup(bot):
    await bot.add_cog(Config_cmd(bot))
