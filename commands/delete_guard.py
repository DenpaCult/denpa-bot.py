import logging

from discord import Member
from base.config import Config
from discord.ext import commands
from base.database import db
from dao.deleteguard_dao import DeleteGuardDAO
from models.delete_guard import GuardedUser


class DeleteGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dao = DeleteGuardDAO(db)
        self.config = Config.read_config()

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @commands.command(aliases=["deleteguard"])
    @commands.has_permissions(manage_roles=True)  # FIXME: is tea admin?
    async def guard(self, ctx: commands.Context, action: str, *args: Member):
        assert ctx.guild is not None

        match action:
            case "add":
                self.dao.add(GuardedUser.from_member(args[0]))
                await ctx.send(f"added {args[0].name} to delete guard.")

            case "remove":
                self.dao.remove(GuardedUser.from_member(args[0]))
                await ctx.send(f"removed {args[0].name} from delete guard.")

            case "list":
                ids = list(map(lambda x: x.id, self.dao.get_all(ctx.guild.id)))
                members = filter(lambda m: m.id in ids, ctx.guild.members)
                names = list(map(lambda m: m.name, members))

                # TODO: embed
                out = ", ".join(names) if names else "no guarded users"
                await ctx.send(out)
            case _:
                pass


async def setup(bot):
    await bot.add_cog(DeleteGuard(bot))
