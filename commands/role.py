from discord.ext import commands
from base.config import Config
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
        self.config = Config.read_config()

    @commands.command(aliases=['broadcast', 'syntonize', 'roles', 'role'])
    @is_in_guild()
    async def Role(self, ctx: commands.Context, *args):
        import discord
        # TODO retreive blacklists and filter by permission
        
        roles = list(map(lambda x: x.name,ctx.guild.roles))

        embed = discord.Embed(color=0x0099ff, description=" ")
        if (len(args) == 0):
            roles_per_page = 5
            pages = math.ceil(len(roles) / roles_per_page)
            for i in range(pages):
                msg = ', '.join(roles[i*roles_per_page:min(i*roles_per_page + roles_per_page, len(roles) - 1)])
                embed.add_field(name="Roles", value=msg)
                await ctx.send(embed=embed)

        elif(len(args) == 2):
            role_name = args[1]
            found = list(filter(lambda x: x.name == role_name, ctx.guild.roles))
            msg = f"{self.config['emoji']['error']} | Role doesn't exist"
            if (found):

                if (args[0] == "remove"):
                    await ctx.author.remove_roles(found[0])
                    msg = f"{self.config['emoji']['denpabot']} | {ctx.author.display_name} is no longer in tune with {found[0].name}"

                elif(args[0] in ["bl", "blacklist"]):
                    # TODO blacklist logic
                    pass
                elif(args[0] in ["unbl", "unblacklist"]):
                    # TODO unblacklist logic
                    pass

                elif (args[0] == "add"):
                    await ctx.author.add_roles(found[0])
                    msg = f"{self.config['emoji']['denpabot']} | {ctx.author.display_name} established connection with {found[0].name}"

            embed.add_field(name="Roles", value=msg)
            await ctx.send(embed=embed)






async def setup(bot):
    await bot.add_cog(role(bot))

