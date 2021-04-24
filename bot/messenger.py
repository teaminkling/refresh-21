"""Relays messages from the Discord API to local JSON files. Downloads all files."""

import json
import logging
import os
from logging import Logger
from typing import Any, Dict, List, Optional

import discord
from discord import Client, Message, User

# Initialise logging and include Discord SDK logs.

logger: Logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

# Constants.

MESSAGE_HISTORY_UPPER_LIMIT: int = 10000
"""An upper limit of the number of messages to retrieve."""

SUBMISSIONS_CHANNEL = "submissions"
"""The expected name of the channel with all submissions."""


def do_dump_all_messages():
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

        channel: Optional[Any] = discord.utils.get(
            client.get_all_channels(), name=SUBMISSIONS_CHANNEL
        )

        if not channel:
            raise RuntimeError(f"No channel named: [{SUBMISSIONS_CHANNEL}].")

        # Iterate through all messages in that channel and add to a JSON output.

        all_messages: List[Message] = await channel.history(
            limit=MESSAGE_HISTORY_UPPER_LIMIT
        ).flatten()

        message: Message
        for message in all_messages:
            created_timestamp: str = message.created_at.isoformat()
            author_with_discriminator: str = get_name_with_discriminator(message.author)

            data["users"].add(author_with_discriminator)

            # Save all attachments to disk and then reference it.

            attachments: List[Dict[str, str]] = []
            for attachment in message.attachments:
                author_directory: str = os.path.join("out", author_with_discriminator.lower())

                # Dynamic directory generation.

                if not os.path.exists(author_directory):
                    os.makedirs(author_directory)

                filename: str = f"{created_timestamp}+{attachment.filename}"
                local_path: str = os.path.join(author_directory, filename)

                with open(local_path, "wb") as attachment_file:
                    logger.info("Writing: [%s]...", local_path)

                    await attachment.save(attachment_file)

                attachments_map: dict = {
                    "id": attachment.id,
                    "cloud_url": attachment.url,
                    "local_url": local_path,
                    "filename": attachment.filename,
                    "type": attachment.content_type,
                }

                attachments.append(attachments_map)
                data["attachments"].append(attachments_map)

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
                    "content": message.content,
                    "attachments": attachments,
                }
            )

        # Write meta-information. Users to posts is not recorded here because of multi-posts; this
        # is handled in the parser instead.

        data["message_count"] = len(data["messages"])
        data["user_count"] = len(data["users"])
        data["attachment_count"] = len(data["attachments"])

        # Write to file.

        data["users"] = sorted(data["users"])

        with open("out/retrieved.json", "w") as json_file:
            json.dump(data, json_file, indent=2)

        await client.close()

    client.run("ODM1MTg3MzU2NDYxODI2MDk4.YILy1g.GC32acHsgcE203sXTV1Rqkph8Xc")


def get_name_with_discriminator(user: User) -> str:
    """Retrieve a name with discriminator from a user."""

    return f"{user.name}#{user.discriminator}"


if __name__ == "__main__":
    do_dump_all_messages()
