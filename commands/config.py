import logging
from attrs import asdict, has
from discord import Embed
from discord.ext import commands

from base.config import Config, GuildConfig


class ConfigCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @commands.command(aliases=["cfg"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def config(self, ctx: commands.Context, *args: str):
        assert ctx.guild
        cfg = await Config.load(ctx.guild.id)

        match args:
            case ("check", *_):
                await ctx.send(self.check(cfg))
            case ("set", *params):
                await ctx.send(await self.update_val(cfg, ctx.guild.id, params))
            case ("help", *params):
                await ctx.send(embed=self.help(cfg, params))
            case _:
                await ctx.send(embed=self.help(cfg, ()))

    def check(self, cfg: GuildConfig) -> str:
        builder = "### Config Check\n"

        error_count = 0

        if cfg.wood.channel_id is None:
            builder += "- cfg.wood.channel_id is not set. ;;wood will not work as expected.\n"
            error_count += 1

        if cfg.cringe.channel_id is None:
            builder += "- cfg.cringe.channel_id is not set. ;;cringe will not work as expected.\n"
            error_count += 1

        if cfg.delete_guard.channel_id is None:
            builder += "- cfg.delete_guard.channel_id is not set. ;;deleteguard will not work as expected\n"
            error_count += 1

        builder += "- TODO(kajo): implement checks for default and koko roles\n"
        builder += "### Summary\n"
        builder += f"{error_count} issues detected. ;;toromi will run "
        builder += "in a degraded state." if error_count else "as expected."

        return builder

    def help(self, cfg: GuildConfig, args) -> Embed:
        args = args[0].lower() if args else ""

        _embed = Embed(color=0x0099FF, description=" ", title="admin config menu")

        if args == "":
            _embed.description = "use with args below to show more info"

            for k in asdict(cfg).keys():
                attrib = cfg.__getattribute__(k)
                value = attrib
                if has(type(attrib)):
                    value = "..."

                _embed.add_field(name=f"{k}: {value}", value="", inline=False)

        elif has(type(cfg.__getattribute__(args))):
            for name, value in asdict(cfg.__getattribute__(args)).items():
                _embed.add_field(name=f"{name}: {value}", value="", inline=False)

        return _embed

    async def update_val(self, cfg: GuildConfig, guild_id: int, *args: str) -> str:
        # TODO: reimplement the embed that hoog did
        report = "FIXME(kajo): this message should have been overwritten"

        match args:
            case ((field, value),):
                try:
                    setattr(cfg, field, maybe_int(value))
                    report = f"set cfg.{field} to {value}"
                except AttributeError:
                    return f"{field} is not a property of GuildConfig"

            case ((feat, field, value),):
                try:
                    setattr(getattr(cfg, feat), field, maybe_int(value))
                    report = f"set cfg.{feat}.{field} to {value}"
                except AttributeError:
                    return f"{feat}.{field} is not a property of GuildConfig "

            case _:
                return (
                    "To use ;;config set, either provide:\n"
                    "`;;config set foo bar` for `cfg.foo = bar`, or\n"
                    "`;;config set foo bar baz` for `cfg.foo.bar = baz`"
                )

        await Config.save(guild_id)
        return report


def maybe_int(s: str) -> str | int:
    try:
        return int(s)
    except ValueError:
        return s


async def setup(bot):
    await bot.add_cog(ConfigCommand(bot))
