import logging

from discord import Guild, HTTPException, Member
from discord.ext import commands

from base.config import Config
from base.database import db
from dao.deleteguard_dao import DeleteGuardDAO
from models.delete_guard import GuardedUser
from models.reply_embeds import ReplyEmbed

USAGE = (
    "`;;dg` or `;;dg list`: show guarded members\n"
    "`;;dg add @member`: repost their deleted messages and log their edits\n"
    "`;;dg remove @member`: stop guarding them\n"
    "the log channel is set with `;;config set delete_guard channel_id <channel_id>`"
)


class DeleteGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dao = DeleteGuardDAO(db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @commands.command(aliases=["deleteguard", "dg"])
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    async def guard(
        self, ctx: commands.Context, action: str = "list", member: Member | None = None
    ):
        assert ctx.guild is not None

        _embed = ReplyEmbed(title="𝒜𝒹𝓂𝒾𝓃 𝑀𝑒𝓃𝓊")

        match action.lower():
            case "add" | "remove" if member is None:
                await ctx.send(
                    embed=_embed.set_description(
                        f"mention the member to {action.lower()}.\n{USAGE}"
                    )
                )

            case "add":
                assert member
                added = await self.dao.add(GuardedUser.from_member(member))
                await ctx.send(
                    embed=_embed.set_description(
                        f"added {member.name} to delete guard."
                        if added
                        else f"{member.name} is already guarded."
                    )
                )

            case "remove":
                assert member
                removed = await self.dao.remove(GuardedUser.from_member(member))
                await ctx.send(
                    embed=_embed.set_description(
                        f"removed {member.name} from delete guard."
                        if removed
                        else f"{member.name} wasn't guarded."
                    )
                )

            case "list":
                cfg = await Config.load(ctx.guild.id)
                channel = (
                    f"<#{cfg.delete_guard.channel_id}>"
                    if cfg.delete_guard.channel_id
                    else "not set"
                )

                names = [
                    await self.describe(ctx.guild, x.id)
                    for x in await self.dao.get_all(ctx.guild.id)
                ]
                out = ", ".join(names) if names else "no guarded users"

                if len(out) > 1024:  # truncation
                    out = out[:1000] + "…"

                await ctx.send(
                    embed=_embed.add_field(
                        name="Channel", value=channel, inline=False
                    ).add_field(name="Guarded members", value=out, inline=False)
                )

            case _:
                await ctx.send(
                    embed=_embed.set_description(f"unknown option '{action}'.\n{USAGE}")
                )

    async def describe(self, guild: Guild, user_id: int) -> str:
        if (member := guild.get_member(user_id)) is not None:
            return f"{member.name} ({user_id})"

        try:
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        except HTTPException:
            return f"({user_id})"

        return f"{user.name} ({user_id}, not in server)"


async def setup(bot):
    await bot.add_cog(DeleteGuard(bot))
