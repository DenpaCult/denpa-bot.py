from discord import Role
from discord.ext import commands

from base.database import db
from dao.blacklist_dao import BlacklistDAO
from models.blacklist import BlacklistRole
from models.reply_embeds import ReplyEmbed


class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dao = BlacklistDAO(db)

    @commands.command(aliases=["bl"])
    @commands.has_permissions(administrator=True, manage_roles=True)
    async def blacklist(self, ctx: commands.Context, action: str, *args: str):
        assert ctx.guild

        action = action.strip()

        match action:
            case "list":
                ids = [x.id for x in await self.dao.get_all(ctx.guild.id)]
                role_names = [x.name for x in filter(lambda r: r.id in ids, ctx.guild.roles)]
                msg = ", ".join(role_names)

            case "add" | "remove":
                role = " ".join(args)
                roles = list(filter(lambda x: x.name == role, ctx.guild.roles))

                match len(roles):
                    case 0:
                        msg = f"no role with name '{role}' exists'"
                    case 1:
                        target: Role = roles[0]
                        if action == "add":
                            await self.dao.add(BlacklistRole.from_role(target))
                            msg = f"added {role} to the blacklist"
                        else:
                            await self.dao.remove(BlacklistRole.from_role(target))
                            msg = f"removed {role} from the blacklist"
                    case _:
                        msg = f"expected 0 or 1 roles, found {len(roles)}"

            case "help":
                msg = """
                list: Show blacklisted roles
                add: blacklist a role
                remove: remove a blacklisted role
                """
            case _:
                msg = "invalid option TODO(kajo): write better message"

        embed = ReplyEmbed().add_field(name="Blacklist", value=msg)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Blacklist(bot))
