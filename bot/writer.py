"""Using an input JSON, writes Markdown blog posts representing submissions."""

# TODO: Social links must be removed from the final blog post.

import json
from typing import Any, Dict, List, Optional

import requests
from requests import Response
from webpreview import web_preview

GITHUB_REPO_URL: str = "https://github.com/teaminkling/web-refresh"

GITHUB_EDIT_URL: str = f"{GITHUB_REPO_URL}/edit/main/content/blog/"

GITHUB_BUG_URL: str = f"{GITHUB_REPO_URL}/issues/new?assignees=&labels=bug&template=problem-report.md&title="

VISUAL_MEDIA_TEMPLATE: str = """
<a href="<!IMAGE_SRC>"
   class="image"
   style="--bg-image: url('<!IMAGE_SRC>');"
   target="__blank"
>
  <img class="cover" src="<!IMAGE_SRC>" alt="<!TITLE>" />
</a>
""".strip()

VISUAL_MEDIA_PERMALINK_NOTIFICATION: str = """
_You may need to click on the image for a higher quality permalink._
""".strip()

BLOG_POST_TEMPLATE: str = f"""
+++
title =       "<!TITLE>"
author =      "<!AUTHOR>"
date =        "<!SUBMITTED_DATE>"
themes =      ["<!THEME>"]
artists =     ["<!AUTHOR>"]
description = "<!SEARCH_DESCRIPTION>"
<!PREVIEW>
+++

<!MEDIA>

Week <!WEEK>: **<!THEME_ONLY>**. This art was lovingly created using: **<!MEDIUM>**.

## Artist's Notes

<!DESCRIPTION>

## Social Media

<!SOCIALS>

## Other

- Edit this page on [GitHub]({GITHUB_EDIT_URL}<!ID>.md).
- Create [a bug ticket]({GITHUB_BUG_URL}) for the developer.
- Parsed source from Discord is as follows:

{{{{< highlight txt >}}}}
<!RAW_DESCRIPTION>
{{{{< /highlight >}}}}
""".strip()

IMAGE_FILE_EXTENSIONS = ("png", "jpg", "svg", "jpeg", "bmp", "gif")

VIDEO_FILE_EXTENSIONS = ("mp4", "mov", "swf")

AUDIO_FILE_EXTENSIONS = ("mp3", "wav", "ogg")

WEEK_TO_THEME_MAP: Dict[int, str] = {
    1: "Yellow Lines",
    2: "Deep Ocean",
    3: "Red Circle",
    4: "Murky Silhouettes",
    5: "Royal Green",
    6: "Simple Love",
    7: "Disturbed Desert",
    8: "High Sheen",
    9: "Bold Strokes",
    10: "Folds and Folds",
    11: "Atmosphere Spectrum",
    12: "Visual Words",
    13: "Look At Me",
    14: "Absolute Fire",
    15: "Back to Basics",
    16: "Scaling Giants",
    17: "The 4 R's: Finale",
}
"""A mapping from the week integer to the name of the theme."""


VISUAL_ALT_TEXT: str = "Placeholder thumbnail for a visual still work."

GENERIC_ALT_TEXT: str = "External link image preview for generic website."

EXTERNAL_WEBSITE_DISCLAIMER: str = (
    "The image above leads to an external website. Please be careful!"
)

PREVIEW_STYLE: str = (
    "box-shadow: 0 3px 6px rgb(0 0 0 / 16%), 0 3px 6px rgb(0 0 0 / 23%);"
)


def create_all_posts() -> None:
    """Create all blog posts."""

    # Save the previously parsed JSON.

    with open("out/parsed.json") as parsed_json_file:
        parsed_json: dict = json.load(parsed_json_file)

    # Iterate through all submissions.

    for submission in parsed_json["submissions"]:
        write_submission_post(submission, parsed_json["users"])


def write_submission_post(
    submission: Dict[str, Any],
    users: Dict[str, List[Dict[str, str]]],
) -> None:
    # Extract information about the submission.

    post_url: str = f"/blog/{submission['id']}"

    week_number: int = submission["week"]
    theme_name: str = WEEK_TO_THEME_MAP[submission["week"]]

    title = submission["title"]
    title = (
        title.replace("_", "").replace("*", "").replace('"', "")
    )  # FIXME: move to parser
    short_author: str = submission["author"][:-5]
    medium: str = submission["medium"] or "unknown medium"
    medium = medium.replace('"', "")  # FIXME: move to parser
    description: str = submission["description"]

    # Create the description shown when searching in the interface.

    search_description: str = f"by {short_author} for week {week_number}: {theme_name}. Created using: {medium}."

    # Find the media content HTML and a thumbnail. The thumbnail is used to click into the blog
    # post in the list view.

    # Note the submission thumbnail is not necessarily the same as the media thumbnail.

    submission_thumbnail_url: Optional[str]
    media_content_html: str
    list_item_caption: Optional[str]

    (
        media_content_html,
        submission_thumbnail_url,
        list_item_caption,
    ) = determine_media_and_submission_thumbnail(submission)

    # Write each post to a file using tag substitutions.

    preview: str = f"""
    [[images]]
      src = "{submission_thumbnail_url}"
      href = "{post_url}"
      alt = "{title}"
      caption = "{list_item_caption or ''}"
      stretch = "cover"
    """.strip()

    replacement_map: Dict[str, Any] = {
        "<!ID>": submission["id"],
        "<!TITLE>": title,
        "<!AUTHOR>": short_author,
        "<!SUBMITTED_DATE>": submission["created_at"],
        "<!MEDIUM>": medium,
        "<!WEEK>": str(week_number),
        "<!THEME_ONLY>": theme_name,
        "<!THEME>": f"Week {week_number:02d}: {theme_name}",
        "<!MEDIA>": media_content_html,
        "<!SEARCH_DESCRIPTION>": search_description,
        "<!DESCRIPTION>": description,
        "<!RAW_DESCRIPTION>": submission["raw_content"],
        "<!PREVIEW>": preview,
        "<!SOCIALS>": extract_socials_text(submission, users),
    }

    with open(f"../content/blog/{submission['id']}.md", "w") as output_post_file:
        template: str = BLOG_POST_TEMPLATE

        for key, replacement in replacement_map.items():
            template = template.replace(key, replacement)

        output_post_file.write(template)


