"""Parses local text files and translates them into a JSON object."""

import json
import logging
import re
from logging import Logger
from typing import Any, Dict, List, Optional, Pattern, TextIO, Tuple, Union

# Initialise logging.

LOGGER: Logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.WARNING)
log_formatter: logging.Formatter = logging.Formatter(
    "(%(asctime)s) [%(levelname)s]: %(message)s",
    "%Y-%m-%d %H:%M:%S",
)

stream_handler: logging.StreamHandler = logging.StreamHandler()

stream_handler.setLevel(logging.WARNING)
stream_handler.setFormatter(log_formatter)

logging.root.handlers.clear()

LOGGER.addHandler(stream_handler)

# Constants.

WEEK_PARSING_REGEX: Pattern = re.compile(
    (
        r"(?P<preamble>[\s\S]*?)(?<!my )(?<!for )(?:week)(?!-)(?:.{0,16})(?P<week>[0-9]+|One)"
        r"(?:.*)(?:[\s])(?P<remainder>[\S\s]+?)(?:(?<!title: )(?=week.{1,16}?[0-9]+)"
        r"(?!week-)(?!week \d+[ ,])|(?:\Z))"
    ),
    flags=re.MULTILINE | re.IGNORECASE,
)
"""
A complex parsing regex that retrieves, in one content string, matches where each match is the 
entire body of a weekly submission where there is a group that takes the integer week value and the
preamble and remainder of the content to be parsed for optional values.

Note that this can't handle one post for multiple submissions if there are attachments.
"""

with open("in/replacements.json") as replacements_json_file:
    REPLACEMENTS_AND_EXPECTED_MISSING_MAP: dict = json.load(replacements_json_file)
    """
    A map containing replacements and expected missing values for invalid submissions.
    
    Note that this is pre-processing. If the parser got something wrong or the formatting just 
    wasn't very good for the final blog post, I suggest using the `formatting.json` file instead.
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
        r"(?:medi(?:(?:um)|a)[,:\-*]*[\s]+)"
        r"(?P<medium>.*$)"
        r"(?P<remainder>[\s\S]*)"
    ),
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex that retrieves a title if applicable."""

