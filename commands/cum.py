import logging
from discord.ext import commands
from discord import Member
from base.config import Config
from dao.cum_dao import CumDAO
from models.cum import Cum

class Cum_cmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dao = CumDAO()
        self.config = Config.read_config()
        self.logger = logging.getLogger(__name__)

    @commands.command()
    @commands.guild_only()
    async def cum(self, ctx: commands.Context, member: Member|None = None):
        # put userid and mentioned member id in cum-dao
        cummer_id = ctx.author.id

        cummee_id = 0
        if member:
            cummee_id = member.id


        if not member or cummee_id == cummer_id:
            await ctx.send(f"Oh no! {ctx.author.mention} has cummed on themselves! {self.config['emoji']['cat1']} {self.config['emoji']['UwU']} :drool: {self.config['emoji']['cunny']}")
            self.dao.add(Cum(cummer_id, cummer_id))
            return

        await ctx.send(f"Oh no! {ctx.author.mention} has cummed on {member.mention}! {self.config['emoji']['cat1']} {self.config['emoji']['UwU']} :drool: {self.config['emoji']['cunny']}")

        self.dao.add(Cum(cummer_id, cummee_id))


async def setup(bot):
    await bot.add_cog(Cum_cmd(bot))
