import logging
from attrs import asdict, has
from discord import Embed
from discord.ext import commands

from base.config import Config, GuildConfig

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
        cfg = await Config.load(ctx.guild.id)
        match(action.lower()):
            case "help":
                await ctx.send(
                        embed=self.help_menu(cfg, args)
                        )
            case _:
                await ctx.send(
                        embed=await self.update_val(
                            cfg, 
                            ctx.guild.id, 
                            [action, *args[:-1]], # all the args between the command and the last arg are the field names (this definitly can be written better)
                            args[-1] # field value
                            )
                        )

    def help_menu(self, cfg: GuildConfig, args) -> Embed:
        args = args[0].lower() if args else ""

        _embed = Embed(
                color=0x0099ff,
                description=" ",
                title="admin config menu"
                )

        if (args == ""):
            _embed.description = "use with args below to show more info"

            for k in asdict(cfg).keys():
                attrib = cfg.__getattribute__(k)
                value = attrib
                if has(type(attrib)):
                    value = "..."

                _embed.add_field(
                        name=f"{k}: {value}", 
                        value="",
                        inline=False
                        )

        elif has(type(cfg.__getattribute__(args))):

            for name, value in asdict(cfg.__getattribute__(args)).items():
                _embed.add_field(
                        name=f"{name}: {value}",
                        value="",
                        inline=False
                        )

        return _embed

    async def update_val(self, cfg: GuildConfig, guild_id: int, names: list, val) -> Embed:
        _embed = Embed(color=0x0099ff, description="Invalid arguments")
        if len(names) < 1:
            return _embed

        last = names.pop()

        try:
            obj = cfg
            for name in names:
                obj = obj.__getattribute__(name)

            try:
                val = int(val)
            except Exception as _:
                pass

            obj.__setattr__(last, val)
            await Config.save(guild_id)
            _embed.description = f"updated {' '.join(names + [last])} to {val}"
            return _embed
        except Exception as _:
            return _embed





async def setup(bot):
    await bot.add_cog(Config_cmd(bot))