RAW_SOCIAL_PARSING_REGEX: Pattern = re.compile(
    (
        r"(?P<preamble>[\s\S]*?)"
        r"(?P<raw_socials>social(?:s|(?: media))?[:\-*]*[\s]+)"
        r"(?P<remainder>[\s\S]*)"
    ),
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex that splits text into preamble and remainder after the socials marker."""

TEMPLATE_FRAGMENT: str = """
**Submission Template**
``Week: 
**Title:  **
Medium: 
Description: 

Social Media:
``
""".strip()
"""Part of the template post which gets ignored."""


HYPERLINK_REGEX: Pattern = re.compile(
    r"https?://[A-Za-z0-9./\-_~!+,*:@?=&$#]*", flags=re.MULTILINE | re.IGNORECASE
)
"""
Regex that finds simple hyperlinks.

Notes
-----
This is not meant to be extremely accurate but pick up most links you would find pasted into 
Discord. There are niche and non-ASCII examples that will break this but we do not consider them.
"""

CONTENT_LINK_REGEX: Pattern = re.compile(
    (
        r"(?:youtu\.be/\S)|"
        r"(?:youtube\.com/watch\?v="
        r"(?!xGP1pUeVJYA))|"
        r"(?:soundcloud\.com/\S+/\S)|"
        r"(?:itch\.io/\S)|"
        r"(?:docs\.google\.com)|"
        r"(?:imgur\.com/a/\S)|"
        r"(?:vimeo\.com)|"
        r"(?:webtoons\.com)"
    )
)
"""Regex used to parse content links, i.e., if they match a hyperlink, it's content."""


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

    # Handle missing content logging by placing it in the output temp directory. It's not
    # ignored by VCS but it is not expected to actually be used outside of diagnostically.

    write_missing_meta_file("out/temp/missing_socials.txt", final_data["submissions"], "socials")
    write_missing_meta_file("out/temp/missing_media.txt", final_data["submissions"], "medium")
    write_missing_meta_file("out/temp/missing_titles.txt", final_data["submissions"], "title")

    write_missing_meta_file(
        "out/temp/missing_descriptions.txt", final_data["submissions"], "description"
    )

    write_missing_meta_file(
        "out/temp/missing_attachments.txt", final_data["submissions"], "attachments"
    )


def write_missing_meta_file(file_path: str, submissions: List[dict], parse_type: str):
    with open(file_path, "w") as missing_meta_file:
        missing_meta_file.write(f"This file contains all missing [{parse_type}]s.")

        count: int = 0
        for submission in submissions:
            value: Union[str, list] = submission[parse_type]

            if parse_type == "description":
                value = value.strip()
            if not value:
                count += 1

                missing_meta_file.write(f"\n\nENTRY {count}\n{'='*119}\n\n")
                missing_meta_file.write(submission["raw_content"].strip())
                missing_meta_file.write(f"\n\n{'='*119}")

        missing_meta_file.write("\n")


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
            cumulative_message += f"\n{message['content']}\n"
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

    if TEMPLATE_FRAGMENT in content:
        return []

    # Find all matches otherwise.

    matches: List[Tuple[str, str, str]] = re.findall(WEEK_PARSING_REGEX, content)

    if not matches:
        is_handled: bool
        replacement: Optional[str]

        is_handled, replacement = match_replacement_or_expected_missing(content, "week")

        if not is_handled:
            LOGGER.warning("No [week]s found for content over next line:\n\n%s\n", content)

            return []

        if replacement and not isinstance(replacement, str):
            LOGGER.warning(
                "Week replacement found but it is not text for content over next line:\n\n%s\n",
                content,
            )

            return []

        if not replacement:
            LOGGER.info("Ignoring post entirely for content over next line:\n\n%s\n", content)

            return []

        # If it's handled, manually force a match and try to parse the rest.

        matches = [
            (
                "",
                replacement,
                content,
            ),
        ]

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

        # Form the hyperlinks and augment attachments if applicable.

        links: list[Any] = re.findall(HYPERLINK_REGEX, description)

        content_data.append({
            "author": author,
            "week": week,
            "title": title.strip(),
            "medium": medium.strip(),
            "description": description.strip(),
            "attachments": attachments + parse_content_hyperlinks(links),
            "socials": socials,
            "raw_content": content,
            "raw_hyperlinks": links
        })

        # TODO: attachments need to include hyperlinks if found.
        # TODO: hyperlinks surrounded by <> are not added to the links.

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
        The parse type, e.g., "raw_socials".

    Returns
    -------
    `Tuple[str, str, str]`
        A preamble, extraction, and remainder.
    """

    text = text.strip()

    matches: List[Tuple[str, str, str]] = re.findall(pattern, text)

    if not matches:
        is_handled: bool
        replacement: Optional[Any]

        is_handled, replacement = match_replacement_or_expected_missing(text, parse_type)

        if not is_handled:
            LOGGER.info("No [%s]s found for content over next line:\n\n%s\n", parse_type, text)

            return "", "", text

        return "", replacement or "", text
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

    return [{"__raw__": text}], text


def parse_content_hyperlinks(links: List[str]) -> List[str]:
    return [link for link in links if re.findall(CONTENT_LINK_REGEX, link)]


def match_replacement_or_expected_missing(
    description: str, name: str
) -> Tuple[bool, Optional[Any]]:
    """
    See if the description provided can be parsed using explicit replacements or ignores.

    Parameters
    ----------
    description : `str`
        The description or description fragment to search.

    name : `str`
        The name of the field to replace or ignore.

    Returns
    -------
    `Tuple[bool, Optional[Any]]`
        Whether or not it was handled (replaced or ignored) and what to replace it with,
        if applicable.
    """

    for replacement in REPLACEMENTS_AND_EXPECTED_MISSING_MAP["replacements"]:
        if replacement["description"] in description and name == replacement["name"]:
            return True, replacement["value"]

    for replacement in REPLACEMENTS_AND_EXPECTED_MISSING_MAP["expected_missing"]:
        if replacement["description"] in description and name == replacement["name"]:
            return True, None

    return False, None


def extract_socials_using_hyperlinks():
    pass  # TODO


if __name__ == "__main__":
    parse_retrieved()
