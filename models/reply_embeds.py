import datetime
from typing import Any, Optional, Union
from discord import Colour
from discord.embeds import Embed
from discord.types.embed import EmbedType

# TODO: move this to database config

COLOR = 0xcf8875 # cotton candy pink
ERROR_COLOR = 0xf81a44
TITLE = "とろ美 𝓁𝑜𝓋𝑒'𝓈 𝓎𝑜𝓊"
ERROR_TITLE = "とろ𝓢𝓽𝓻𝓲𝓴𝓮"
FOOTER = (
        "とろ美( ⑅˃̵o˂̵⑅ )", # footer name
        "https://cdn.discordapp.com/attachments/1090086858635096086/1515950801833689209/Iy3G2hIhxL_oidNSwogJYgZhkMYS_44XOiv3YFUZFjalGk2S4USGz9IDTjKBAz1W2EvD2uEt-As900-c-k-c0x00ffffff-no-rj.png?ex=6a30deb4&is=6a2f8d34&hm=82bc28a1d2bb03ed82fa7303abc12a854ca85496a1227a13f0643a8b2667fcfe&" # footer icon
        )

class ReplyEmbed(Embed):
    '''
    will improve on this later,
    but so far we can have an easily changable default color now without needing to specify it everytime
    TODO: replace all reply embeds in commands with this one,
    TODO: add more default options
    '''

    @classmethod
    def Error(
        cls,
        *,
        colour: Optional[Union[int, Colour]] = ERROR_COLOR,
        color: Optional[Union[int, Colour]] = ERROR_COLOR,
        title: Optional[Any] = ERROR_TITLE,
        type: EmbedType = 'rich',
        url: Optional[Any] = None,
        description: Optional[Any] = None,
        timestamp: Optional[datetime.datetime] = datetime.datetime.now(),
        footer: Optional[tuple[Optional[str], Optional[str]]] = FOOTER
        ):
        return cls(colour=colour, color=color, title=title, type=type, url=url, description=description, timestamp=timestamp, footer=footer)
    # this is a way we could make presets, please don't murder me delta

    def __init__(
        self,
        *,
        colour: Optional[Union[int, Colour]] = COLOR,
        color: Optional[Union[int, Colour]] = COLOR,
        title: Optional[Any] = TITLE,
        type: EmbedType = 'rich',
        url: Optional[Any] = None,
        description: Optional[Any] = None,
        timestamp: Optional[datetime.datetime] = datetime.datetime.now(),
        footer: Optional[tuple[Optional[str], Optional[str]]] = FOOTER
        ):
        super().__init__(colour=colour, color=color, title=title, type=type, url=url, description=description, timestamp=timestamp)
        if footer:
            self.set_footer(text=footer[0], icon_url=footer[1])
        

    def set_color(self, color) -> "ReplyEmbed":
        self.color = color
        self.colour = color
        return self

    def set_description(self, description) -> "ReplyEmbed":
        self.description = description
        return self
