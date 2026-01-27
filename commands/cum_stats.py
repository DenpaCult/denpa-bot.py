from datetime import datetime, timezone
from discord import Embed
from discord.ext import commands

from base.database import db
from base.config import Config
from dao.cum_dao import CumDAO

class cum_stats_command(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.dao = CumDAO(db)

    @commands.command()
    async def cumstats(self, ctx: commands.Context):
        assert ctx.guild

        cfg = await Config.load(ctx.guild.id)

        cunnyPointPngUrl = 'https://media.discordapp.net/attachments/856649672117583875/1150930157750722650/F5w7qXvaIAALzwy.png?width=1410&height=1168' # the what now?

        user = ctx.author
        # override if another user is specifeid
        if ctx.message.mentions:
            user = ctx.message.mentions[0]

        most_cummed_on_id = await self.dao.get_most_cummed_on_user(user.id)
        most_cummed_on = (await self.bot.fetch_user(most_cummed_on_id)).name if most_cummed_on_id else ""

        most_cummed_on_by_id = await self.dao.get_most_cummer_on_you(user.id)
        most_cummed_on_by = (await self.bot.fetch_user(most_cummed_on_by_id)).name if most_cummed_on_by_id else ""  # these namings are all too confusing
        _embed = Embed(
                color=0xffffff, 
                description="Here are this users cum stats!",
                timestamp=datetime.now(tz=timezone.utc)
                ).set_author( # i just realised Embed is a builder lol
                        name=f"{user.name} | {cfg.emoji.wood} {cfg.emoji.same} tbh",# shouldn't this be changed?
                        icon_url=user.display_avatar.url
                ).set_thumbnail(
                        url=cunnyPointPngUrl
                ).add_field(
                        name='# of times cummed', value=await self.dao.get_cummed_count(user.id), inline=True
                ).add_field(
                        name='# of times cummed on', value=await self.dao.get_cummed_on_count(user.id), inline=True
                ).add_field(
                        name='most cummed on user by you', value=most_cummed_on, inline=False
                ).add_field(
                        name='user who cummed on you the most', value=most_cummed_on_by , inline=False
                ).set_footer(text='cummies :))', icon_url=cunnyPointPngUrl)

        await ctx.send(embed=_embed)

async def setup(bot):
    await bot.add_cog(cum_stats_command(bot))
