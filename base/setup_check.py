"""
All runtime guild checks for ;;config check
"""

import re

from attrs import asdict
from discord import Guild, TextChannel

from base.config import Config, GuildConfig
from base.database import db
from dao.blacklist_dao import BlacklistDAO
from dao.edit_cfg_dao import EditCfgDAO
from models.edit_cfg import EditCfg

MAX_TIMEOUT_S = 28 * 24 * 60 * 60  # discord's limit
CUSTOM_EMOJI = re.compile(r"<a?:\w+:(\d+)>")

REQUIRED_PERMISSIONS = {
    "moderate_members": ("Timeout Members", "cringe can't time anyone out"),
    "manage_roles": ("Manage Roles", ";;role and the koko role don't work"),
    "add_reactions": ("Add Reactions", "auto reacts (same, take) don't work"),
}

CHANNEL_PERMISSIONS = {
    "view_channel": "View Channel",
    "send_messages": "Send Messages",
    "embed_links": "Embed Links",
}


async def find_problems(guild: Guild, known_emoji_ids: set[int]) -> list[str]:
    cfg = await Config.load(guild.id)
    edit = await EditCfgDAO(db).get_guild_cfg(guild.id)
    blacklisted = {r.id for r in await BlacklistDAO(db).get_all(guild.id)}

    return check(guild, cfg, edit, blacklisted, known_emoji_ids)


def check(
    guild: Guild,
    cfg: GuildConfig,
    edit: EditCfg | None,
    blacklisted: set[int],
    known_emoji_ids: set[int],
) -> list[str]:
    problems: list[str] = []

    for perm, (name, effect) in REQUIRED_PERMISSIONS.items():
        if not getattr(guild.me.guild_permissions, perm):
            problems.append(f";;toromi is missing the {name} permission, {effect}.")

    # woodboard
    problems += channel_problems(
        guild,
        "woodboard",
        cfg.wood.channel_id,
        "`;;config set wood channel_id <channel_id>`",
    )
    if cfg.wood.threshold < 1:
        problems.append(
            f"wood threshold is {cfg.wood.threshold}. `;;config set wood threshold <number>`"
        )

    # cringe
    problems += channel_problems(
        guild,
        "cringe",
        cfg.cringe.channel_id,
        "`;;config set cringe channel_id <channel_id>`",
    )
    if cfg.cringe.threshold < 1:
        problems.append(
            f"cringe threshold is {cfg.cringe.threshold}. `;;config set cringe threshold <number>`"
        )
    if not 0 < cfg.cringe.timeout_time <= MAX_TIMEOUT_S:
        problems.append(
            f"cringe timeout is {cfg.cringe.timeout_time}s, discord only allows 1s to 28 days. "
            "`;;config set cringe timeout_time <seconds>`"
        )
    if cfg.cringe.expire_time <= 0:
        problems.append(
            f"cringe expire_time is {cfg.cringe.expire_time}s. `;;config set cringe expire_time <seconds>`"
        )

    # deleteguard
    problems += channel_problems(
        guild,
        "deleteguard",
        cfg.delete_guard.channel_id,
        "`;;config set delete_guard channel_id <channel_id>`",
    )

    # edit window, only if it's been turned on
    if edit is not None and edit.enabled:
        if not guild.me.guild_permissions.manage_messages:
            problems.append(
                ";;toromi is missing the Manage Messages permission, the edit window can't delete edited messages."
            )
        problems += channel_problems(
            guild,
            "edit window report",
            edit.report_channel_id,
            "`;;editwindow channel #channel`",
        )
        if not edit.rules:
            problems.append(
                "the edit window is enabled but has no rules. `;;editwindow rule add <seconds> <role>`"
            )

        role_ids = edit.exempt_role_ids.union(*(rule.role_ids for rule in edit.rules))
        if missing := [id for id in role_ids if guild.get_role(id) is None]:
            problems.append(
                f"the edit window uses {len(missing)} deleted role(s). check `;;editwindow` and remove them"
            )

    # koko rainbow role
    if cfg.koko_role is None:
        problems.append("no koko role. `;;config set koko_role <role_id>`")
    elif (koko := guild.get_role(cfg.koko_role)) is None:
        problems.append(
            f"the koko role ({cfg.koko_role}) no longer exists. `;;config set koko_role <role_id>`"
        )
    elif koko >= guild.me.top_role:
        problems.append(f"the koko role {koko.name} is above ;;toromi's highest role.")

    # ;;role
    if not blacklisted:
        problems.append(
            "the blacklist is empty, so ;;role lets anyone remove permissionless roles like punishment roles. "
            "`;;blacklist add <role>`"
        )
    if stale := [id for id in blacklisted if guild.get_role(id) is None]:
        problems.append(
            f"{len(stale)} blacklisted role(s) have been deleted. harmless, but `;;blacklist` won't show them"
        )

    # emoji ;;toromi reacts with or matches reactions against
    for field, value in asdict(cfg.emoji).items():
        match = CUSTOM_EMOJI.fullmatch(value)
        if match and int(match[1]) not in known_emoji_ids:
            problems.append(
                f"emoji {field} is a custom emoji ;;toromi can't use ({value}). `;;config set emoji {field} <emoji>`"
            )

    # TODO(hoog): checks on music features

    return problems


def channel_problems(
    guild: Guild, what: str, channel_id: int | None, fix: str
) -> list[str]:
    """problems with a channel ;;toromi posts to. fix: how to set the channel"""
    if channel_id is None:
        return [f"no {what} channel. {fix}"]

    channel = guild.get_channel(channel_id)
    if not isinstance(channel, TextChannel):
        return [
            f"the {what} channel ({channel_id}) no longer exists or isn't a text channel. {fix}"
        ]

    perms = channel.permissions_for(guild.me)
    if missing := [
        name for perm, name in CHANNEL_PERMISSIONS.items() if not getattr(perms, perm)
    ]:
        return [
            f";;toromi can't post in {channel.mention} ({what}), it's missing {', '.join(missing)}"
        ]

    return []
