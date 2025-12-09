import logging
from discord.ext import commands
from base.config import Config
import math
from dao import blacklist_dao
from dao.blacklist_dao import BlacklistDAO
from models.blacklist import BlacklistRole
from base.checks import is_in_guild

class role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.read_config()
        self.blacklist_dao = blacklist_dao.BlacklistDAO()
        self.logger = logging.getLogger(__name__)

    @commands.command(aliases=["broadcast", "syntonize", "roles", "role"])
    @is_in_guild()
    async def Role(self, ctx: commands.Context, *args):
        from discord import Embed, Permissions
        
        roles = list(map(lambda x: x.name,ctx.guild.roles))

        has_permission = ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_roles
        bl_ids = list(map(lambda x: x.id ,self.blacklist_dao.get_all()))
        bl_names = list(map(lambda x: x.name, filter(lambda x: x.id in bl_ids, ctx.guild.roles)))
        roles = list(filter(lambda x: x not in bl_names, roles)) if not has_permission else roles
    

        if(len(args) == 0):
            roles_per_page = 5
            pages = math.ceil(len(roles) / roles_per_page)
            self.logger.info(f"{pages}, {len(roles)}, {roles_per_page}")
            self.logger.info(f"{roles}")
            for i in range(pages):

                embed = Embed(color=0x0099ff, description=" ")
                msg = ', '.join(roles[i*roles_per_page:i*roles_per_page + roles_per_page])
                embed.add_field(name="Roles", value=msg)
                await ctx.send(embed=embed)

        elif(len(args) >= 2):
            embed = Embed(color=0x0099ff, description=" ")
            role_name = " ".join(args[1:])
            found = list(filter(lambda x: x.name == role_name, ctx.guild.roles))
            msg = f"{self.config['emoji']['error']} | Role doesn't exist"
            if (found):
                match (args[0]):
                    case "remove":
                        if (not has_permission and found[0].name in bl_names):
                            msg = f"{self.config['emoji']['error']} | Not allowed"
                        else:
                            await ctx.author.remove_roles(found[0])
                            msg = f"{self.config['emoji']['denpabot']} | {ctx.author.display_name} is no longer in tune with {found[0].name}"
                    case("add"):
                        if (not has_permission and found[0].name in bl_names):
                            msg = f"{self.config['emoji']['error']} | Not allowed"
                        else:
                            await ctx.author.add_roles(found[0])
                            msg = f"{self.config['emoji']['denpabot']} | {ctx.author.display_name} established connection with {found[0].name}"
            
            embed.add_field(name="Roles", value=msg)
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(role(bot))
