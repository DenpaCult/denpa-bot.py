from discord.ext import commands
from dao.blacklist_dao import BlackListDao
from models.blacklist import BlackList
import math

def is_in_guild(): # TODO: move this somewhere else
    async def predicate(ctx):
        return ctx.guild
    return commands.check(predicate)

class role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['broadcast', 'syntonize', 'roles', 'role'])
    @is_in_guild()
    async def Role(self, ctx: commands.Context, *args):
        import discord
        # TODO retrive blacklists and filter by permission
        
        roles = list(map(lambda x: x.name,ctx.guild.roles))

        if (len(args) == 0):
            roles_per_page = 5
            pages = math.ceil(len(roles) / roles_per_page)
            for i in range(pages):
                msg = ', '.join(roles[i*roles_per_page:min(i*roles_per_page + roles_per_page, len(roles) - 1)])
                embed = discord.Embed(color=0x0099ff, description=" ")
                embed.add_field(name="Roles", value=msg)
                await ctx.send(embeds=[embed])





async def setup(bot):
    await bot.add_cog(role(bot))

