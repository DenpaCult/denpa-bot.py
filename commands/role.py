import math

from discord import Member
from discord import Role as DiscordRole
from discord.ext import commands

from base.config import Config
from base.database import db
from base.roles import find_roles, is_self_assignable
from dao.blacklist_dao import BlacklistDAO
from models.reply_embeds import ReplyEmbed

USAGE = (
    "use `;;role <name>`, `;;role add <name>`, `;;role remove <name>` or `;;role list`"
)


class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.blacklist_dao = BlacklistDAO(db)

    @commands.command(aliases=["broadcast", "syntonize", "roles"])
    @commands.guild_only()
    async def role(self, ctx: commands.Context, *args: str):
        assert ctx.guild is not None
        assert isinstance(ctx.author, Member)

        cfg = await Config.load(ctx.guild.id)
        valid = cfg.emoji.denpabot
        err = cfg.emoji.error

        blacklisted = {r.id for r in await self.blacklist_dao.get_all(ctx.guild.id)}
        assignable = [r for r in ctx.guild.roles if is_self_assignable(r, blacklisted)]

        match args:
            case () | ("list",):
                return await list_roles(ctx, assignable)
            case ("add" | "remove" as action,):
                return await ctx.send(
                    embed=ReplyEmbed.Error(
                        description=f"{err} | specify a role to {action}. {USAGE}"
                    )
                )

            # support ;;role add <thing> and ;;role <thing>
            case ("add" | "remove" as action, *name):
                pass
            case name:
                action = "add"

        role_name = " ".join(name)
        matches = [r for r in find_roles(ctx.guild, role_name) if r in assignable]

        if len(matches) != 1:
            reason = (
                "is unavailable or does not exist"
                if not matches
                else "is ambiguous, ask a mod"
            )
            return await ctx.send(
                embed=ReplyEmbed.Error(description=f"{err} | '{role_name}' {reason}")
            )

        target = matches[0]

        if action == "add":
            await ctx.author.add_roles(target, reason="self-assigned with ;;role")
            msg = f"{valid} | {ctx.author.display_name} established connection with {target.name}"
        else:
            await ctx.author.remove_roles(target, reason="self-removed with ;;role")
            msg = f"{valid} | {ctx.author.display_name} is no longer in tune with {target.name}"

        await ctx.send(embed=ReplyEmbed(description=msg))


# FIXME: a more elegant pagination solution maybe?
async def list_roles(ctx: commands.Context, roles: list[DiscordRole]):
    names_only = [x.name for x in roles]

    if not names_only:
        return await ctx.send(
            embed=ReplyEmbed().add_field(name="Roles", value="no self-assignable roles")
        )

    per_page = 6
    pages = math.ceil(len(roles) / per_page)

    for i in range(pages):
        per_row = 3
        names_only_trimmed = names_only[i * per_page : i * per_page + per_page]

        msg = ""
        _len = len(names_only_trimmed)

        for j in range(0, _len, per_row):  # {per_row} roles per row, seperated by ˖˚˳⌖
            msg += " ˖˚˳⌖  ".join(names_only_trimmed[j : min(j + 3, _len)]) + "\n"

        embed = ReplyEmbed().add_field(name="Roles" if i == 0 else "", value=msg)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Role(bot))