def determine_media_and_submission_thumbnail(submission):
    submission_thumbnail_url: Optional[str] = None
    media_content_html: str = ""
    list_item_caption: Optional[str] = None

    if not submission["attachments"]:
        submission_thumbnail_url = "img/other-placeholder.png"
        list_item_caption = (
            "Please view the full post to see the submission!"
        )

    for attachment_data in submission["attachments"]:
        # The submission may already have a generated thumbnail.

        generated_thumbnail_url: Optional[str] = attachment_data.get("thumbnail_url")
        if generated_thumbnail_url:
            generated_thumbnail_url = generated_thumbnail_url.replace("../static", "")

        # Find information about the local nature of the content and the type of content it is.

        attachment_url: str = attachment_data["url"].replace("../static/", "")
        attachment_extension: str = attachment_url.split(".")[-1].lower()
        is_locally_hosted: bool = "img/" in attachment_url

        # Ensure both URLs start with a "/"

        if not attachment_url.startswith("/") and not attachment_url.startswith("http"):
            attachment_url = f"/{attachment_url}"

        if generated_thumbnail_url and not generated_thumbnail_url.startswith("/"):
            generated_thumbnail_url = f"/{generated_thumbnail_url}"

        # Start to determine the media content and ensure correct thumbnail for this post.

        if is_locally_hosted:
            # If the existing thumbnail is not a local file, overwrite it. Do the same if there's
            # no determined thumbnail yet as well.

            can_use_generated_as_first_submission_url: bool = (
                not submission_thumbnail_url and generated_thumbnail_url
            )

            can_replace_retrieved_thumbnail: bool = (
                submission_thumbnail_url and "img/" not in submission_thumbnail_url
            )

            can_replace_placeholder_thumbnail: bool = (
                submission_thumbnail_url and "-placeholder.png" in submission_thumbnail_url
            )

            if (
                can_use_generated_as_first_submission_url
                or can_replace_retrieved_thumbnail
                or can_replace_placeholder_thumbnail
            ):
                submission_thumbnail_url = generated_thumbnail_url

            # Handle media content.

            if attachment_extension in IMAGE_FILE_EXTENSIONS:
                submission_thumbnail_url = submission_thumbnail_url or attachment_url
                media_content_html += create_fancybox_string(
                    thumbnail=generated_thumbnail_url or attachment_url,
                    permalink=attachment_url,
                    alt=VISUAL_ALT_TEXT,
                )
            elif attachment_extension in VIDEO_FILE_EXTENSIONS:
                submission_thumbnail_url = (
                    submission_thumbnail_url or "/img/video-placeholder.png"
                )

                media_content_html += create_fancybox_string(
                    thumbnail=generated_thumbnail_url or "/img/video-placeholder.png",
                    permalink=attachment_url,
                    alt="Placeholder thumbnail for a video work.",
                    caption="The above is an MP4 video link. Please click it to view the video!",
                )

                if not list_item_caption:
                    list_item_caption = (
                        "This submission contains a video. Please view the full post to see it!"
                    )
            elif attachment_extension in AUDIO_FILE_EXTENSIONS:
                submission_thumbnail_url = (
                    submission_thumbnail_url or "/img/audio-placeholder.png"
                )

                media_content_html += (
                    f'<div style="padding: 1.5em; text-align: center"><audio controls>\n<source '
                    f'src="{attachment_url}" type="{determine_mime_type(attachment_extension)}"> '
                    f'Your browser does not support the audio element.</audio></div>'
                )

                if not list_item_caption:
                    list_item_caption = (
                        "This submission contains audio. Please view the full post to hear it!"
                    )
            else:
                submission_thumbnail_url = (
                    submission_thumbnail_url or "/img/other-placeholder.png"
                )

                media_content_html += (
                    f'<a href="{attachment_url}" target="_blank">Direct link to a '
                    f".{attachment_extension} file.</a>"
                )

                if not list_item_caption:
                    list_item_caption = (
                        "This submission contains a file. Please view the full post to see it!"
                    )
        elif "youtu" in attachment_url or "vimeo" in attachment_url:
            video_api_thumbnail: str = extract_external_video_thumbnail_url(attachment_url)
            submission_thumbnail_url = submission_thumbnail_url or video_api_thumbnail
            media_content_html += create_fancybox_string(
                thumbnail=video_api_thumbnail,
                permalink=attachment_url,
                alt=VISUAL_ALT_TEXT,
            )

            if not list_item_caption:
                list_item_caption = (
                    "This submission contains a video link. Please view the full post to see it!"
                )
        elif "soundcloud" in attachment_url:
            # TODO: Soundcloud embed.

            submission_thumbnail_url = submission_thumbnail_url or "/img/audio-placeholder.png"
            media_content_html += f"\n[View on SoundCloud.]({attachment_url})\n"

            if not list_item_caption:
                list_item_caption = (
                    "This submission contains an audio link. Please view the full post to hear it!"
                )
        else:
            # Use slow tool to find the thumbnail for the link.

            # TODO: cache

            image_url: str
            _, _, image_url = web_preview(attachment_url, parser="html.parser")

            if image_url:
                media_content_html += create_custom_image_content_string(attachment_url, image_url)
                if not list_item_caption:
                    list_item_caption = (
                        "This submission contains a link. Please view the full post to see it!"
                    )
            else:
                media_content_html += (
                    f"\n[View on External Website.]({attachment_url})\n"
                )

            if not list_item_caption:
                list_item_caption = (
                    "This submission contains a web link. Please view the full post to see it!"
                )

            submission_thumbnail_url = (
                submission_thumbnail_url or image_url or "img/other-placeholder.png"
            )

    return media_content_html, submission_thumbnail_url, list_item_caption


