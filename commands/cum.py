import time

from discord import Member
from discord.ext import commands

from base.config import Config
from base.database import db
from dao.cum_dao import CumDAO
from models.cum import Cum
from models.reply_embeds import ReplyEmbed


class CumCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dao = CumDAO(db)

    @commands.command()
    @commands.guild_only()
    async def cum(self, ctx: commands.Context, member: Member | None = None):
        assert ctx.guild

        # no member means a self cum
        target = member or ctx.author
        who = "themselves" if target.id == ctx.author.id else target.mention

        cfg = await Config.load(ctx.guild.id)

        await ctx.send(
            embed=ReplyEmbed(
                description=f"Oh no! {ctx.author.mention} has cummed on {who}! {cfg.emoji.cat1} {cfg.emoji.uwu} :drool: {cfg.emoji.cunny}"
            )
        )

        await self.dao.add(Cum(ctx.guild.id, ctx.author.id, target.id, now_ms()))


def now_ms() -> int:
    return time.time_ns() // 1_000_000


async def setup(bot):
    await bot.add_cog(CumCommand(bot))
