from discord.ext import commands

from base.database import db
from dao.cum_dao import CumDAO
from models.reply_embeds import ReplyEmbed


class cum_stats_command(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.dao = CumDAO(db)

    @commands.command()
    async def cumstats(self, ctx: commands.Context):
        assert ctx.guild

        cunnyPointPngUrl = 'https://media.discordapp.net/attachments/856649672117583875/1150930157750722650/F5w7qXvaIAALzwy.png?width=1410&height=1168' # the what now?

        user = ctx.author

        assert ctx.guild
        # override if another user is specifeid
        if ctx.message.mentions:
            user = ctx.message.mentions[0]

        most_cummed_on_id = await self.dao.get_most_cummed_on_user(
                user.id,
                ctx.guild.id
                )
        most_cummed_on = (
                await self.bot.fetch_user(most_cummed_on_id)
                ).name if most_cummed_on_id else ""

        most_cummed_on_by_id = await self.dao.get_most_cummer_on_you(
                user.id, ctx.guild.id
                )
        most_cummed_on_by = (await self.bot.fetch_user(most_cummed_on_by_id)
                             ).name if most_cummed_on_by_id else ""
        # these namings are all too confusing
        _embed = ReplyEmbed(
                description=f"Here are {user.name}'s cum stats!",
                ).set_thumbnail(
                        url=cunnyPointPngUrl
                ).add_field(
                        name='# of times cummed',
                        value=await self.dao.get_cummed_count(
                            user.id,
                            ctx.guild.id
                            ),
                        inline=True
                ).add_field(
                        name='# of times cummed on',
                        value=await self.dao.get_cummed_on_count(
                            user.id,
                            ctx.guild.id
                            ),
                        inline=True
                ).add_field(
                        name='most cummed on user by you',
                        value=most_cummed_on,
                        inline=False
                ).add_field(
                        name='user who cummed on you the most',
                        value=most_cummed_on_by,
                        inline=False
                )

        await ctx.send(embed=_embed)


async def setup(bot):
    await bot.add_cog(cum_stats_command(bot))
