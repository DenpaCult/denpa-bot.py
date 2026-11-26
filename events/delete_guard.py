import logging

from discord import Guild, Member, Message, TextChannel
from discord.ext import commands

from base.config import Config
from base.database import db
from base.utils import msg_embed
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
        if message.guild is None:
            return  # DMs

        if not isinstance(message.author, Member):
            return  # Author was a plain User

        assert isinstance(message.guild, Guild)

        if not await self.dao.exists(GuardedUser.from_member(message.author)):
            return

        guild_name = message.guild.name

        embeds = await msg_embed(
            message, f"{message.author.name}", "Deleted Message", allow_nsfw=False
        )
        await message.channel.send(embeds=embeds)

        self.logger.info(f"[{guild_name}]: {message.author} deleted their message")

    @commands.Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        if before.guild is None:
            return  # DMs

        if not isinstance(before.author, Member):
            return  # Author was a plain User

        assert isinstance(before.guild, Guild)

        # Discord will fire this event when it adds a link preview, even if the content is unchanged. 
        if before.content == after.content:
            return

        cfg = await Config.load(before.guild.id)

        if not await self.dao.exists(GuardedUser.from_member(before.author)):
            return

        if cfg.delete_guard.channel_id is None:
            self.logger.warning(
                f"[{before.guild.name}]: {before.author}'s edit not reported, no deleteguard channel. "
                "an admin can run `;;config set delete_guard channel_id <channel_id>`"
            )
            return

        guild_name = before.guild.name

        channel = await self.bot.fetch_channel(cfg.delete_guard.channel_id)
        assert isinstance(channel, TextChannel)

        embeds = await msg_embed(
            before, f"{before.author.name}", "Old Message Content", allow_nsfw=False
        )
        await channel.send(embeds=embeds)

        self.logger.info(f"[{guild_name}]: {before.author} edited their message")


async def setup(bot):
    await bot.add_cog(DeleteGuardEvent(bot))
