import logging

from discord import Member
from discord.ext import commands
from base.database import db
from dao.deleteguard_dao import DeleteGuardDAO
from models.delete_guard import GuardedUser
from models.reply_embeds import ReplyEmbed


class DeleteGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dao = DeleteGuardDAO(db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @commands.command(aliases=["deleteguard", "dg"])
    @commands.has_permissions(manage_roles=True)  # FIXME: is tea admin?
    async def guard(self, ctx: commands.Context, action: str, member: Member | None):
        assert ctx.guild is not None

        _embed = ReplyEmbed(
                            title="𝒜𝒹𝓂𝒾𝓃 𝑀𝑒𝓃𝓊",
                            )

        match action:
            case "add":
                assert member
                await self.dao.add(GuardedUser.from_member(member))
                # await ctx.send(f"added {args[0].name} to delete guard.")
                await ctx.send(
                        embed=_embed.set_description(
                            f"added {member.name} to delete guard."
                            )
                        )

            case "remove":
                assert member
                await self.dao.remove(GuardedUser.from_member(member))
                # await ctx.send(f"removed {member.name} from delete guard.")
                await ctx.send(
                        embed=_embed.set_description(
                            f"removed {member.name} from delete guard."
                            )
                        )

            case "list":
                ids = list(map(lambda x: x.id, await self.dao.get_all(ctx.guild.id)))
                members = filter(lambda m: m.id in ids, ctx.guild.members)
                names = list(map(lambda m: m.name, members))

                # TODO: embed
                out = ", ".join(names) if names else "no guarded users"
                await ctx.send(
                        embed=_embed.add_field(
                            name="Guarded members",
                            value=out,
                            inline=False
                            )
                        )
            case _:
                pass


async def setup(bot):
    await bot.add_cog(DeleteGuard(bot))
