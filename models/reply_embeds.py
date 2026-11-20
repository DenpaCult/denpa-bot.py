from discord import utils
from discord.embeds import Embed

# TODO(hoog): move this to database config

COLOUR = 0xCF8875  # cotton candy pink
ERROR_COLOR = 0xF81A44
TITLE = "とろ美 𝓁𝑜𝓋𝑒'𝓈 𝓎𝑜𝓊"
ERROR_TITLE = "とろ𝓢𝓽𝓻𝓲𝓴𝓮"
FOOTER = (
    "とろ美( ⑅˃̵o˂̵⑅ )",  # footer name
    "https://cdn.discordapp.com/attachments/1090086858635096086/1515950801833689209/Iy3G2hIhxL_oidNSwogJYgZhkMYS_44XOiv3YFUZFjalGk2S4USGz9IDTjKBAz1W2EvD2uEt-As900-c-k-c0x00ffffff-no-rj.png?ex=6a30deb4&is=6a2f8d34&hm=82bc28a1d2bb03ed82fa7303abc12a854ca85496a1227a13f0643a8b2667fcfe&",  # footer icon
)


class ReplyEmbed(Embed):
    """
    A custom Embed class with default values for the bot.
    """

    def __init__(self, *, colour=COLOUR, title=TITLE, footer=FOOTER, **kwargs):
        # the default has to be computed here, a default argument would be the import time
        kwargs.setdefault("timestamp", utils.utcnow())

        super().__init__(colour=colour, title=title, **kwargs)
        if footer:
            self.set_footer(text=footer[0], icon_url=footer[1])

    @classmethod
    def Error(cls, **kwargs) -> "ReplyEmbed":
        kwargs.setdefault("colour", ERROR_COLOR)
        kwargs.setdefault("title", ERROR_TITLE)

        return cls(**kwargs)

    def set_description(self, description) -> "ReplyEmbed":
        self.description = description
        return self
