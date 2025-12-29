import json
import re
import requests
from datetime import datetime, timezone
from discord import Embed, Message
from urllib.parse import urlparse

from discord.ext.commands.bot import logging

URL_REGEX = r"https?://(?:www\.)?(?:[a-zA-Z0-9@:%._+~#=]{1,256}\.)(?:[a-zA-Z0-9()]{1,6})\b(?:[-a-zA-Z0-9()@:%_+.~#?&//=]*)"

TWITTER_REGEX = (
    r"https?:\/\/(?:www\.)?(twitter|x|fxtwitter|vxtwitter|fixupx|girlcockx)\.com"
)

COLOUR_SAPWOOD = 0xE8B693
DUMMY_URL = "https://example.com"

url_regex = re.compile(URL_REGEX)


def cringe_embed(message: Message) -> list[Embed]:
    embeds: list[Embed] = []

    main = (
        Embed(
            color=COLOUR_SAPWOOD,
            url=DUMMY_URL,
            timestamp=datetime.now(tz=timezone.utc),
        )
        .set_author(
            name=f"{message.author.name} posted cringe",
            icon_url=message.author.display_avatar.url,
        )
        .set_footer(text=f"ID: {message.id}")
    )

    if message.content != "":
        main.add_field(name="Message", value=message.content)

    main.add_field(name="Link", value=message.jump_url)

    links: list[str] = url_regex.findall(message.content)
    attachments: list[str] = list(map(lambda x: x.url, message.attachments))

    # eg. a tweet with multiple images, only one can be the main image
    extra_img_urls = []

    match (
        len(links) > 0,
        len(attachments) > 0,
    ):
        case (True, False):
            img_urls = handle_link(links[0])
            links = links[1::]  # remove the link that was just handled

            main.set_image(url=img_urls[0])
            extra_img_urls = img_urls[1::]

        case (False, True):
            main.set_image(url=attachments[0])
            attachments = attachments[1::]

        case (True, True):
            main.set_image(url=attachments[0])
            attachments = attachments[1::]
        case _:
            pass

    embeds.append(main)

    for url in extra_img_urls:
        embeds.append(Embed(url=DUMMY_URL).set_image(url=url))

    for link in links:
        img_urls = handle_link(link)

        for url in img_urls:
            embeds.append(Embed(url=DUMMY_URL).set_image(url=url))

    for url in attachments:
        embeds.append(Embed(url=DUMMY_URL).set_image(url=url))

    return embeds


def handle_link(url: str) -> list[str]:
    logger = logging.getLogger("utils.cringe.handle_link")
    result = urlparse(url)

    match result.netloc:
        # TODO: how many more of these things do dsd members use...
        case (
            "x.com"
            | "twitter.com"
            | "fixupx.com"
            | "fixvx.com"
            | "cunnyx.com"
            | "vxtwitter.com"
            | "fxtwitter.com"
            | "hotyurisex.com"
            | "girlcockx.com"
        ):
            api = result._replace(netloc="api.fxtwitter.com")

            r = requests.get(api.geturl())
            if r.status_code != 200:
                logger.error(f"{r.status_code} from {api.geturl()}")

            obj = json.loads(r.text)
            urls: list[str] = list(
                map(lambda x: x["url"], obj["tweet"]["media"]["photos"])
            )

            return urls
        case _:
            return [url]


def parse_message_into_embed(
    message: Message,
    color: int,
    author: tuple[str, str],
    footer: str,
    content_override: bool = False,
    extra_fields: list[tuple[str, str, bool]] = [],
) -> list[Embed]:
    """
    receives a message
    creates a main embed with color, author[name, icon_url], footer
    appends message.content to the main embed
    content_override: if True message.content wont be added to the embed and can be added manually through extra_fields
    extra_fields: array of (name, value, inline) tuples to define extra fields for the embed
    retreives all twitter,x,fx etc... hyperlinks from content
    and queries api.fxtwtiiter.com for valid image links
    creates additional embes with the links and returns a full list
    the embeds should combine because of the hack that was used in the original bot
            https://www.reddit.com/r/discordapp/comments/raz4kl/finally_a_way_to_display_multiple_images_in_an/
    TODO: i think there is a problem with some attachment/url combinations needs to be fixed
    TODO: remove the Link add field

    NEEDS TO BE TESTED !!!
    """

    main_embed = Embed(
        color=color,
        url="https://example.com",  # will this also work in python?
        timestamp=datetime.now(tz=timezone.utc),
    )
    main_embed.set_author(name=author[0], icon_url=author[1])
    main_embed.set_footer(text=footer)

    if message.content and not content_override:
        main_embed.add_field(name="Message", value=message.content, inline=False)

    for field in extra_fields:
        main_embed.add_field(name=field[0], value=field[1], inline=field[2])

    main_embed.add_field(
        name="Link", value=message.jump_url, inline=False
    )  # TODO: remove this and force outsiders to put it in extra_fileds

    hyperlinks = re.findall(URL_REGEX, message.content)

    if message.attachments:
        main_embed.set_image(url=message.attachments[0].url)

    embeds = [main_embed]

    media_urls = fetch_media_url(hyperlinks)

    for url in media_urls:
        _embed = Embed(url="https://example.com")
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
