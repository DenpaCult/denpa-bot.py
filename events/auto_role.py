from discord.ext.commands import Bot, Cog
from discord import Member, Object
from base.config import Config
from base.logger import Logger


class AutoRole(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = Logger.instance()
        self.config = Config.read_config()

    @Cog.listener()
    async def on_member_join(self, member: Member):
        role_ids: map[Object] = map(
            lambda x: Object(x.id),
            filter(lambda x: x.id in self.config["defaultRoles"], member.guild.roles),
        )

        # TODO: Log action
        await member.add_roles(*role_ids)

async def setup(bot: Bot):
    await bot.add_cog(AutoRole(bot))
