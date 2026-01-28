import logging

from discord import Message, Member, TextChannel, Guild
from discord.ext import commands
from base.utils import msg_embed
from base.config import Config
from base.database import db
from dao.deleteguard_dao import DeleteGuardDAO
from models.delete_guard import GuardedUser

# FIXME(kajo): Need to access raw event due to ability to edit old mesasges (before bot init)

class DeleteGuardEvent(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.dao = DeleteGuardDAO(db)

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @commands.Cog.listener()
    async def on_message_delete(self, message: Message):
        assert isinstance(message.author, Member)
        assert isinstance(message.guild, Guild)

        if not self.dao.exists(GuardedUser.from_member(message.author)):
            return

        guild_name = message.guild.name

        embeds = msg_embed(message, f"{message.author.name}", "Deleted Message")
        await message.channel.send(embeds=embeds)

        self.logger.info(f"[{guild_name}]: {message.author} deleted their message")

    @commands.Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        assert isinstance(before.author, Member)
        assert isinstance(before.guild, Guild)

        cfg = await Config.load(before.guild.id)

        # for some reason discord fires this event even if content is unchanged
        if before.content == after.content:
            return

        if not self.dao.exists(GuardedUser.from_member(before.author)):
            return

        if cfg.delete_guard.channel_id is None:
            return await after.channel.send("cfg.delete_guard.channel_id not set. run `;;config delete_guard channel_id <channel_id>`")

        guild_name = before.guild.name

        channel = await self.bot.fetch_channel(cfg.delete_guard.channel_id)
        assert isinstance(channel, TextChannel)

        embeds = msg_embed(before, f"{before.author.name}", "Old Message Content")
        await channel.send(embeds=embeds)

        self.logger.info(f"[{guild_name}]: {before.author} edited their message")


async def setup(bot):
    await bot.add_cog(DeleteGuardEvent(bot))
