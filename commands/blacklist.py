from discord import Role
from discord.ext import commands
from base.config import Config
from base.database import db
from dao.blacklist_dao import BlacklistDAO
from models.blacklist import BlacklistRole


class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dao = BlacklistDAO(db)
        self.config = Config.read_config()

    @commands.command(aliases=['bl'])
    @commands.has_permissions(administrator=True, manage_roles=True)
    async def blacklist(self, ctx: commands.Context, action: str, *args: str):
        if not action:
            return

        from discord import Embed

        action = action.strip()
        msg = f"{self.config['emoji']['error']} | Command error"
        
        embed = Embed(color=0x0099ff, description=" ")
        match action:
            case "list":
                blacklisted = ", ".join(set(map(lambda x: x.name, self.dao.get_all())))

                msg = f"{blacklisted}"

            case "add"|"remove":
                role = args[0]
                roles = list(filter(lambda x: x.name == role, ctx.guild.roles))

                match len(roles):
                    case 0:
                        msg = ctx.send(f"no role with name '{role}' exists'")
                    case 1:
                        target: Role = roles[0]
                        if (action == "add"):
                            self.dao.add(BlacklistRole.from_role(target))
                            msg = f"added {role} to the blacklist"
                        else:
                            self.dao.remove(BlacklistRole.from_role(target))
                            msg = f"removed {role} from the blacklist"
                    case _:
                        msg = f"expected 0 or 1 roles, found {len(roles)}"

            case "help":
                msg = """
                list: Show blacklisted roles
                add: blacklist a role
                remove: remove a blacklisted role
                """
            case _:
                msg = "invalid option TODO(kajo): write better message"

        embed.add_field(name="Blacklist", value=msg)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Blacklist(bot))
