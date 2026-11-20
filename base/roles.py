from discord import Guild, Member, Role
from discord.ext import commands


def find_roles(guild: Guild, name: str) -> list[Role]:
    """roles whose name matches, ignoring case"""
    needle = name.strip().casefold()

    return [role for role in guild.roles if role.name.casefold() == needle]


def is_self_assignable(role: Role, blacklisted_ids: set[int]) -> bool:
    """
    A role is considered self-assignable if:
        - Discord considers it assignable (e.g. not @everyone, not managed by an integration, is within the bot's authority)
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
                raise commands.RoleNotFound(argument)
            case found:
                raise commands.BadArgument(
                    f"{len(found)} roles are named '{argument}', use a mention or ID instead"
                )
