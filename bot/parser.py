"""Parses local text files and translates them into a JSON object."""

import json
import logging
import re
from logging import Logger
from typing import Any, Dict, List, Pattern, Tuple

# Initialise logging.

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

WEEK_PARSING_REGEX: Pattern = re.compile(
    (
        r"(?P<preamble>[\s\S]*?)"
        r"(?:[Ww]eek)(?!-)(?:.*?)"
        r"(?P<week>[0-9]+|One)(?:.*)"
        r"(?:[\s])(?P<remainder>[\S\s]+?)"
        r"(?:(?<!title: )"
        r"(?=[Ww]eek.*[0-9]+)"
        r"(?!week-)|(?:\Z))"
    ),
    flags=re.MULTILINE | re.IGNORECASE,
)
"""
A complex parsing regex that retrieves, in one content string, matches where each match is the 
entire body of a weekly submission where there is a group that takes the integer week value and the
preamble and remainder of the content to be parsed for optional values.

Note that this can't handle one post for multiple submissions if there are attachments.
"""

TITLE_PARSING_REGEX: Pattern = re.compile(
    r"(?P<preamble>[\s\S]*?)(?:title[:\-* ]+)(?P<title>.*$)(?P<remainder>[\s\S]*)",
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex that retrieves a title if applicable."""

MEDIUM_PARSING_REGEX: Pattern = re.compile(
    (
        r"(?P<preamble>[\s\S]*?)"
        r"(?<!social )"
        r"(?:medi(?:(?:um)|a)[:\-*]*[\s]+)"
        r"(?P<medium>.*$)"
        r"(?P<remainder>[\s\S]*)"
    ),
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex that retrieves a title if applicable."""

RAW_SOCIAL_PARSING_REGEX: Pattern = re.compile(
    (
        r"(?P<preamble>[\s\S]*?)"
        r"(?i)(?P<raw_socials>social(?:s|(?: media))?[:\-*]*[\s]+)"
        r"(?P<remainder>[\s\S]*)"
    ),
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex that splits text into preamble and remainder after the socials marker."""

TEMPLATE_BEGINNING: str = "**Submission Template**"
"""The start of the template post which gets ignored."""


def parse_retrieved() -> None:
    """
    Parse raw messages retrieved previously from Discord.

    This function should not be called from a pipeline.

    Algorithm:

    1. Join messages sequentially posted by the same poster together into one mapping.
    2. Parse that mapping's description content and search for the week, splitting into an object
       where the keys are the user and the week.

       Multiple submissions in one week are still considered one submission.
    3. Find all social links and associate with the user's "blob" information.
    4. Find all content URLs and add to a URL list for each submission.
    5. For each user, parse their socials and save them in a tabular format.
    6. For each submission, parse their URLs and save them in a tabular format.
    7. Write users and submissions to output JSON file.
    """

    final_data: dict = {
        "users": {},
        "submissions": [],
    }

    with open("out/retrieved.json") as retrieved_file:
        retrieved_data: dict = json.load(retrieved_file)

    # Keep certain information over from the retrieved data.

    final_data["user_count"] = retrieved_data["user_count"]

    # Parse matches and add them to a mapping of "author: week".

    message: Dict[str, Any]
    for message in parse_cumulative_messages(retrieved_data):
        author: str = message["author"]
        content: str = message["message"]
        attachments: List[str] = message["attachments"]

        final_data["submissions"].extend(extract_all_content(content, author, attachments))

    # Write final data before we start to write blog posts and pages.

    final_data["submission_count"] = len(final_data["submissions"])

    with open("out/parsed.json", "w") as json_output_file:
        json.dump(final_data, json_output_file, indent=2)


def parse_cumulative_messages(retrieved_data: dict) -> List[dict]:
    """
    Parse cumulative messages by order of created (ascending) and join them together if sequential.

    Parameters
    ----------
    retrieved_data : `dict`
        The contents of the `retrieved.json` file.

    Returns
    -------
    `List[dict]`
        A list of cumulative `dict`s.
    """

    joined_messages: List[dict] = []

    # Combine all of the consecutive messages together.

    cumulative_message: str = ""
    cumulative_attachments: List[str] = []
    author: str = ""
    last_author: str = ""

    for message in reversed(retrieved_data["messages"]):
        author: str = message["author"]["mention_name"]
        attachments: List[str] = [
            attachment["local_url"] for attachment in message["attachments"]
        ]

        if author == last_author or not last_author:
            cumulative_message += message["content"]
            cumulative_attachments.extend(attachments)
        else:
            joined_messages.append(
                {
                    "message": cumulative_message,
                    "attachments": cumulative_attachments,
                    "author": last_author,
                }
            )

            cumulative_message = message["content"]
            cumulative_attachments = attachments

        last_author = author

    # Write the very last entry.

    if author:
        joined_messages.append(
            {
                "message": cumulative_message,
                "attachments": cumulative_attachments,
                "author": author,
            }
        )

    return joined_messages


def extract_all_content(content: str, author: str, attachments: List[str]) -> List[dict]:
    # Don't bother extracting if it's the template message.

    if content.startswith(TEMPLATE_BEGINNING):
        return []

    # Find all matches otherwise.

    matches: List[Tuple[str, str, str]] = re.findall(WEEK_PARSING_REGEX, content)

    if not matches:
        LOGGER.warning("No [week]s found for content over next line:\n\n%s\n", content)

        return []

    content_data: List[dict] = []

    for match in matches:
        # Initialise what may be found from the parsers. Note that week is the only mandatory value
        # and is parsed separately (and first) from the other values.

        week: int
        title: str
        medium: str
        description: str

        # Socials are special: list of provider to URL/username.

        socials: List[Tuple[str, str]] = []

        # Weeks may have an exception where a week is written as "one" instead of "1".

        if match[1].lower() == "one":
            week = 1
        else:
            week = int(match[1])

        # Parse the remainder and preamble. This code here kinda sucks but so does the regex,
        # so whatever. The amount of content is fixed (not dynamic) so there's no point iterating.

        preamble: str = match[0]
        remainder: str = match[2]

        # Remove bolds.

        preamble = re.sub(r"\*\*(?P<unformatted>.*)\*\*", r"\g<unformatted>", preamble)
        remainder = re.sub(r"\*\*(?P<unformatted>.*)\*\*", r"\g<unformatted>", remainder)

        # Remove italics.

        preamble = re.sub(r"_(?P<unformatted>.*)_", r"\g<unformatted>", preamble)
        remainder = re.sub(r"_(?P<unformatted>.*)_", r"\g<unformatted>", remainder)
        preamble = re.sub(r"\*(?P<unformatted>.*)\*", r"\g<unformatted>", preamble)
        remainder = re.sub(r"\*(?P<unformatted>.*)\*", r"\g<unformatted>", remainder)

        # Remove underlines.

        preamble = re.sub(r"__(?P<unformatted>.*)__", r"\g<unformatted>", preamble)
        remainder = re.sub(r"__(?P<unformatted>.*)__", r"\g<unformatted>", remainder)

        # Start to parse content.

        preamble, title, remainder = parse_content(
            text=f"{preamble}\n{remainder}",
            pattern=TITLE_PARSING_REGEX,
            parse_type="title",
        )

        preamble, medium, remainder = parse_content(
            text=f"{preamble}\n{remainder}",
            pattern=MEDIUM_PARSING_REGEX,
            parse_type="medium",
        )

        # Description and socials are dynamic. We need to intelligently parse them. This is a
        # complex algorithm:

        # 1. Have the part before social indicator as a chunk of text before socials.
        # 2. The second part has socials somewhere after it, but there may be other information.
        # 3. From the information after socials, pick up Instagram, Spotify, Twitter, etc.
        # 4. Retrieve these but then remove it from the chunk after socials.
        # 5. Combine the before and after chunks together.
        # 6. Format and remove description and social labels.
        # 7. Add as Description for this work.

        preamble, raw_socials, remainder = parse_content(
            text=f"{preamble}\n{remainder}",
            pattern=RAW_SOCIAL_PARSING_REGEX,
            parse_type="raw_socials",
        )

        if raw_socials:
            socials, remainder = parse_socials(remainder)

        dynamic_content: str = f"{preamble}\n{remainder}".strip()
        dynamic_content = re.sub(r"\n{3,}", "\n\n", dynamic_content)
        dynamic_content = re.sub(r"(?i:description)[: -]*", "", dynamic_content)

        # Note that further processing may be done later in dedicated code for making things look
        # better. It does not need to happen here but we partially clean it because we can.

        description = re.sub(r"(?i:social[s]?(?: media)?)[: -]*", "", dynamic_content)

        # If there's no week, we can't form an ID.

        content_data.append({
            "author": author,
            "week": week,
            "title": title.strip(),
            "medium": medium.strip(),
            "description": description.strip(),
            "attachments": attachments,
            "socials": socials,
        })

        # TODO: unexpected no medium/description/title/socials: handle it.

    return content_data


def parse_content(text: str, pattern: Pattern, parse_type: str) -> Tuple[str, str, str]:
    """
    Using a regular expression, parse something as a preamble, extraction, and remainder.

    Parameters
    ----------
    text : `str`
        The text to parse.

    pattern : `Pattern`
        The pattern which is used to parse and must have three group returns.

    parse_type : `str`
        The parse type used for logging.

    Returns
    -------
    `Tuple[str, str, str]`
        A preamble, extraction, and remainder.
    """

    text = text.strip()

    matches: List[Tuple[str, str, str]] = re.findall(pattern, text)

    if not matches:
        LOGGER.info("No [%s]s found for content over next line:\n\n%s\n", parse_type, text)

        return "", "", text
    elif len(matches) > 1:
        LOGGER.info(
            "Multiple [%s]s found for content over next line:\n\n%s\n", parse_type, text,
        )

    return matches[0][0], matches[0][1], matches[0][2]


def parse_socials(text: str) -> Tuple[List[Dict[str, str]], str]:
    """
    Parse social links and references to tags on popular social media websites.

    Parameters
    ----------
    text :

    Returns
    -------
    `Tuple[List[Dict[str, str]], str]`
        A `tuple` of the socials found (which is a mapping of provider to username) and the
        remainder of the content which was not parsed, if applicable, to be added back to the
        description to be formatted.
    """

    # TODO: Implement.

    return [{"Test": text}], text


if __name__ == "__main__":
    parse_retrieved()
