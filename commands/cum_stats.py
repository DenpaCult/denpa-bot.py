from discord.ext import commands

from base.database import db
from dao.cum_dao import CumDAO
from models.reply_embeds import ReplyEmbed

IMAGE_URL: str = 'https://media.discordapp.net/attachments/856649672117583875/1150930157750722650/F5w7qXvaIAALzwy.png?width=1410&height=1168'

class CumStats(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.dao = CumDAO(db)

    @commands.command()
    async def cumstats(self, ctx: commands.Context):
        assert ctx.guild

        user = ctx.author

        # override if another user is specifeid
        if ctx.message.mentions:
            user = ctx.message.mentions[0]

        guild_id = ctx.guild.id

        # Who this user sent the most 'cums' towards
        most_cummed_on_id = await self.dao.get_most_cummed_on_user(guild_id, user.id)
        most_cummed_on = ""
        if most_cummed_on_id:
            times = await self.dao.get_pair_count(guild_id, user.id, most_cummed_on_id)
            most_cummed_on = f"<@{most_cummed_on_id}> ({times})"

        # Who this user received the most 'cums' from
        most_cummed_on_by_id = await self.dao.get_most_cummer_on_you(guild_id, user.id)
        most_cummed_on_by = ""
        if most_cummed_on_by_id:
            times = await self.dao.get_pair_count(guild_id, most_cummed_on_by_id, user.id)
            most_cummed_on_by = f"<@{most_cummed_on_by_id}> ({times})"

        # mentions inside an embed show the user's name without pinging them
        _embed = ReplyEmbed(
                description=f"Here are {user.name}'s cum stats!",
                ).set_thumbnail(
                        url=IMAGE_URL
                ).add_field(
                        name='# of times cummed', value=await self.dao.get_cummed_count(guild_id, user.id), inline=True
                ).add_field(
                        name='# of times cummed on', value=await self.dao.get_cummed_on_count(guild_id, user.id), inline=True
                ).add_field(
                        name='most cummed on user by you', value=most_cummed_on, inline=False
                ).add_field(
                        name='user who cummed on you the most', value=most_cummed_on_by, inline=False
                )

        await ctx.send(embed=_embed)


async def setup(bot):
    await bot.add_cog(CumStats(bot))
