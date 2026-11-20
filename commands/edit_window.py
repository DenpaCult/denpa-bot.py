from collections.abc import Sequence
from typing import Annotated, Literal

from discord import Role, TextChannel
from discord.ext import commands

from base.database import db
from base.roles import RoleArg
from dao.edit_cfg_dao import EditCfgDAO
from models.edit_cfg import EditCfg
from models.reply_embeds import ReplyEmbed

USAGE = (
    "`;;editwindow`: show the current settings\n"
    "`;;editwindow enable` / `disable`\n"
    "`;;editwindow channel <#channel>`: where edits are reported\n"
    "`;;editwindow rule add <seconds> <role> [role...]`: ping these roles for edits at least this old\n"
    "`;;editwindow rule remove <seconds>`\n"
    "`;;editwindow exempt add <role> [role...]`: never delete these roles' edited messages\n"
    "`;;editwindow exempt remove <role> [role...]`\n"
    'role names with spaces need quotes, e.g. `"event organizer"`'
)


# TODO(kajo): migrate to command groups everywhere?


class EditWindow(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dao = EditCfgDAO(db)

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False

        return await commands.has_guild_permissions(administrator=True).predicate(ctx)

    async def current(self, guild_id: int) -> EditCfg:
        return await self.dao.get_guild_cfg(guild_id) or EditCfg(
            guild_id, enabled=False, report_channel_id=None
        )

    @commands.group(name="editwindow", aliases=["ew"], invoke_without_command=True)
    async def editwindow(self, ctx: commands.Context, *, rest: str = ""):
        assert ctx.guild is not None

        if rest:
            return await reply(
                ctx, f"unknown option '{rest.split()[0]}'.\n{USAGE}", error=True
            )

        cfg = await self.current(ctx.guild.id)
        channel = f"<#{cfg.report_channel_id}>" if cfg.report_channel_id else "not set"
        rules = "\n".join(
            f"- {rule.threshold_s}s: " + " ".join(f"<@&{id}>" for id in rule.role_ids)
            for rule in cfg.rules
        )
        exempt = " ".join(f"<@&{id}>" for id in cfg.exempt_role_ids)

        embed = (
            ReplyEmbed(description=USAGE)
            .add_field(name="Enabled", value="yes" if cfg.enabled else "no")
            .add_field(name="Report channel", value=channel)
            .add_field(name="Rules", value=rules or "none", inline=False)
            .add_field(name="Exempt roles", value=exempt or "none", inline=False)
        )
        await ctx.send(embed=embed)

    @editwindow.command()
    async def enable(self, ctx: commands.Context):
        assert ctx.guild is not None
        cfg = await self.current(ctx.guild.id)

        await self.dao.set_config(ctx.guild.id, True, cfg.report_channel_id)
        warning = (
            ""
            if cfg.report_channel_id
            else " no report channel is set yet, see `;;editwindow channel`"
        )
        await reply(ctx, f"edit window monitoring enabled.{warning}")

    @editwindow.command()
    async def disable(self, ctx: commands.Context):
        assert ctx.guild is not None
        cfg = await self.current(ctx.guild.id)

        await self.dao.set_config(ctx.guild.id, False, cfg.report_channel_id)
        await reply(ctx, "edit window monitoring disabled")

    @editwindow.command()
    async def channel(
        self, ctx: commands.Context, _set: Literal["set"] | None, channel: TextChannel
    ):
        assert ctx.guild is not None
        cfg = await self.current(ctx.guild.id)

        await self.dao.set_config(ctx.guild.id, cfg.enabled, channel.id)
        await reply(ctx, f"edits will be reported in {channel.mention}")

    @editwindow.group(invoke_without_command=True)
    async def rule(self, ctx: commands.Context):
        await reply(ctx, f"use `rule add` or `rule remove`.\n{USAGE}", error=True)

    @rule.command(name="add")
    async def rule_add(
        self, ctx: commands.Context, threshold_s: int, *roles: Annotated[Role, RoleArg]
    ):
        assert ctx.guild is not None

        if threshold_s <= 0:
            return await reply(
                ctx, "the threshold must be a positive number of seconds", error=True
            )
        if not roles:
            return await reply(ctx, "name at least one role to ping", error=True)

        added = [
            role
            for role in roles
            if await self.dao.add_rule(ctx.guild.id, threshold_s, role.id)
        ]
        await reply(
            ctx,
            f"edits at least {threshold_s}s old will ping {names(roles)}"
            + already(roles, added),
        )

    @rule.command(name="remove")
    async def rule_remove(self, ctx: commands.Context, threshold_s: int):
        assert ctx.guild is not None

        cfg = await self.current(ctx.guild.id)
        if not any(rule.threshold_s == threshold_s for rule in cfg.rules):
            return await reply(ctx, f"there is no {threshold_s}s rule", error=True)

        await self.dao.remove_rule(ctx.guild.id, threshold_s)
        await reply(ctx, f"removed the {threshold_s}s rule")

    @editwindow.group(invoke_without_command=True)
    async def exempt(self, ctx: commands.Context):
        await reply(ctx, f"use `exempt add` or `exempt remove`.\n{USAGE}", error=True)

    @exempt.command(name="add")
    async def exempt_add(self, ctx: commands.Context, *roles: Annotated[Role, RoleArg]):
        assert ctx.guild is not None

        if not roles:
            return await reply(ctx, "name at least one role", error=True)

        added = [
            role
            for role in roles
            if await self.dao.add_exempt_role(ctx.guild.id, role.id)
        ]
        await reply(
            ctx,
            f"edited messages from {names(roles)} won't be deleted"
            + already(roles, added),
        )

    @exempt.command(name="remove")
    async def exempt_remove(
        self, ctx: commands.Context, *roles: Annotated[Role, RoleArg]
    ):
        assert ctx.guild is not None

        if not roles:
            return await reply(ctx, "name at least one role", error=True)

        for role in roles:
            await self.dao.remove_exempt_role(ctx.guild.id, role.id)

        await reply(ctx, f"{names(roles)} no longer exempt")


async def reply(ctx: commands.Context, text: str, error: bool = False):
    embed = (
        ReplyEmbed.Error(description=text) if error else ReplyEmbed(description=text)
    )
    await ctx.send(embed=embed)


def names(roles: Sequence[Role]) -> str:
    return ", ".join(role.name for role in roles)


def already(roles: Sequence[Role], added: list[Role]) -> str:
    existing = [role for role in roles if role not in added]

    return f" ({names(existing)} already set)" if existing else ""


async def setup(bot: commands.Bot):
    await bot.add_cog(EditWindow(bot))
