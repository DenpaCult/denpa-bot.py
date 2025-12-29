from discord.ext.commands import check

"""
command checks go here
just import and use the function as a decorator bellow the command decrator
https://discordpy-reborn.readthedocs.io/en/latest/ext/commands/commands.html#checks
"""


# FIXME: this doesn't assist in type checking with ty or pylance
def is_in_guild():
    async def predicate(ctx):
        return ctx.guild

    return check(predicate)
