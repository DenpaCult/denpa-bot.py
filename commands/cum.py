import logging
from discord.ext import commands
from discord import Member
from base.config import Config
from base.database import db
from dao.cum_dao import CumDAO
from models.cum import Cum

class Cum_cmd(commands.Cog):
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
            await ctx.send(f"Oh no! {ctx.author.mention} has cummed on themselves! {cfg.emoji.cat1} {cfg.emoji.uwu} :drool: {cfg.emoji.cunny}")
            self.dao.add(Cum(cummer_id, cummer_id))
            return

        await ctx.send(f"Oh no! {ctx.author.mention} has cummed on {member.mention}! {cfg.emoji.cat1} {cfg.emoji.uwu} :drool: {cfg.emoji.cunny}")

        self.dao.add(Cum(cummer_id, cummee_id))


async def setup(bot):
    await bot.add_cog(Cum_cmd(bot))
