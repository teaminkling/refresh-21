"""
Relays messages from the Discord API to local JSON files. Downloads all files.

Do not run this script on a pipeline.
"""

import json
import logging
import os
from hashlib import md5
from logging import Logger
from typing import Any, Dict, List, Optional

import discord
from discord import Client, Message, User

# Initialise logging and include Discord SDK logs.

LOGGER: Logger = logging.getLogger(__name__)

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

# Constants.

CLIENT_SECRET_KEY: str = "CLIENT_SECRET"
"""The name of the environment variable used to feed to the Discord SDK."""

MESSAGE_HISTORY_UPPER_LIMIT: int = 10000
"""An upper limit of the number of messages to retrieve."""

SUBMISSIONS_CHANNEL = "submissions"
"""The expected name of the channel with all submissions."""


def do_dump_all_messages():
    """Dump all messages from all connected Discord guilds."""

    # Create a closure that creates a Discord SDK client.

    client: Client = discord.Client()

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
        As soon as the bot is ready, retrieve all messages.
        """

        # Find a channel named "submissions" in the connected guild(s):

        LOGGER.info("Connecting to channel...")

        channel: Optional[Any] = discord.utils.get(
            client.get_all_channels(), name=SUBMISSIONS_CHANNEL
        )

        if not channel:
            raise RuntimeError(f"No channel named: [{SUBMISSIONS_CHANNEL}].")

        # Iterate through all messages in that channel and add to a JSON output.

        all_messages: List[Message] = await channel.history(
            limit=MESSAGE_HISTORY_UPPER_LIMIT
        ).flatten()

        LOGGER.info("Writing attachments and messages...")

        message: Message
        for message in all_messages:
            created_timestamp: str = message.created_at.isoformat()
            author_with_discriminator: str = get_name_with_discriminator(message.author)

            data["users"].add(author_with_discriminator)

            # Save all attachments to disk and then reference it.

            LOGGER.debug(
                "Writing attachments for user: [%s]...",
                author_with_discriminator,
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
                    f"{md5(attachment.filename.encode()).hexdigest()}"
                )

                extension: str = attachment.filename.split(".")[-1]

                local_path: str = os.path.join(
                    author_directory, f"{filename}.{extension}"
                )

                if not os.path.exists(local_path):
                    with open(local_path, "wb") as attachment_file:
                        LOGGER.info("Writing: [%s]...", local_path)

                        await attachment.save(attachment_file)
                else:
                    LOGGER.debug("Exists, skipping: [%s]...", local_path)

                attachments_map: dict = {
                    "id": attachment.id,
                    "cloud_url": attachment.url,
                    "local_url": local_path,
                    "filename": attachment.filename,
                    "type": attachment.content_type,
                }

                attachments.append(attachments_map)
                data["attachments"].append(attachments_map)

            # Replace mentions with direct @Username references.

            content: str = message.content

            mention: User
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

        # Write to file.

        LOGGER.info("Sorting [%d] users...", data["user_count"])

        data["users"] = sorted(list(data["users"]))

        LOGGER.info("Writing retrieved.json file...")

        with open("out/retrieved.json", "w") as json_file:
            json.dump(data, json_file, indent=2)

        LOGGER.info("Done with Discord, closing client!")

        await client.close()

    client.run(os.environ.get(CLIENT_SECRET_KEY))


def get_name_with_discriminator(user: User) -> str:
    """
    Retrieve a name with discriminator from a user.

    Parameters
    ----------
    user : `User`
        The `User` whose name we want.

    Returns
    -------
    `str`
        A username with a discriminator separated by a "#" symbol.
    """

    return f"{user.name}#{user.discriminator}"


if __name__ == "__main__":
    do_dump_all_messages()
