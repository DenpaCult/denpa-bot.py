from discord import Role
from discord.ext import commands
from database import db
from dao.blacklist_dao import BlacklistDAO
from models.blacklist import BlacklistRole


class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dao = BlacklistDAO(db)

    @commands.command()
    async def blacklist(self, ctx: commands.Context, action: str, *args: str):
        match action.strip():
            case "list":
                blacklisted = self.dao.get_all()

                await ctx.send(f"{blacklisted}")
                return

            case "add":
                role = args[0]
                roles = list(filter(lambda x: x.name == role, ctx.guild.roles))

                match len(roles):
                    case 0:
                        await ctx.send(f"no role with name '{role}' exists'")
                        return
                    case 1:
                        target: Role = roles[0]
                        self.dao.add(BlacklistRole(target.id))
                        await ctx.send(f"added {role} to the blacklist")
                        return
                    case _:
                        await ctx.send(f"expected 0 or 1 roles, found {len(roles)}")
                        return

            case "remove":
                await ctx.send("blacklist remove")
            case "help":
                await ctx.send("TODO(kajo): show help menu here")
            case _:
                await ctx.send("invalid option TODO(kajo): write better message")


async def setup(bot):
    await bot.add_cog(Blacklist(bot))
