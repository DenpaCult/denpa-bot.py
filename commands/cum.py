import logging
from discord.ext import commands
from discord import Member
from base.config import Config
from dao.cum_dao import CumDAO
from models.cum import Cumshot
from base.database import db


class Cum(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dao = CumDAO(db)
        self.config = Config.read_config()
        self.logger = logging.getLogger(__name__)

    @commands.command()
    @commands.guild_only()
    async def cum(self, ctx: commands.Context, member: Member | None = None):
        cummer_id: int = ctx.author.id
        cummee_id: int | None = member.id if member else None

        if not member or cummee_id == cummer_id:
            await ctx.send(
                f"Oh no! {ctx.author.mention} has cummed on themselves! {self.config['emoji']['cat1']} {self.config['emoji']['UwU']} :drool: {self.config['emoji']['cunny']}"
            )
        else:
            await ctx.send(
                f"Oh no! {ctx.author.mention} has cummed on {member.mention}! {self.config['emoji']['cat1']} {self.config['emoji']['UwU']} :drool: {self.config['emoji']['cunny']}"
            )

        self.dao.add(Cumshot(cummer_id, cummee_id if cummee_id != None else cummer_id))


async def setup(bot):
    await bot.add_cog(Cum(bot))
