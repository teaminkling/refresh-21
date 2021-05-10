"""Parses local text files and translates them into a JSON object."""

import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from hashlib import md5
from logging import Logger
from typing import Any, Dict, List, Optional, Pattern, Set, Tuple, Union
from urllib.parse import quote

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

# noinspection RegExpUnnecessaryNonCapturingGroup
WEEK_PARSING_REGEX: Pattern = re.compile(
    (
        r"(?P<preamble>[\s\S]*?)(?<!my )(?<!for )(?:week)(?!-)(?:.{0,16}?)(?P<week>[0-9]+|One)"
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

Also note that this isn't perfect and there will need to be exceptions in many places in the code
to have this work for every submission.
"""

with open("in/replacements.json") as replacements_json_file:
    REPLACEMENTS_CONFIG_MAP: dict = json.load(replacements_json_file)
    """
    A map containing replacements and expected missing values for invalid submissions.
    
    Note that this is pre-processing. If the parser got something wrong or the formatting just 
    wasn't very good for the final blog post, I suggest using the `formatting.json` file instead.
    """

with open("in/socials.json") as socials_json_file:
    SOCIALS_CONFIG_MAP: dict = json.load(socials_json_file)
    """
    A map containing socials to ignore to help with erroneous social inputs.
    """

# noinspection RegExpUnnecessaryNonCapturingGroup
TITLE_PARSING_REGEX: Pattern = re.compile(
    r"(?P<preamble>[\s\S]*?)(?:title[:\-* ]+)(?P<title>.*$)(?P<remainder>[\s\S]*)",
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex that retrieves a title if applicable."""

# noinspection RegExpUnnecessaryNonCapturingGroup
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

# noinspection RegExpUnnecessaryNonCapturingGroup
RAW_SOCIAL_PARSING_REGEX: Pattern = re.compile(
    (
        r"(?P<preamble>[\s\S]*?)"
        r"(?P<raw_socials>socia"
        r"(?:(?:ls)|"
        r"(?:l media)|"
        r"(?:sl)|l)?(?! life)[:\-*]*[\s]+)"
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
    r"https?://[A-Za-z0-9./\-_~!+,*:@?=&$#]*",
    flags=re.MULTILINE | re.IGNORECASE,
)
"""
Regex that finds simple hyperlinks.

Notes
-----
This is not meant to be extremely accurate but pick up most links you would find pasted into 
Discord. There are niche and non-ASCII examples that will break this but we do not consider them.
"""

# noinspection RegExpUnnecessaryNonCapturingGroup
CONTENT_LINK_REGEX: Pattern = re.compile(
    (
        r"(?:youtu\.be/\S)|"
        r"(?:youtube\.com/watch\?v="
        r"(?!xGP1pUeVJYA)"
        r"(?!dQw4w9WgXcQ))|"
        r"(?:soundcloud\.com/\S+/\S)|"
        r"(?:itch\.io/\S)|"
        r"(?:docs\.google\.com)|"
        r"(?:imgur\.com/a/\S)|"
        r"(?:vimeo\.com)|"
        r"(?:webtoons\.com)|"
        r"(?:fliphtml5\.com)"
    ),
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex used to parse content links, i.e., if they match a hyperlink, it's content."""

SINGLE_NEWLINE_REGEX: Pattern = re.compile(
    r"(?<=\S)\n(?=[A-Za-z0-9(}\[\]_*])", flags=re.MULTILINE,
)

# noinspection RegExpUnnecessaryNonCapturingGroup
SOCIAL_PATTERN_PARENTHESES: Pattern[str] = re.compile(
    r"(?P<replacement>@(?P<username>\S+) +(?:\((?P<platforms>.*?)\)))",
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex used to find social patterns based on parentheses."""

# noinspection RegExpUnnecessaryNonCapturingGroup
SOCIAL_PATTERN_ON: Pattern[str] = re.compile(
    (
        r"(?P<replacement>"
        r"(?P<username>\S+) on "
        r"(?P<platform>"
        r"(?:(?:tw?itter)|"
        r"(?:twitch)|"
        r"(?:insta)|"
        r"(?:everything)|"
        r"(?:ig)).*))"
    ),
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex used to find social patterns based on the word "on"."""

# noinspection RegExpUnnecessaryNonCapturingGroup
NATURAL_LANGUAGE_SOCIALS: Pattern[str] = re.compile(
    r"(?: and )|(?: \+ )|\|| |/", flags=re.MULTILINE | re.IGNORECASE)
"""A pattern that allows general processing of a litany of different ways to itemise socials."""

# noinspection RegExpUnnecessaryNonCapturingGroup
SOCIAL_PATTERNS = [
    (
        "Instagram",
        re.compile(
            r"(?P<link>(?:(?:Insta(?:gram)?)|(?:IG)[: ,-]+)?"
            r"(?:https?://)?"
            r"(?:www\.)?instagram\.com/"
            r"(?P<username>[A-Za-z0-9_\-+&%#@^.]+))",
            flags=re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        "Twitter",
        re.compile(
            r"(?P<link>(?:Twitter[: ,-]+)?"
            r"(?:https?://)?"
            r"(?:www\.)?(?:mobile\.)?twitter\.com/"
            r"(?P<username>[A-Za-z0-9_\-+&%#@^.]+))",
            flags=re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        "Twitch",
        re.compile(
            r"(?P<link>(?:Twitch[: ,-]+)?"
            r"(?:https?://)?"
            r"(?:www\.)?twitch\."
            r"(?:(?:tv)|(?:com))/"
            r"(?P<username>[A-Za-z0-9_\-+&%#@^.]+))",
            flags=re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        "Tumblr",
        re.compile(
            r"(?P<link>(?:Tumblr[: ,-]+)?"
            r"(?:https?://)?"
            r"(?P<username>[A-Za-z0-9_\-+&%#@^.]+)\.tumblr\.com)",
            flags=re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        "Twitter",
        re.compile(
            r"(?P<replacement>twitter[ :=]+@(?P<username>[A-Za-z0-9_\-+&%#@^.]+))",
            flags=re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        "Instagram",
        re.compile(
            r"(?P<replacement>instagram[ :=]+@(?P<username>[A-Za-z0-9_\-+&%#@^.]+))",
            flags=re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        "Instagram",
        re.compile(
            r"(?P<replacement>instagram: +(?P<username>[A-Za-z0-9_\-+&%#@^.]+))",
            flags=re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        "Instagram",
        re.compile(
            (
                r"(?P<replacement>"
                r"(?:(?i:instagram)|(?:IG)|(?i:Insta))[ =\-:]+@?"
                r"(?P<username>[A-Za-z0-9_\-+&%#@^.]+))"
            ),
            flags=re.MULTILINE,
        ),
    ),
    (
        "Twitch",
        re.compile(
            r"(?P<replacement>twitch[ :=]*@(?P<username>[A-Za-z0-9_\-+&%#@^.]+))",
            flags=re.MULTILINE | re.IGNORECASE,
        ),
    ),
]
"""Tuples of a platform to a regex to find that platform as a replacement and username."""

# noinspection SpellCheckingInspection
PLATFORM_MAP: Dict[str, str] = {
    "twit": "Twitter",
    "titter": "Twitter",
    "twitter": "Twitter",
    "twittter": "Twitter",
    "twitch": "Twitch",
    "titch": "Twitch",
    "ig": "Instagram",
    "instagram": "Instagram",
    "insta": "Instagram",
    "everything": "Everywhere",
    "tumblr": "Tumblr",
}
"""Mapping of names for platforms to formatted names."""

# noinspection SpellCheckingInspection
PROBLEMATIC_CONTENT_FRAGMENTS: List[Tuple[str, str]] = [
    ("So this is it! This is finale of 17 weeks of Designrefesh!", "17"),
    ("liked the whale from the deep sea week (2)", "17"),
    ("So this week I am not submitting anything really", "17"),
]
"""
Content fragments which will cause the system to simply take the entire post as one week.

The second tuple part is the week to examine the fragmented messages as.
"""


def parse_retrieved() -> None:
    """
    Parse raw messages retrieved previously from Discord.
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
    for message in join_cumulative_messages(retrieved_data):
        # Remove special characters from authors from Discord.

        author: str = (
            message["author"]
            .encode("ascii", "ignore")
            .decode()
            .replace("(", "")
            .replace(
                ")",
                "",
            )
        )

        content: str = message["message"]
        created_at: str = message["created_at"]
        attachments: List[Dict[str, str]] = message["attachments"]

        final_data["submissions"].extend(
            extract_all_content(
                content=content,
                author=author,
                created_at=datetime.fromisoformat(created_at).date().isoformat(),
                attachments=attachments,
            ),
        )

    # Write final data.

    final_data["submission_count"] = len(final_data["submissions"])
    final_data["users"] = assign_submission_socials_to_users(final_data["submissions"])

    with open("out/parsed.json", "w") as json_output_file:
        json.dump(final_data, json_output_file, indent=2)

    write_missing_meta_files(final_data)


def write_missing_meta_files(data: dict) -> None:
    """
    Handle missing content logging by placing it in the output temp directory. It's not
    ignored by VCS but it is only expected to be used diagnostically.
    """

    write_missing_meta_file(data["submissions"], "medium")
    write_missing_meta_file(data["submissions"], "title")
    write_missing_meta_file(data["submissions"], "description")
    write_missing_meta_file(data["submissions"], "attachments")
    write_missing_meta_file(data["submissions"], "raw_socials")
    write_missing_meta_file(data["submissions"], "socials")

    # There is one more special case: if the "raw_socials" exists but the "socials" does not.

    with open("out/temp/unparsed_socials.txt", "w") as unparsed_socials_file:
        unparsed_socials_file.write(
            f"This file contains all unparsed socials with available raws.",
        )

        count: int = 0
        for submission in data["submissions"]:
            if submission["raw_socials"] and not submission["socials"]:
                count += 1

                unparsed_socials_file.write(f"\n\nENTRY {count}\n{'=' * 119}\n\n")
                unparsed_socials_file.write(submission["raw_content"].strip())
                unparsed_socials_file.write(f"\n\n{'=' * 119}")

        unparsed_socials_file.write("\n")


def write_missing_meta_file(submissions: List[dict], parse_type: str) -> None:
    """
    Write a meta file for missing attributes in any submission.

    Parameters
    ----------
    submissions : `List[dict]`
        The submissions `list`.

    parse_type : `str`
        The parse type used for attribute lookup.
    """

    with open(f"out/temp/missing_{parse_type}.txt", "w") as missing_meta_file:
        missing_meta_file.write(f"This file contains all missing [{parse_type}]s.")

        count: int = 0
        for submission in submissions:
            value: Union[str, list] = submission[parse_type]

            if parse_type == "description":
                if isinstance(value, list):
                    raise RuntimeError(
                        "Parse type cannot be [description] if the parsed element is not text.",
                    )

                value = value.strip()

            if parse_type == "title" and value == "Untitled":
                value = ""

            if not value:
                count += 1

                missing_meta_file.write(f"\n\nENTRY {count}\n{'='*119}\n\n")
                missing_meta_file.write(submission["raw_content"].strip())
                missing_meta_file.write(f"\n\n{'='*119}")

        missing_meta_file.write("\n")


def join_cumulative_messages(retrieved_data: dict) -> List[dict]:
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
    cumulative_attachments: List[Dict[str, str]] = []
    author: str = ""
    last_author: str = ""
    last_seen_date: str = ""

    for message in reversed(retrieved_data["messages"]):
        author = message["author"]["mention_name"]
        attachments: List[Dict[str, str]] = [
            {
                "url": attachment["url"],
                "thumbnail_url": attachment["thumbnail_url"],
            }
            for attachment in message["attachments"]
        ]
        last_seen_date = message["created_at"]

        if author == last_author or not last_author:
            cumulative_message += f"\n{message['content']}\n"
            cumulative_attachments.extend(attachments)
        else:
            joined_messages.append(
                {
                    "message": cumulative_message,
                    "attachments": cumulative_attachments,
                    "author": last_author,
                    "created_at": last_seen_date,
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
                "created_at": last_seen_date,
            }
        )

    return joined_messages


def extract_all_content(
    content: str, author: str, created_at: str, attachments: List[Dict[str, str]]
) -> List[dict]:
    """
    Extract all information for content, allowing for multiple week submissions in one post.

    Parameters
    ----------
    content : `str`
        The content text.

    author : `str`
        The author of the submission(s).

    created_at : `str`
        The created timestamp.

    attachments : `List[Dict[str, str]`
        The found attachments for the given content. Note that if there are attachments for
        multiple weeks in one post, there will be duplications that must be handled manually.

    Returns
    -------
    `List[dict]`
        Content `dict` that can be extended for the final parsed JSON file.
    """

    # First, clean the message of any leftover emoji codes. They might screw up the parse.

    content = re.sub(r"<:\S+:\d+>", "", content)

    # Don't bother extracting if it's the template message.

    if TEMPLATE_FRAGMENT in content:
        return []

    # Find all matches via the complex week-seeking regex.

    matches: List[Tuple[str, str, str]] = re.findall(WEEK_PARSING_REGEX, content)

    # Handle some extremely headache-inducing submissions that may as well be manual.

    if len(matches) > 1:
        for fragment, replacement_week in PROBLEMATIC_CONTENT_FRAGMENTS:
            if fragment in content:
                matches = [("", replacement_week, content)]

                break

    # If there are no weeks found via the regex, handle it.

    if not matches:
        is_handled: bool
        replacement: Optional[str]

        is_handled, replacement = match_replacement_or_expected_missing(content, "week")

        if not is_handled:
            LOGGER.warning(
                "No [week]s found for content over next line:\n\n%s\n",
                content,
            )

            return []

        if replacement and not isinstance(replacement, str):
            LOGGER.warning(
                "Week replacement found but it is not text for content over next line:\n\n%s\n",
                content,
            )

            return []

        if not replacement:
            LOGGER.info(
                "Ignoring post entirely for content over next line:\n\n%s\n",
                content,
            )

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

        # Weeks may have an exception where a week is written as "one" instead of "1".

        week: int
        if match[1].lower() == "one":
            week = 1
        else:
            week = int(match[1])

        # Parse the remainder and preamble. The amount of content is fixed (not dynamic) so
        # there's no point iterating.

        preamble: str
        remainder: str

        preamble, remainder = remove_markdown_formatting(match[0], match[2])

        # Start to parse content.

        title: str
        preamble, title, remainder = parse_content(
            text=f"{preamble}\n{remainder}",
            pattern=TITLE_PARSING_REGEX,
            parse_type="title",
        )

        # Kill the title if it's too long.

        title = title.strip()
        if len(title) > 128:
            title = "[Title Too Long]"

        medium: str
        preamble, medium, remainder = parse_content(
            text=f"{preamble}\n{remainder}",
            pattern=MEDIUM_PARSING_REGEX,
            parse_type="medium",
        )

        # Description and socials are dynamic. We need to intelligently parse them.

        preamble, raw_socials, remainder = parse_content(
            text=f"{preamble}\n{remainder}",
            pattern=RAW_SOCIAL_PARSING_REGEX,
            parse_type="raw_socials",
        )

        socials: List[Dict[str, str]] = []
        if raw_socials:
            # Set the raw socials to be saved as meta-information later.

            raw_socials = remainder

            # Parse the socials in a tabular manner.

            socials, remainder = parse_socials(remainder)

        description: str = handle_descriptions(preamble, remainder)

        # Form the hyperlinks and augment attachments if applicable.

        links: List[str] = re.findall(HYPERLINK_REGEX, description)
        url_attachments: List[Dict[str, str]] = [
            {"url": link} for link in links if re.findall(CONTENT_LINK_REGEX, link)
        ]

        # Form an ID to be used as the slug for each submission.

        title = title.replace('"', "").strip() or "Untitled"
        submission_id: str = quote(
            f"{author[:-5]}-week-{week}-{md5(title.encode()).hexdigest()[:4]}".lower()
            .replace(" ", "-")
            .encode("ascii", "ignore")
            .decode()
        )

        content_data.append(
            {
                "id": submission_id,
                "author": author,
                "created_at": created_at,
                "week": week,
                "title": title,
                "medium": medium.strip(),
                "description": description.strip(),
                "attachments": attachments + url_attachments,
                "socials": socials,
                "raw_content": content,
                "raw_socials": raw_socials,
                "raw_hyperlinks": links,
            },
        )

    return content_data


def handle_descriptions(preamble: str, remainder: str) -> str:
    """
    Parse a description.

    Descriptions are the leftover content after parsing everything else (except attachments
    which is handled in the step after)

    Parameters
    ----------
    preamble : `str`
        The textual preamble.

    remainder : `str`
        The textual remainder.

    Returns
    -------
    `str`
        The description.
    """

    dynamic_content: str = f"{preamble}\n{remainder}".strip()
    dynamic_content = re.sub(r"\n{3,}", "\n\n", dynamic_content)
    dynamic_content = re.sub(r"(?i:description)[: -]*", "", dynamic_content)

    # Partially clean the description by removing "social media" text from the description.

    description = re.sub(r"(?i:social[s]?(?: media)?)[: -]*", "", dynamic_content)

    # Remove lines that are just single characters. Leaves whitespace.

    temp_description: str = ""

    for line in description.split("\n"):
        if len(line.strip()) != 1 or line.strip() == "<>":
            temp_description += f"{line}\n"

    description = temp_description

    # Ensure all newlines are two \ns, not one or more than two.

    description = re.sub(r"\n{3,}", "\n\n", description)
    description = re.sub(SINGLE_NEWLINE_REGEX, "\n\n", description)

    return description


def remove_markdown_formatting(preamble: str, remainder: str) -> Tuple[str, str]:
    """
    Remove Markdown formatting from a preamble and remainder pair.

    Parameters
    ----------
    preamble : `str`
        The textual preamble.

    remainder : `str`
        The textual remainder.

    Returns
    -------
    `Tuple[str, str]`
        A pair of the parsed preamble and remainder.
    """

    # Remove bolds.

    preamble = re.sub(r"\*\*(?P<unformatted>.*)\*\*", r"\g<unformatted>", preamble)
    remainder = re.sub(
        r"\*\*(?P<unformatted>.*)\*\*",
        r"\g<unformatted>",
        remainder,
    )

    # Remove italics.

    preamble = re.sub(
        r"(?<!\S)_(?P<unformatted>.*)_(?!\S)", r"\g<unformatted>", preamble
    )
    remainder = re.sub(
        r"(?<!\S)_(?P<unformatted>.*)_(?!\S)", r"\g<unformatted>", remainder
    )
    preamble = re.sub(
        r"(?<!\S)\*(?P<unformatted>.*)\*(?!\S)", r"\g<unformatted>", preamble
    )
    remainder = re.sub(
        r"(?<!\S)\*(?P<unformatted>.*)\*(?!\S)", r"\g<unformatted>", remainder
    )

    # Remove underlines.

    preamble = re.sub(r"__(?P<unformatted>.*)__", r"\g<unformatted>", preamble)
    remainder = re.sub(r"__(?P<unformatted>.*)__", r"\g<unformatted>", remainder)

    return preamble, remainder


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

        is_handled, replacement = match_replacement_or_expected_missing(
            text,
            parse_type,
        )

        if not is_handled:
            LOGGER.info(
                "No [%s]s found for content over next line:\n\n%s\n",
                parse_type,
                text,
            )

            return "", "", text

        return "", replacement or "", text
    elif len(matches) > 1:
        LOGGER.info(
            "Multiple [%s]s found for content over next line:\n\n%s\n",
            parse_type,
            text,
        )

    return matches[0][0], matches[0][1], matches[0][2]


def parse_socials(text: str) -> Tuple[List[Dict[str, str]], str]:
    """
    Parse social links and references to tags on popular social media websites.

    Parameters
    ----------
    text : `str`
        The text to parse and replace.

    Returns
    -------
    `Tuple[List[Dict[str, str]], str]`
        A `tuple` of the socials found (which is a mapping of provider to username) and the
        remainder of the content which was not parsed, if applicable, to be added back to the
        description to be formatted.
    """

    found_socials: List[Dict[str, str]] = []

    # Handle situations where people put socials in brackets, use "X on Y", and have multiple of
    # the same username on different social platforms.

    for match in list(re.findall(SOCIAL_PATTERN_PARENTHESES, text)) + list(
        re.findall(SOCIAL_PATTERN_ON, text)
    ):
        replacement: str = match[0]
        username: str = match[1].replace("@", "").replace("/", "")
        platforms_text: str = match[2].encode("ascii", "ignore").decode().strip()

        if replacement in SOCIALS_CONFIG_MAP["ignore_socials"]["partial"]:
            continue

        platform: str
        for platform in re.split(NATURAL_LANGUAGE_SOCIALS, platforms_text):
            # Parse out unnecessary punctuation.

            platform = platform.lower().replace("!", "").replace(".", "")

            found_platform: Optional[str] = PLATFORM_MAP.get(platform)

            if found_platform:
                found_socials.append({"provider": found_platform, "username": username.lower()})
            else:
                LOGGER.warning("Unknown platform: [%s].", platform)

        text = text.replace(replacement, "").strip()

        LOGGER.info("Found [%s], replacing: [%s].", username, replacement)

    # Handle remainder cases.

    for name, regex in SOCIAL_PATTERNS:
        for social in re.findall(regex, text):
            if social[1]:
                LOGGER.info(
                    "Found [%s], replacing: [%s], using: [%s].",
                    social[1],
                    social[0],
                    regex,
                )

                found_socials.append({"provider": name, "username": social[1].lower()})

                # Replace the exact match in the regex such that it does not appear in the
                # description when it is added back.

                text = text.replace(social[0], "").strip()

    # Handle cases where all that's left in the text is symbols and special characters.

    text = text.strip()
    if all([character in " |,;/`" for character in text]):
        text = ""

    # Handle cases that are not social medias and match wholesale with an exclude list.

    if text in SOCIALS_CONFIG_MAP["ignore_socials"]["wholesale"]:
        text = ""

    if text:
        LOGGER.warning(
            "There is remainder text that can't be parsed as socials over next line:\n\n%s\n",
            text,
        )

    return sorted(
        found_socials,
        key=lambda social_data: (social_data["provider"], social_data["username"]),
    ), text


def assign_submission_socials_to_users(
    submissions: List[dict],
) -> Dict[str, List[Dict[str, str]]]:
    """
    Search through all submissions and assign all socials for each individual user.

    Notes
    -----
    Sets do not allow custom hash algorithms for uniqueness, so we use linear search instead.

    Parameters
    ----------
    submissions : `List[dict]`
        The submissions `list`.

    Returns
    -------
    `Dict[str, List[Dict[str, str]]]`
        A mapping of users to a list of their providers, which is provided as a `dict` mapping a
        provider name and username.
    """

    # Combine all users' socials to one big list.

    user_to_socials: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for submission in submissions:
        if submission["socials"]:
            user_to_socials[submission["author"]].extend(submission["socials"])

    # Flatten out the resultant list.

    seen_socials: Set[Tuple[str, str]] = set()
    user_to_unique_socials: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    for discord_username, socials in user_to_socials.items():
        for social in socials:
            social_key: Tuple[str, str] = (social["provider"], social["username"])

            if social_key not in seen_socials:
                user_to_unique_socials[discord_username].append(social)

                seen_socials.add(social_key)

    return user_to_unique_socials


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

    for replacement in REPLACEMENTS_CONFIG_MAP["replacements"]:
        if replacement["description"] in description and name == replacement["name"]:
            return True, replacement["value"]

    for replacement in REPLACEMENTS_CONFIG_MAP["expected_missing"]:
        if replacement["description"] in description and name == replacement["name"]:
            return True, None

    return False, None


if __name__ == "__main__":
    parse_retrieved()
