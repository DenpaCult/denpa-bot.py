from datetime import datetime, timezone
from discord import Embed, Message
import re
from discord.ext.commands.bot import logging
import requests

URL_REGEX = r"https?://(?:www\.)?(?:[a-zA-Z0-9@:%._+~#=]{1,256}\.)(?:[a-zA-Z0-9()]{1,6})\b(?:[-a-zA-Z0-9()@:%_+.~#?&//=]*)"

TWITTER_REGEX = r"https?:\/\/(?:www\.)?(twitter|x|fxtwitter|vxtwitter|fixupx|girlcockx)\.com"


def parse_message_into_embed(message: Message, color: int, author: tuple[str,str], footer: str) -> list[Embed]:
    """
    receives a message
    creates a main embed with color, author[name, icon_url], footer
    appends message.content to the main embed
    retreives all twitter,x,fx etc... hyperlinks from content
    and queries api.fxtwtiiter.com for valid image links
    creates additional embes with the links and returns a full list
    the embeds should combine because of the hack that was used in the original bot
            https://www.reddit.com/r/discordapp/comments/raz4kl/finally_a_way_to_display_multiple_images_in_an/
    TODO: i think there is a problem with some attachment/url combinations needs to be fixed

    NEEDS TO BE TESTED !!!
    """
    
    main_embed = Embed(
            color=color, 
            url="https://example.com", # will this also work in python?
            timestamp=datetime.now(tz=timezone.utc)
            )
    main_embed.set_author(name=author[0], icon_url=author[1])
    main_embed.set_footer(text=footer)

    if message.content:
        main_embed.add_field(name="Message", value=message.content, inline=False)

    main_embed.add_field(name="Link", value=message.jump_url, inline=False)

    hyperlinks = re.findall(URL_REGEX, message.content)


    if message.attachments:
        main_embed.set_image(url=message.attachments[0].url)

    embeds = [main_embed]

    media_urls = fetch_media_url(hyperlinks)

    for url in media_urls:
        _embed = Embed(
            url="https://example.com"
            )
        _embed.set_image(url=url)
        embeds.append(_embed)

    return embeds


def fetch_media_url(hyperlinks: list[str]) -> list[str]:
    """
    receives list of hyperlinks
    returns a list of fxtwitter media urls
    """
    photo_urls = []
    for link in hyperlinks:
        if not re.match(TWITTER_REGEX, link):
            continue

        link = re.sub(TWITTER_REGEX, "https://api.fxtwitter.com", link)
        _json = requests.get(link).json()

        try:
            photo_urls += list(map(lambda x: x["url"], _json["tweet"]["media"]["all"]))
        except:
            pass

    return photo_urls

