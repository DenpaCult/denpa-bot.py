import json
import logging
import re
from datetime import UTC, datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from discord import Client, Embed, Message
from discord.abc import Messageable

URL_REGEX = r"https?://(?:www\.)?(?:[a-zA-Z0-9@:%._+~#=]{1,256}\.)(?:[a-zA-Z0-9()]{1,6})\b(?:[-a-zA-Z0-9()@:%_+.~#?&//=]*)"

COLOUR_SAPWOOD = 0xE8B693
DUMMY_URL = "https://example.com"
REQUEST_TIMEOUT = 10  # seconds; these calls block the event loop

# pixiv + phixiv embed-fixer (plus c for compact)
PIXIV_HOSTS = {
    "pixiv.net",
    "www.pixiv.net",
    "phixiv.net",
    "www.phixiv.net",
    "c.phixiv.net",
    "ppxiv.net",
    "www.ppxiv.net",
    "c.ppxiv.net",
}

# just in case someone posts manga
PIXIV_MAX_PAGES = 4

url_regex = re.compile(URL_REGEX)


async def message_channel(client: Client, channel_id: int) -> Messageable | None:
    """
    If available, returns the message channel that corresponds to the channel_id.
    This may be a text channel, thread or discord's built-in voice text chat.
    """

    channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
    return channel if isinstance(channel, Messageable) else None


