import json
import re
import requests
from datetime import datetime, timezone
from discord import Embed, Message
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from discord.ext.commands.bot import logging

URL_REGEX = r"https?://(?:www\.)?(?:[a-zA-Z0-9@:%._+~#=]{1,256}\.)(?:[a-zA-Z0-9()]{1,6})\b(?:[-a-zA-Z0-9()@:%_+.~#?&//=]*)"

COLOUR_SAPWOOD = 0xE8B693
DUMMY_URL = "https://example.com"

url_regex = re.compile(URL_REGEX)


def msg_embed(
    message: Message,
    author_title: str,
    message_title: str = "Message",
) -> list[Embed]:
    """
    refers to a user's message. supports attachemnts and links to twitter + other direct links to images
    """
    embeds: list[Embed] = []

    main = (
        Embed(
            color=COLOUR_SAPWOOD,  # TODO: change colour based on message type
            url=DUMMY_URL,
            timestamp=datetime.now(tz=timezone.utc),
        )
        .set_author(
            name=author_title,
            icon_url=message.author.display_avatar.url,
        )
        .set_footer(text=f"ID: {message.id}")
    )

    if message.content != "":
        main.add_field(name=message_title, value=message.content, inline=False)

    if message_title != "Deleted Message":  # FIXME: make this an enum or something
        main.add_field(name="Link", value=message.jump_url, inline=False)

    links: list[str] = url_regex.findall(message.content)
    attachments: list[str] = list(map(lambda x: x.url, message.attachments))  # ty:ignore[invalid-argument-type]

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

        case (False, True) | (True, True):
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
                return [url]

            obj = json.loads(r.text)
            urls: list[str] = list(
                map(lambda x: x["url"], obj["tweet"]["media"]["photos"])
            )

            return urls
        case "tenor.com":
            view_path = result.path

            # e.g https://tenor.com/buEMs.gif
            if result.path.endswith(".gif"):
                # redirect to view page
                r = requests.get(url)
                if r.status_code != 200:
                    logger.error(f"{r.status_code} from {url}")
                    return [url]

                view_path = r.url

            id = re.findall(r"/view/[^/?]+-(\d+)", view_path)
            if len(id) == 0:
                return [url]

            embed_url = f"https://tenor.com/embed/{id[0]}"

            r = requests.get(embed_url)
            if r.status_code != 200:
                logger.error(f"{r.status_code} from {embed_url}")
                return [url]

            soup = BeautifulSoup(r.text, "html.parser")
            element = soup.select_one("script#gif-json")

            if element is None:
                logger.error(f"no script#gif-json in {embed_url}")
                return [url]

            assert element.string is not None
            obj = json.loads(element.string)

            return [obj["media_formats"]["webp"]["url"]]

        case _:
            return [url]
