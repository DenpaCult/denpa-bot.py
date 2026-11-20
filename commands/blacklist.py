from discord import Member
from discord.ext import commands

from base.database import db
from base.roles import can_manage_roles, find_roles, is_admin, quote_hint
from dao.blacklist_dao import BlacklistDAO
from models.blacklist import BlacklistRole
from models.reply_embeds import ReplyEmbed

USAGE = (
    "`;;blacklist list`: show blacklisted roles\n"
    "`;;blacklist add <role>`: stop members giving themselves a role (Admin or Manage Roles)\n"
    "`;;blacklist remove <role>`: let members give themselves a role again (Admin)"
)


class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dao = BlacklistDAO(db)

    @commands.command(aliases=["bl"])
    @commands.guild_only()
    async def blacklist(self, ctx: commands.Context, action: str = "list", *args: str):
        assert ctx.guild is not None
        assert isinstance(ctx.author, Member)

        # NB: "Manage Roles" can add to blacklist, however only admins can remove from blacklist
        match action.strip().lower():
            case "list":
                ids = {x.id for x in await self.dao.get_all(ctx.guild.id)}
                names = [r.name for r in ctx.guild.roles if r.id in ids]
                msg = ", ".join(names) or "no roles are blacklisted"

            case "add" if not can_manage_roles(ctx.author):
                msg = "adding to the blacklist needs Admin or Manage Roles"

            case "remove" if not is_admin(ctx.author):
                msg = "removing from the blacklist needs Admin"

            case "add" | "remove" as verb if not args:
                msg = f"specify a role to {verb}"

            case "add" | "remove" as verb:
                name = " ".join(args)

                match find_roles(ctx.guild, name):
                    case []:
                        msg = f'no role named "{name}" exists{quote_hint(name)}'
                    case [role] if verb == "add":
                        added = await self.dao.add(BlacklistRole.from_role(role))
                        msg = (
                            f"blacklisted {role.name}"
                            if added
                            else f"{role.name} is already blacklisted"
                        )
                    case [role]:
                        removed = await self.dao.remove(BlacklistRole.from_role(role))
                        msg = (
                            f"unblacklisted {role.name}"
                            if removed
                            else f"{role.name} isn't blacklisted"
                        )
                    case found:
                        msg = f'{len(found)} roles are named "{name}", rename one first'

            case "help":
                msg = USAGE

            case _:
                msg = f'unknown option "{action}".\n{USAGE}'

        await ctx.send(embed=ReplyEmbed().add_field(name="Blacklist", value=msg))


async def setup(bot):
    await bot.add_cog(Blacklist(bot))
