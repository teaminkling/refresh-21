"""
Relays messages from the Discord API to local JSON files. Downloads all files.

Do not run this script on a pipeline.
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import time, timedelta
from hashlib import md5
from logging import Logger
from typing import Any, Collection, Dict, List, Optional, Union

import discord
from discord import Attachment, Client, ClientUser, Member, Message, User
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

PIL_THUMBNAIL_TYPES: Collection[str] = (
    "png",
    "jpg",
    "jpeg",
    "gif",
)

FORCE_GIF_THUMBNAIL_REGENERATION: bool = True
"""Whether to always regenerate the thumbnail image."""


@dataclass
class MediaFile:
    """A file extracted from Discord."""

    author_directory: str
    """The author (category) directory in img/ the file will be saved to."""

    filename: str
    """The filename with extension."""

    extension: str
    """The file extension."""

    _has_thumbnail: bool
    """Whether the thumbnail has been processed yet."""

    def __init__(
        self, author: Union[User, Member], message: Message, attachment: Attachment
    ):
        self.author_directory = self._compute_author_directory(author)
        self.filename = self._compute_filename(message, attachment)
        self.extension = self._compute_extension(attachment)

        self._has_thumbnail = False

    @property
    def local_path(self) -> str:
        """
        Returns
        -------
        `str`
            The local location on disk from where the cloud attachment will be saved.
        """

        return os.path.join(self.author_directory, f"{self.filename}.{self.extension}")

    @property
    def thumb_extension(self) -> str:
        return "jpg" if self.extension == "mp4" else self.extension

    @property
    def local_thumb_path(self) -> Optional[str]:
        if not self._has_thumbnail:
            return

        thumbnail_filename: str = (
            f"{self.filename}-thumb-w{THUMBNAIL_MAX_WIDTH}px.{self.thumb_extension}"
        )

        return os.path.join(self.author_directory, thumbnail_filename)

    async def save(self, attachment: Attachment) -> None:
        """
        Write an `Attachment` to disk if needed (forcing depending on configuration).

        Parameters
        ----------
        attachment : `Attachment`
            The attachment to save to disk.
        """

        if not os.path.exists(self.author_directory):
            os.makedirs(self.author_directory)

        if not os.path.exists(self.local_path):
            with open(self.local_path, "wb") as attachment_file:
                LOGGER.info("Writing: [%s]...", self.local_path)

                await attachment.save(attachment_file)
        else:
            LOGGER.debug("Exists, skipping: [%s]...", self.local_path)

        # Not done. Needs to save again if the video file is supported.

        if self.extension == "mov":
            self._convert_video()

        # Lastly, generate a thumbnail for this image.

        self._generate_thumbnail()

    def _convert_video(self) -> None:
        """
        Convert supported alternative video formats to `.mp4` using `ffmpeg`.

        Returns
        -------
        `str`
            The path to the file presented in the local path. This may be unchanged.
        """

        mp4_local_path = self.local_path.replace(".mov", ".mp4")
        if not os.path.exists(mp4_local_path):
            LOGGER.info("Converting a .mov to .mp4: [%s].", self.local_path)

            # Will hang if file already exists.

            subprocess.call(["ffmpeg", "-i", self.local_path, mp4_local_path])

            self.extension = "mp4"

    def _generate_thumbnail(self) -> None:
        self._has_thumbnail = True

        thumbnail_exists: bool = os.path.exists(self.local_thumb_path)
        force: bool = FORCE_GIF_THUMBNAIL_REGENERATION and self.extension == "gif"

        if not thumbnail_exists or force:
            if self.extension in PIL_THUMBNAIL_TYPES:
                LOGGER.info("Writing thumbnail: [%s]...", self.local_thumb_path)

                # Open the original image.

                image: Image = Image.open(self.local_path)

                # If the image is big enough, don't compress the size.

                width_percent: float = THUMBNAIL_MAX_WIDTH / float(image.size[0])
                if image.size[0] <= THUMBNAIL_MAX_WIDTH:
                    width_percent = 1.0

                height: int = int(image.size[1] * width_percent)

                # Handle gifs separately to images and videos.

                if self.extension == "gif":
                    self._make_gif_thumbnail(height, image)
                else:
                    image.thumbnail((THUMBNAIL_MAX_WIDTH, height))
                    image.save(self.local_thumb_path)
            elif self.extension == "mp4":
                self._make_mp4_thumbnail()
            else:
                self._has_thumbnail = False

    def _make_gif_thumbnail(self, height, image):
        frames: List[Image] = []

        for frame in ImageSequence.Iterator(image):
            gif_thumbnail: Image = frame.copy()
            gif_thumbnail.thumbnail((THUMBNAIL_MAX_WIDTH, height), Image.ANTIALIAS)

            frames.append(gif_thumbnail)

        # Save output.

        output_gif: Image = frames[0]

        output_gif.info = image.info
        output_gif.info["duration"] = [frame.info["duration"] for frame in frames]

        output_gif.save(
            self.local_thumb_path,
            save_all=True,
            format=image.format,
            append_images=list(frames)[1:],
            optimize=True,
            loop=0,
        )

    def _make_mp4_thumbnail(self):
        # First we need to know the duration of the video.

        ffprobe_output = subprocess.check_output(
            f'ffprobe -v quiet -show_streams -select_streams v:0 -of json "{self.local_path}"',
            shell=True,
        ).decode()

        # Allow failure; expect total success.

        stream_info: dict = json.loads(ffprobe_output)["streams"][0]
        duration: float = float(stream_info["duration"])

        # Now, get the time halfway through the video and immediately save it.

        midway_time: timedelta = timedelta(seconds=duration / 2)
        subprocess.call(
            [
                "ffmpeg",
                "-i",
                self.local_path,
                "-ss",
                str(midway_time),
                "-vframes",
                "1",
                self.local_thumb_path,
            ]
        )

    @staticmethod
    def _compute_author_directory(author: Union[User, Member]):
        """
        Clean up an author's name

        Parameters
        ----------
        author : `Union[User, Member]`
            The poster of a particular `Message`.

        Returns
        -------
        `str`
            The directory in which this author's files will be placed.
        """

        # Get rid of non-ASCII characters in names.

        cleaned_author: str = author.name.encode("ascii", "ignore").decode().lower()

        # These are not supported by URL paths, so we strip them out.

        cleaned_author = (
            cleaned_author.replace(" ", "_").replace("(", "").replace(")", "")
        )

        return os.path.join("../static/img", cleaned_author)

    @staticmethod
    def _compute_filename(message: Message, attachment: Attachment):
        return (
            f"{message.created_at.date().isoformat()}+"
            f"{md5(attachment.filename.encode()).hexdigest()[:8]}"
        )

    @staticmethod
    def _compute_extension(attachment: Attachment):
        return attachment.filename.split(".")[-1].lower()


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

        LOGGER.debug("Starting iteration through all messages...")

        message: Message
        for message in all_messages:
            await process_message(message)

        await write_meta_information()
        await write_retrieved_file()

        await client.close()

    async def write_retrieved_file():
        # Write to file.

        LOGGER.debug("Sorting [%d] users...", data["user_count"])
        data["users"] = sorted(list(data["users"]))

        LOGGER.debug("Writing retrieved.json file...")
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

    async def process_message(message: Message):
        created_timestamp: str = message.created_at.isoformat()

        # Add user to the user set, remembering their name. This name may contain unicode or
        # difficult-to-parse symbols and should be cleaned in the parser.

        author_with_discriminator: str = get_name_with_discriminator(message.author)
        data["users"].add(author_with_discriminator)

        # Save all attachments to disk and generate a thumbnail.

        attachments: List[Dict[str, str]] = await extract_media(message.author, message)

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

    async def extract_media(
        author: Union[User, Member], message: Message
    ) -> List[Dict[str, str]]:
        """
        Extract media from Discord and save it.

        Parameters
        ----------
        author : `Union[User, Member]`
            An author of the post this media is for.

        message : `Message`
            The message from which to extract.

        Returns
        -------
        `List[Dict[str, str]]`
            A list of attachment meta objects. Each object has elements like "id", "cloud_url",
            and, most importantly, both "url" and "thumbnail_url".
        """

        LOGGER.debug(
            "Writing attachments. User: [%s], posted at: [%s]...",
            author,
            message.created_at,
        )

        attachments: List[Dict[str, str]] = []

        attachment: Attachment
        for attachment in message.attachments:
            media_file: MediaFile = MediaFile(
                author=author, message=message, attachment=attachment
            )

            # Save the file and thumbnail if required/forced.

            await media_file.save(attachment)

            attachments_map: dict = {
                "id": attachment.id,
                "cloud_url": attachment.url,
                "url": media_file.local_path,
                "thumbnail_url": media_file.local_thumb_path,
                "filename": attachment.filename,
                "type": attachment.content_type,
            }

            # Append to the overall attachments map (meta-information) and this post's map.

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
