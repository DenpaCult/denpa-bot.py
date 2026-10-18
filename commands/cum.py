import logging
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
        self.logger = logging.getLogger(__name__)

    @commands.command()
    @commands.guild_only()
    async def cum(self, ctx: commands.Context, member: Member|None = None):
        # put userid and mentioned member id in cum-dao

        assert ctx.guild

        cummer_id = ctx.author.id

        cummee_id = 0
        if member:
            cummee_id = member.id

        cfg = await Config.load(ctx.guild.id)


        if not member or cummee_id == cummer_id:
            await ctx.send(
                    embed=ReplyEmbed(
                        description=f"Oh no! {ctx.author.mention} has cummed on themselves! {cfg.emoji.cat1} {cfg.emoji.uwu} :drool: {cfg.emoji.cunny}"
                        )
                    )

            await self.dao.add(Cum(ctx.guild.id, cummer_id, cummer_id, now_ms()))
            return


        await ctx.send(
                embed=ReplyEmbed(
                    description=f"Oh no! {ctx.author.mention} has cummed on {member.mention}! {cfg.emoji.cat1} {cfg.emoji.uwu} :drool: {cfg.emoji.cunny}"
                    )
                )

        await self.dao.add(Cum(ctx.guild.id, cummer_id, cummee_id, now_ms()))


def now_ms() -> int:
    return time.time_ns() // 1_000_000


async def setup(bot):
    await bot.add_cog(CumCommand(bot))
