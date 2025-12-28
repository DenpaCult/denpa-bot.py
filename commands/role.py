import logging
import math
from discord import Embed, Member, Role as DiscordRole
from discord.ext import commands
from dao.blacklist_dao import BlacklistDAO
from base.config import Config
from base.checks import is_in_guild
from base.database import db


class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.read_config()
        self.blacklist_dao = BlacklistDAO(db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @commands.command(aliases=["broadcast", "syntonize", "roles"])
    @is_in_guild()
    async def role(self, ctx: commands.Context, *args):
        if not ctx.guild or not isinstance(ctx.author, Member):
            self.logger.error(f";;role called outside of guild by {ctx.author.name}")
            return

        permissions = ctx.author.guild_permissions
        has_permission = permissions.administrator or permissions.manage_roles

        bl_ids = map(lambda r: r.id, self.blacklist_dao.get_all())
        roles = filter(
            lambda r: (r.id not in bl_ids) or has_permission, ctx.guild.roles
        )

        emoji = self.config["emoji"]["denpabot"]
        emoji_err = self.config["emoji"]["error"]
        embed = Embed(color=0x0099FF)

        match len(args):
            case 0:
                await list_roles(ctx, list(roles)[1:])  # skip @everyone role
            case 1:
                err = (
                    "specify role name"
                    if args[0] in ["add", "remove"]
                    else "unknown subcommand. use 'add' or 'remove'."
                )

                embed.add_field(name="Roles", value=f"{emoji_err} | {err}")
                await ctx.send(embed=embed)
            case _:
                role_name = " ".join(args[1:])
                needle = list(filter(lambda x: x.name == role_name, roles))

                if len(needle) == 0:
                    embed.add_field(
                        name="Roles", value=f"{emoji_err} | role doesn't exist"
                    )
                    await ctx.send(embed=embed)
                    return

                match args[0]:
                    case "add":
                        await ctx.author.add_roles(needle[0])

                        embed.add_field(
                            name="Roles",
                            value=f"{emoji} | {ctx.author.display_name} established connection with {needle[0].name}",
                        )
                        await ctx.send(embed=embed)

                    case "remove":
                        await ctx.author.remove_roles(needle[0])

                        embed.add_field(
                            name="Roles",
                            value=f"{emoji} | {ctx.author.display_name} is no longer in tune with {needle[0].name}",
                        )
                        await ctx.send(embed=embed)
                    case _:
                        embed.add_field(
                            name="Roles",
                            value=f"{emoji_err} | invalid subcommand. use 'add' or 'remove'.",
                        )
                        await ctx.send(embed=embed)


# FIXME: a more elegant pagination solution maybe?
async def list_roles(ctx: commands.Context, roles: list[DiscordRole]):
    names_only = list(map(lambda x: x.name, roles))

    page_count = 5
    pages = math.ceil(len(roles) / page_count)

    for i in range(pages):
        msg = ", ".join(names_only[i * page_count : i * page_count + page_count])

        builder = Embed(color=0x0099FF)  # FIXME: magic number
        builder.add_field(name="Roles" if i == 0 else "", value=msg)
        await ctx.send(embed=builder)


async def setup(bot):
    await bot.add_cog(Role(bot))
