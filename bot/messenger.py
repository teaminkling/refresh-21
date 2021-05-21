"""
Relays messages from the Discord API to local JSON files. Downloads all files.

Do not run this script on a pipeline.
"""

import json
import logging
import os
import subprocess
from hashlib import md5
from logging import Logger
from statistics import mean, median
from typing import Any, Dict, List, Optional, Union

import discord
from discord import Client, ClientUser, Member, Message, User
from PIL import Image, ImageSequence

# Initialise logging and include Discord SDK logs.

LOGGER: Logger = logging.getLogger(__name__)

# Constants.

CLIENT_SECRET_KEY: str = "CLIENT_SECRET"
"""The name of the environment variable used to feed to the Discord SDK."""

MESSAGE_HISTORY_UPPER_LIMIT: int = 10000
"""An upper limit of the number of messages to retrieve."""

SUBMISSIONS_CHANNEL: str = "submissions"
"""The expected name of the channel with all submissions."""

THUMBNAIL_MAX_WIDTH: int = 720
"""Pixel maximum width of a thumbnail."""

FORCE_GIF_THUMBNAIL_REGENERATION: bool = True
"""Whether to always regenerate the thumbnail image."""


def do_dump_all_messages():
    """Dump all messages from all connected Discord guilds."""

    # Create a closure that creates a Discord SDK client.

    client: Client = discord.Client()

    # Initialise raw data JSON-like mapping.

    data: dict = {
        "message_count": 0,
        "attachment_count": 0,
        "user_count": 0,
        "messages": [],
        "users": set(),
        "attachments": [],
    }

    @client.event
    async def on_ready() -> None:
        """
        As soon as the bot is ready, perform all parts of the algorithm.
        """

        channel: discord.channel.TextChannel = await connect_to_channel()
        all_messages: List[Message] = await channel.history(
            limit=MESSAGE_HISTORY_UPPER_LIMIT,
        ).flatten()

        LOGGER.info("Starting iteration through all messages...")

        for message in all_messages:
            await process_message(message)

        await write_meta_information()
        await write_retrieved_file()

        await client.close()

    async def write_retrieved_file():
        # Write to file.

        LOGGER.info("Sorting [%d] users...", data["user_count"])
        data["users"] = sorted(list(data["users"]))

        LOGGER.info("Writing retrieved.json file...")
        with open("out/retrieved.json", "w") as json_file:
            json.dump(data, json_file, indent=2)

        LOGGER.info("Done with Discord, closing client!")

    async def connect_to_channel() -> discord.channel.TextChannel:
        LOGGER.info("Connecting to [%s] channel...", SUBMISSIONS_CHANNEL)
        channel: Optional[Any] = discord.utils.get(
            client.get_all_channels(),
            name=SUBMISSIONS_CHANNEL,
        )

        if not isinstance(channel, discord.channel.TextChannel):
            raise RuntimeError(f"No channel named: [{SUBMISSIONS_CHANNEL}].")

        return channel

    async def write_meta_information():
        # Write meta-information. Users to posts is not recorded here because of multi-posts; this
        # is handled in the parser instead.

        data["message_count"] = len(data["messages"])
        data["user_count"] = len(data["users"])
        data["attachment_count"] = len(data["attachments"])

        LOGGER.info(
            "Finished writing all [%d] attachments and [%d] messages!",
            data["attachment_count"],
            data["message_count"],
        )

    async def process_message(message):
        created_timestamp: str = message.created_at.isoformat()

        # Add user to the user set, remembering their name. This name may contain unicode or
        # difficult-to-parse symbols and should be cleaned in the parser.

        author_with_discriminator: str = get_name_with_discriminator(message.author)
        data["users"].add(author_with_discriminator)

        # Save all attachments to disk and generate a thumbnail.

        attachments = await extract_media(
            author_with_discriminator, created_timestamp, message
        )

        # Replace mentions with direct @Username references.

        content: str = message.content
        mention: Union[User, Member, ClientUser]

        for mention in message.mentions:
            content = content.replace(f"<@!{mention.id}>", f"@{mention.name}")
            content = content.replace(mention.mention, f"@{mention.name}")

        data["messages"].append(
            {
                "id": message.id,
                "permalink": message.jump_url,
                "created_at": created_timestamp,
                "author": {
                    "id": message.author.id,
                    "display_name": message.author.name,
                    "mention_name": author_with_discriminator,
                },
                "content": content,
                "attachments": attachments,
            }
        )

    async def extract_media(author_with_discriminator, created_timestamp, message):
        LOGGER.debug(
            "Writing attachments for user: [%s] with post created at [%s]...",
            author_with_discriminator,
            created_timestamp,
        )

        attachments: List[Dict[str, str]] = []
        for attachment in message.attachments:
            author_directory: str = os.path.join(
                "../static/img",
                message.author.name.encode("ascii", "ignore")
                .decode()
                .lower()
                .replace(" ", "_")
                .replace("(", "")
                .replace(")", ""),
            )

            # Dynamic directory generation.

            if not os.path.exists(author_directory):
                os.makedirs(author_directory)

            # Save the file locally. If it already exists, skip.

            filename: str = (
                f"{message.created_at.date().isoformat()}+"
                f"{md5(attachment.filename.encode()).hexdigest()[:8]}"
            )

            extension: str = attachment.filename.split(".")[-1].lower()
            local_path: str = os.path.join(author_directory, f"{filename}.{extension}")
            local_thumb_path: str = os.path.join(
                author_directory,
                f"{filename}-thumbnail-w{THUMBNAIL_MAX_WIDTH}px.{extension}",
            )

            if not os.path.exists(local_path):
                with open(local_path, "wb") as attachment_file:
                    LOGGER.info("Writing: [%s]...", local_path)

                    await attachment.save(attachment_file)
            else:
                LOGGER.debug("Exists, skipping: [%s]...", local_path)

            # Add a thumbnail if applicable.

            if (
                not os.path.exists(local_thumb_path)
                or FORCE_GIF_THUMBNAIL_REGENERATION
                and extension == "gif"
            ) and extension in (
                "png",
                "jpg",
                "jpeg",
                "gif",
            ):
                LOGGER.info("Writing thumbnail: [%s]...", local_thumb_path)

                image: Image = Image.open(local_path)

                # If the image is big enough, don't compress the size.

                width_percent: float = THUMBNAIL_MAX_WIDTH / float(image.size[0])
                if image.size[0] <= THUMBNAIL_MAX_WIDTH:
                    width_percent = 1.0

                height: int = int(image.size[1] * width_percent)

                if extension == "gif":
                    frames: List[Image] = []

                    for frame in ImageSequence.Iterator(image):
                        gif_thumbnail: Image = frame.copy()
                        gif_thumbnail.thumbnail(
                            (THUMBNAIL_MAX_WIDTH, height), Image.ANTIALIAS
                        )

                        frames.append(gif_thumbnail)

                    # Save output.

                    output_gif: Image = frames[0]

                    output_gif.info = image.info
                    output_gif.info["duration"] = [frame.info["duration"] for frame in frames]

                    output_gif.save(
                        local_thumb_path,
                        save_all=True,
                        format=image.format,
                        append_images=list(frames)[1:],
                        optimize=True,
                        loop=0,
                    )
                else:
                    image.thumbnail((THUMBNAIL_MAX_WIDTH, height))
                    image.save(local_thumb_path)

            local_thumb_path = (
                local_thumb_path if os.path.exists(local_thumb_path) else None
            )

            # If the file is .mov we need to open a subprocess to convert it.

            mp4_local_path = local_path.replace(".mov", ".mp4")
            if extension == "mov" and not os.path.exists(mp4_local_path):
                LOGGER.info("Converting a .mov to .mp4: [%s].", filename)

                # Will hang if file already exists.

                subprocess.call(["ffmpeg", "-i", local_path, mp4_local_path])

                local_path = mp4_local_path

            attachments_map: dict = {
                "id": attachment.id,
                "cloud_url": attachment.url,
                "url": local_path,
                "thumbnail_url": local_thumb_path,
                "filename": attachment.filename,
                "type": attachment.content_type,
            }

            attachments.append(attachments_map)
            data["attachments"].append(attachments_map)

        return attachments

    client.run(os.environ.get(CLIENT_SECRET_KEY))


def get_name_with_discriminator(user: Union[User, Member]) -> str:
    """
    Retrieve a name with discriminator from a user.

    Parameters
    ----------
    user : `Union[User, Member]`
        The `User` or `Member` whose name will be extracted.

    Returns
    -------
    `str`
        A username with a discriminator separated by a "#" symbol.
    """

    return f"{user.name}#{user.discriminator}"


if __name__ == "__main__":
    # Set up logger.

    logging.basicConfig(level=logging.INFO)
    log_formatter: logging.Formatter = logging.Formatter(
        "(%(asctime)s) [%(levelname)s]: %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    stream_handler: logging.StreamHandler = logging.StreamHandler()

    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(log_formatter)

    logging.root.handlers.clear()

    LOGGER.addHandler(stream_handler)

    do_dump_all_messages()
