from discord.ext.commands import check

"""
command checks go here
just import and use the function as a decorator bellow the command decrator
https://discordpy-reborn.readthedocs.io/en/latest/ext/commands/commands.html#checks
"""

def is_in_guild():
    async def predicate(ctx):
        return ctx.guild
    return check(predicate)
