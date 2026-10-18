import logging
from sqlite3 import IntegrityError

from attrs import asdict, has
from discord.ext import commands

from base.config import Config, GuildConfig
from models.reply_embeds import ReplyEmbed


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
                await ctx.send(embed=self.check(cfg))
            case ("set", *params):
                await ctx.send(embed=await self.update_val(cfg, ctx.guild.id, params))
            case ("help", *params):
                await ctx.send(embed=self.help(cfg, params))
            case _:
                await ctx.send(embed=self.help(cfg, ()))

    def check(self, cfg: GuildConfig) -> ReplyEmbed:
        b = "### Config Check\n"
        err_count = 0

        if cfg.wood.channel_id is None:
            b += "- cfg.wood.channel_id is not set. (;;wood)\n"
            err_count += 1

        if cfg.cringe.channel_id is None:
            b += "- cfg.cringe.channel_id is not set. (;;cringe)\n"
            err_count += 1

        if cfg.delete_guard.channel_id is None:
            b += "- cfg.delete_guard.channel_id is not set. (;;deleteguard)\n"
            err_count += 1

        if cfg.koko_role is None:
            b += "- cfg.koko_role is not set. (;;toromi role rainbow)\n"
            err_count += 1

        b += "### Summary\n"
        b += f"{err_count} issues detected. ;;toromi will run "
        b += "in a degraded state." if err_count else "as expected."
        embed = ReplyEmbed(description=b) if err_count else ReplyEmbed.Error(description=b)

        return embed

    def help(self, cfg: GuildConfig, args) -> ReplyEmbed:
        # TODO: get the args from the db
        args = args[0].lower() if args else ""

        _embed = ReplyEmbed(description=" ", title="𝒶𝒹𝓂𝒾𝓃 𝒸𝑜𝓃𝒻𝒾𝑔 𝓂𝑒𝓃𝓊")

        if args == "":
            _embed.description = "use with args below to show more info"

            for k in asdict(cfg):
                attrib = cfg.__getattribute__(k)
                value = attrib
                if has(type(attrib)):
                    value = "..."

                _embed.add_field(name=f"{k}: {value}", value="", inline=False)

        elif has(type(cfg.__getattribute__(args))):
            for name, value in asdict(cfg.__getattribute__(args)).items():
                _embed.add_field(name=f"{name}: {value}", value="", inline=False)

        return _embed

    async def update_val(self, cfg: GuildConfig, guild_id: int, args: list[str]) -> ReplyEmbed:
        match args:

            case [field, value]:
                db_name, key = None, field

            case [feat, field, value]:
                db_name, key = feat, field

            case _:
                return ReplyEmbed.Error(
                    description=
                    "To use ;;config set, either provide:\n"
                    "`;;config set foo bar` for `cfg.foo = bar`, or\n"
                    "`;;config set foo bar baz` for `cfg.foo.bar = baz`"
                )

        value = maybe_int(value)
        try:
            await Config.update_db(guild_id, db_name, key, value)
        except (AttributeError, KeyError):
            scope = f"{db_name}." if db_name else ""
            return ReplyEmbed.Error(
                description=f"{scope}{key} is not a property of GuildConfig"
            )
        except IntegrityError:
            scope = f"{db_name}." if db_name else ""
            return ReplyEmbed.Error(
                description=f"{value} is not a valid value for {scope}{key}"
            )

        scope = f"{db_name}." if db_name else ""
        return ReplyEmbed(description=f"set cfg.{scope}{key} to {value}")


def maybe_int(s: str) -> str | int:
    try:
        return int(s)
    except ValueError:
        return s


async def setup(bot):
    await bot.add_cog(ConfigCommand(bot))