def create_custom_image_content_string(url: str, image_url: str) -> str:
    output: str = ""

    output += '<div style="text-align: center; margin: 3em; margin-top: 1.5em;" >'
    output += f'<a href="{url}" target="_blank">'
    output += f'<img src="{image_url}" alt="{GENERIC_ALT_TEXT}" style="{PREVIEW_STYLE}"/>'
    output += "</a></div>"
    output += f'<p style="text-align: center"><i>{EXTERNAL_WEBSITE_DISCLAIMER}</i></p>'

    return output


def extract_socials_text(
    submission: Dict[str, Any], users: Dict[str, List[Dict[str, str]]]
) -> str:
    # TODO: Don't do this here. Have it pre-parsed.
    user_socials: List[dict] = users.get(submission["author"], [])

    socials_list: List[str] = []
    for social in sorted(
        user_socials,
        key=lambda pair: tuple([pair["provider"], pair["username"]]),
    ):
        provider: str = social["provider"]
        username: str = social["username"]

        # Handle parsed but invalid socials:

        if provider.lower() == "everywhere":
            continue

        # Handle other social providers:

        link: str = "#"
        if provider.lower() == "tumblr":
            link = f"https://{username}.tumblr.com"
        elif provider.lower() == "instagram":
            link = f"https://instagram.com/{username}"
        elif provider.lower() == "twitter":
            link = f"https://twitter.com/{username}"
        elif provider.lower() == "twitch":
            link = f"https://twitch.tv/{username}"

        socials_list.append(
            f"- **{provider}**: <a href='{link}' target='_blank'>{username}</a>"
        )

    if not socials_list:
        return "- N/A."

    return "\n".join(socials_list)


def extract_external_video_thumbnail_url(attachment_url: str) -> str:
    # TODO: cache with cache timeout
    # TODO: composite with a "play" button.

    code: str = attachment_url.split("/")[-1]

    if "youtube.com/watch" in attachment_url:
        # Assumption: "v" parameter is always first.

        code = code.replace("watch?v=", "").split("&")[0]

        return f"https://img.youtube.com/vi/{code}/maxresdefault.jpg"
    elif "youtu.be" in attachment_url:
        code = code.split("?")[0].split("&")[0]

        return f"https://img.youtube.com/vi/{code}/maxresdefault.jpg"
    elif "vimeo" in attachment_url:
        code = code.split("?")[0]

        response: dict = requests.get(
            f"https://vimeo.com/api/v2/video/{code}.json"
        ).json()

        return response[0]["thumbnail_large"]

    raise RuntimeError(f"Link not understood as video service: [{attachment_url}].")


def determine_mime_type(attachment_extension: str) -> str:
    if attachment_extension == "mp3":
        return "audio/mpeg"
    elif attachment_extension == "wav":
        return "audio/wav"
    elif attachment_extension == "ogg":
        return "audio/ogg"

    raise RuntimeError(f"Unsupported audio type: [{attachment_extension}].")


def create_fancybox_string(thumbnail, permalink, alt, caption=None):
    fancybox: str = (
        f"{{{{< fancybox path=\"{thumbnail}\" file=\"{permalink}\" caption=\"{alt}\" >}}}}\n"
    )

    if caption:
        return f"{fancybox}<p style=\"text-align: center\">{caption}</p>\n"

    return fancybox


if __name__ == "__main__":
    create_all_posts()
