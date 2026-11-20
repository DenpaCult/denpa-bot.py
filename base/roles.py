from discord import Guild, Member, Role
from discord.ext import commands


def quote_hint(text: str) -> str:
    """
    Template text for users for when they try using single quotes to name a role or something.
    Discord.js seems to not like single quotes which is unfortnate
    """
    if text.startswith("'") or text.endswith("'"):
        return ' (names with spaces need double quotes, like "event organizer")'

    return ""


def find_roles(guild: Guild, name: str) -> list[Role]:
    """roles whose name matches, ignoring case"""
    needle = name.strip().casefold()

    return [role for role in guild.roles if role.name.casefold() == needle]


def is_self_assignable(role: Role, blacklisted_ids: set[int]) -> bool:
    """
    A role is considered self-assignable if:
        - Discord considers it assignable (e.g. not @everyone, not managed by an integration, is within ;;toromi's authority)
        - It is not blacklisted
        - Has at most as many permissions as @everyone
    """

    return (
        role.is_assignable()
        and role.id not in blacklisted_ids
        and role.permissions <= role.guild.default_role.permissions
    )


def is_admin(member: Member) -> bool:
    return member.guild_permissions.administrator


def can_manage_roles(member: Member) -> bool:
    return (
        member.guild_permissions.administrator or member.guild_permissions.manage_roles
    )


class RoleArg(commands.Converter[Role]):
    """a role by mention, ID or name. unlike discord.py's RoleConverter, names ignore case"""

    async def convert(self, ctx: commands.Context, argument: str) -> Role:
        assert ctx.guild is not None

        try:
            return await commands.RoleConverter().convert(ctx, argument)
        except commands.RoleNotFound:
            pass

        match find_roles(ctx.guild, argument):
            case [role]:
                return role
            case []:
                raise commands.BadArgument(
                    f'role "{argument}" not found{quote_hint(argument)}'
                )
            case found:
                raise commands.BadArgument(
                    f'{len(found)} roles are named "{argument}", use a mention or ID instead'
                )
