import logging

from discord import Message, Member, TextChannel
from discord.ext import commands
from base.utils import msg_embed
from base.config import Config
from base.database import db
from dao.deleteguard_dao import DeleteGuardDAO
from models.delete_guard import GuardedUser


class DeleteGuardEvent(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.dao = DeleteGuardDAO(db)
        self.config = Config.read_config()

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @commands.Cog.listener()
    async def on_message_delete(self, message: Message):
        assert isinstance(message.author, Member)

        if not self.dao.exists(GuardedUser.from_member(message.author)):
            return

        embeds = msg_embed(message, f"{message.author.name}", "Deleted Message")
        await message.channel.send(embeds=embeds)

    @commands.Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        assert isinstance(before.author, Member)

        # for some reason discord fires this event even if content is unchanged
        if before.content == after.content:
            return

        if not self.dao.exists(GuardedUser.from_member(before.author)):
            return

        channel = await self.bot.fetch_channel(self.config["deleteGuard"]["channelId"])
        assert isinstance(channel, TextChannel)

        embeds = msg_embed(before, f"{before.author.name}", "Old Message Content")
        await channel.send(embeds=embeds)


async def setup(bot):
    await bot.add_cog(DeleteGuardEvent(bot))
