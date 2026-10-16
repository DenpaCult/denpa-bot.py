import logging
import math

from discord import Member, Role as DiscordRole
from discord.ext import commands
from dao.blacklist_dao import BlacklistDAO
from base.config import Config
from base.database import db
from models.reply_embeds import ReplyEmbed

# FIXME: why this colour?
COLOUR_BLUE = 0x0099FF


class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.blacklist_dao = BlacklistDAO(db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @commands.command(aliases=["broadcast", "syntonize", "roles"])
    async def role(self, ctx: commands.Context, *args):
        assert ctx.guild is not None
        assert isinstance(ctx.author, Member)

        cfg = await Config.load(ctx.guild.id)

        permissions = ctx.author.guild_permissions
        has_permissions = permissions.administrator or permissions.manage_roles

        ids = list(map(lambda r: r.id, await self.blacklist_dao.get_all()))
        roles = filter(lambda r: (r.id not in ids) or has_permissions, ctx.guild.roles)
        roles = filter(lambda r: not r.is_bot_managed(), roles)

        valid = cfg.emoji.denpabot
        err = cfg.emoji.error

        match len(args):
            case 0:
                await list_roles(ctx, list(roles)[1:])  # skip @everyone role
            case 1:
                if args[0] == "list":
                    return await list_roles(ctx, list(roles)[1:])  # skip @everyone role

                err_msg = (
                    "specify role name"
                    if args[0] in ["add", "remove"]
                    else "unknown subcommand. use 'add', 'remove' or 'list'"
                )

                await ctx.send(
                    embed=ReplyEmbed.Error(description=f"{err} | {err_msg}")
                )
            case _:
                role_name = " ".join(args[1:])
                needle = list(filter(lambda x: x.name == role_name, roles))

                if len(needle) == 0:
                    return await ctx.send(
                        embed=ReplyEmbed(
                            description=f"{err} | specified role is unavailable or does not exist"
                        )
                    )

                match args[0]:
                    case "add":
                        await ctx.author.add_roles(needle[0])

                        await ctx.send(
                            embed=ReplyEmbed(
                                description=f"{valid} | {ctx.author.display_name} established connection with {needle[0].name}",
                            )
                        )

                    case "remove":
                        await ctx.author.remove_roles(needle[0])

                        await ctx.send(
                            embed=ReplyEmbed(
                                description=f"{valid} | {ctx.author.display_name} is no longer in tune with {needle[0].name}",
                            )
                        )
                    case _:
                        await ctx.send(
                            embed=ReplyEmbed(
                                description=f"{err} | unknown subcommand. use 'add', 'remove' or 'list'",
                            )
                        )


# FIXME: a more elegant pagination solution maybe?
async def list_roles(ctx: commands.Context, roles: list[DiscordRole]):
    names_only = list(map(lambda x: x.name, roles))

    per_page = 6
    pages = math.ceil(len(roles) / per_page)

    for i in range(pages):
        per_row = 3
        names_only_trimmed = names_only[i * per_page : i * per_page + per_page]

        msg = ""
        _len = len(names_only_trimmed)

        for j in range(0, _len, per_row): # {per_row} roles per row, seperated by ˖˚˳⌖
            msg += " ˖˚˳⌖  ".join(names_only_trimmed[j:min(j+3, _len)]) + "\n"

        embed = ReplyEmbed(
                ).add_field(
            name="Roles" if i == 0 else "", value=msg
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Role(bot))
