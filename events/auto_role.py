import logging
from discord.ext.commands import Bot, Cog
from discord import Member, Object
from base.config import Config


class AutoRole(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @Cog.listener()
    async def on_member_join(self, member: Member):
        assert member.guild is not None

        cfg = await Config.load(member.guild.id)

        role_ids = map(
            lambda x: Object(x.id),
            filter(lambda x: x.id in cfg.default_roles, member.guild.roles),
        )

        await member.add_roles(*role_ids)
        self.logger.info(f"[{member.guild.name}] auto-role for {member.name}")


async def setup(bot: Bot):
    await bot.add_cog(AutoRole(bot))
