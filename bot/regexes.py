"""A collection of regular expressions used within the processing scripts."""

import re
from typing import Pattern


WEEK_PARSING_REGEX: Pattern = re.compile(
    (
        r"(?P<preamble>[\s\S]*?)(?<!my )(?<!for )week(?!-).{0,16}?(?P<week>[0-9]+|One)"
        r".*[\s](?P<remainder>[\S\s]+?)(?:(?<!title: )(?=week.{1,16}?[0-9]+)"
        r"(?!week-)(?!week \d+[ ,])|\Z)"
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

TITLE_PARSING_REGEX: Pattern = re.compile(
    r"(?P<preamble>[\s\S]*?)title[:\-* ]+(?P<title>.*$)(?P<remainder>[\s\S]*)",
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex that retrieves a title if applicable."""

MEDIUM_PARSING_REGEX: Pattern = re.compile(
    (
        r"(?P<preamble>[\s\S]*?)"
        r"(?<!social )"
        r"medi(?:um|a)[,:\-*]*[\s]+"
        r"(?P<medium>.*$)"
        r"(?P<remainder>[\s\S]*)"
    ),
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex that retrieves a medium if applicable."""

RAW_SOCIAL_PARSING_REGEX: Pattern = re.compile(
    (
        r"(?P<preamble>[\s\S]*?)"
        r"(?P<raw_socials>socia"
        r"(?:ls|"
        r"l media|"
        r"sl|l|s)?(?! life)[:\-*]*[\s]+)"
        r"(?P<remainder>[\s\S]*)"
    ),
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex that splits text into preamble and remainder after the socials marker."""

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

CONTENT_LINK_REGEX: Pattern = re.compile(
    (
        r"youtu\.be/\S|"
        r"youtube\.com/watch\?v=(?!"
        r"xGP1pUeVJYA)(?!"
        r"dQw4w9WgXcQ)|"
        r"soundcloud\.com/\S+/\S|"
        r"itch\.io/\S|"
        r"docs\.google\.com|"
        r"imgur\.com/a/\S|"
        r"vimeo\.com|"
        r"webtoons\.com|"
        r"fliphtml5\.com"
    ),
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex that recognises if a link is one of the accepted media sites."""

SINGLE_NEWLINE_REGEX: Pattern = re.compile(
    r"(?<=\S)\n(?=[A-Za-z0-9(}\[\]_*])",
    flags=re.MULTILINE,
)
"""Regex used to recognise when there is exactly one newline in text and matches that newline."""

SOCIALS_ITEMIZATION_PARENTHESES_REGEX: Pattern[str] = re.compile(
    r"(?P<replacement>@(?P<username>\S+) +\((?P<platforms>.*?)\))",
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex used to find social patterns based on parentheses."""

SOCIALS_ITEMIZATION_WORD_ON_REGEX: Pattern[str] = re.compile(
    (
        r"(?P<replacement>"
        r"(?P<username>\S+) on "
        r"(?P<platform>"
        r"(?:tw?itter|"
        r"twitch|"
        r"insta|"
        r"everything|"
        r"ig).*))"
    ),
    flags=re.MULTILINE | re.IGNORECASE,
)
"""Regex used to find social patterns based on the word "on"."""

SOCIALS_ITEMIZATION_NATURAL_LANGUAGE_REGEX: Pattern[str] = re.compile(
    r" and | \+ |\|| |/", flags=re.MULTILINE | re.IGNORECASE
)
"""Regex that allows general processing of a litany of different ways to itemise socials."""

SOCIAL_PROVIDER_TO_LINK_REGEX = [
    (
        "Instagram",
        re.compile(
            r"(?P<link>(?:Insta(?:gram)?|IG[: ,-]+)?"
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
            r"(?:tv|com)/"
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
                r"(?:(?i:instagram)|IG|(?i:Insta))[ =\-:]+@?"
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

LINK_SITE_NAME_EXTRACTOR: Pattern = re.compile(
    r"(?:https?://)?(?P<site_name>[a-z0-9]+)\.[a-z/]+(?:$|/)", flags=re.IGNORECASE,
)
"""Regex to extract the name of a site (name before the TLD)."""