def msg_embed(
    message: Message,
    author_title: str,
    message_title: str = "Message",
    *,
    allow_nsfw: bool = False,
) -> list[Embed]:
    """
    refers to a user's message. supports attachemnts and links to twitter + other direct links to images

    allow_nsfw: embed images from sensitive tweets and R-18 (not R-18G) pixiv art
    """
    embeds: list[Embed] = []

    main = (
        Embed(
            color=COLOUR_SAPWOOD,  # TODO: change colour based on message type
            url=DUMMY_URL,
            timestamp=datetime.now(tz=UTC),
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
    attachments: list[str] = [x.url for x in message.attachments]

    # eg. a tweet with multiple images, only one can be the main image
    extra_img_urls = []

    match (
        len(links) > 0,
        len(attachments) > 0,
    ):
        case (True, False):
            img_urls = handle_link(links[0], allow_nsfw=allow_nsfw)
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
        img_urls = handle_link(link, allow_nsfw=allow_nsfw)

        for url in img_urls:
            embeds.append(Embed(url=DUMMY_URL).set_image(url=url))

    for url in attachments:
        embeds.append(Embed(url=DUMMY_URL).set_image(url=url))

    return embeds


def handle_link(url: str, *, allow_nsfw: bool = False) -> list[str]:
    try:
        return _resolve_link(url, allow_nsfw)
    except requests.RequestException as e:
        logging.getLogger("utils.cringe.handle_link").error(f"{e!r} for {url}")
        return [url]


def _fetch_json(api: str) -> dict | None:
    """GET a JSON API, logging and returning None on a non-200 or non-JSON reply"""
    logger = logging.getLogger("utils.cringe.handle_link")

    r = requests.get(api, timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        logger.error(f"{r.status_code} from {api}")
        return None

    # e.g. fxtwitter answers unknown tweet ids with a 200 HTML page
    try:
        obj = r.json()
    except ValueError:
        logger.error(f"non-JSON response from {api}")
        return None

    return obj if isinstance(obj, dict) else None


def _resolve_tweet(url: str, tweet_id: str, allow_nsfw: bool) -> list[str]:
    logger = logging.getLogger("utils.cringe.handle_link")

    obj = _fetch_json(f"https://api.fxtwitter.com/status/{tweet_id}")
    if obj is None:
        return [url]

    tweet = obj.get("tweet", {})

    if tweet.get("possibly_sensitive") and not allow_nsfw:
        logger.info(f"not embedding sensitive tweet {url}")
        return [url]

    # media will be {} on text-only tweets
    media = tweet.get("media", {})

    # collect all images
    urls: list[str] = [x["url"] for x in media.get("photos", [])]

    # collect all video thumbnails
    urls += [
        x["thumbnail_url"] for x in media.get("videos", []) if x.get("thumbnail_url")
    ]

    return urls or [url]

def _resolve_pixiv(url: str, art_id: str, allow_nsfw: bool) -> list[str]:
    logger = logging.getLogger("utils.cringe.handle_link")
    api = f"https://www.pixiv.net/ajax/illust/{art_id}"

    # deleted / nonexistent artworks are a 404
    info = _fetch_json(api)
    if info is None or info.get("error"):
        return [url]


    # TODO(kajo): enum?
    # 0 = all ages, 1 = R-18 (sexual), 2 = R-18G (gore)
    match (info.get("body") or {}).get("xRestrict", 0):
        case 0:
            return _pixiv_pages(url, art_id)

        # pixiv hides R-18 image urls from logged-out requests, but phixiv
        # (which is logged in) puts the first page in its embed's og:image
        case 1 if allow_nsfw:
            return _phixiv_og_image(url, art_id)

        case 1:
            logger.info(f"not embedding R-18 artwork {url}")
            return [url]

        # never embed gore, regardless of allow_nsfw
        case _:
            logger.info(f"not embedding R-18G artwork {url}")
            return [url]


def _pixiv_pages(url: str, art_id: str) -> list[str]:
    logger = logging.getLogger("utils.cringe.handle_link")
    api = f"https://www.pixiv.net/ajax/illust/{art_id}/pages"

    obj = _fetch_json(api)
    if obj is None:
        return [url]

    if obj.get("error"):
        logger.error(f"error from {api}: {obj.get('message')!r}")
        return [url]

    # i.pximg.net historically rejects requests without a pixiv Referer,
    # so serve the images through phixiv's proxy instead
    urls: list[str] = [
        page["urls"]["regular"].replace(
            "https://i.pximg.net/", "https://www.phixiv.net/i/", 1
        )
        for page in (obj.get("body") or [])[:PIXIV_MAX_PAGES]
        if page.get("urls", {}).get("regular")
    ]

    return urls or [url]


def _phixiv_og_image(url: str, art_id: str) -> list[str]:
    logger = logging.getLogger("utils.cringe.handle_link")
    embed_url = f"https://www.phixiv.net/artworks/{art_id}"

    r = requests.get(embed_url, timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        logger.error(f"{r.status_code} from {embed_url}")
        return [url]

    soup = BeautifulSoup(r.text, "html.parser")
    element = soup.select_one('meta[property="og:image"]')
    image = element.get("content") if element else None

    if not isinstance(image, str):
        logger.error(f"no og:image in {embed_url}")
        return [url]

    return [image]


def _resolve_link(url: str, allow_nsfw: bool) -> list[str]:
    logger = logging.getLogger("utils.cringe.handle_link")
    result = urlparse(url)

    # "/user/status/123/photo/1" -> ["user", "status", "123", "photo", "1"]
    segments = result.path.strip("/").split("/")

    match (result.netloc, segments):
        # x.com, twitter.com, and every fxtwitter-style clone share the same path
        # shape, so match on that
        case (_, [_, "status" | "statuses", tweet_id, *_]) if tweet_id.isdecimal():
            return _resolve_tweet(url, tweet_id, allow_nsfw)
        case (_, ["i", "web", "status", tweet_id, *_]) if tweet_id.isdecimal():
            return _resolve_tweet(url, tweet_id, allow_nsfw)

        # /artworks/<id> and /<lang>/artworks/<id>
        case (host, ["artworks", art_id, *_]) if host in PIXIV_HOSTS and art_id.isdecimal():
            return _resolve_pixiv(url, art_id, allow_nsfw)
        case (host, [_, "artworks", art_id, *_]) if host in PIXIV_HOSTS and art_id.isdecimal():
            return _resolve_pixiv(url, art_id, allow_nsfw)

        case ("tenor.com", _):
            view_path = result.path

            # e.g https://tenor.com/buEMs.gif
            if result.path.endswith(".gif"):
                # redirect to view page
                r = requests.get(url, timeout=REQUEST_TIMEOUT)
                if r.status_code != 200:
                    logger.error(f"{r.status_code} from {url}")
                    return [url]

                view_path = r.url

            id = re.findall(r"/view/[^/?]+-(\d+)", view_path)
            if len(id) == 0:
                return [url]

            embed_url = f"https://tenor.com/embed/{id[0]}"

            r = requests.get(embed_url, timeout=REQUEST_TIMEOUT)
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
