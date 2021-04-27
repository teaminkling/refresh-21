"""Using an input JSON, writes Markdown blog posts representing submissions."""

# TODO: Social links must be removed from the final blog post.

import json
from typing import Dict, List

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

FRONTMATTER: str = f"""
+++
title =       "<!TITLE>"
author =      "<!AUTHOR>"
date =        "<!SUBMITTED_DATE>"
themes =      ["<!THEME>"]
artists =     ["<!AUTHOR>"]
description = "<!SHORT_DESCRIPTION>"
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

VALID_INSTANT_THUMBNAILS = ("png", "jpg", "svg", "jpeg", "bmp", "gif")


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


def create_all_posts():
    with open("out/parsed.json") as parsed_json_file:
        parsed_json: dict = json.load(parsed_json_file)

    for submission in parsed_json["submissions"]:
        filename: str = f"{submission['id']}.md"

        with open(f"../content/blog/{filename}", "w") as output_post_file:
            # Extract some shorthand information.

            week_number: int = submission["week"]
            theme_name: str = WEEK_TO_THEME_MAP[submission["week"]]
            short_author: str = submission["author"][:-5]
            description: str = submission["description"]
            medium: str = submission["medium"] or "unknown medium"

            # Handle invalid values.

            title = (
                submission["title"].replace("_", "").replace("*", "").replace('"', "")
            )

            medium = medium.replace('"', "")

            # Determine a short description. This is only used in the search interface.

            short_description: str = f"by {short_author} for week {week_number}: {theme_name}. Created using: {medium}."

            # Determine the media to show.

            attachment_text: str = ""
            thumbnail: str = ""
            for attachment_data in submission["attachments"]:
                attachment: str = attachment_data["url"]
                provided_thumbnail: str = attachment_data.get("thumbnail_url") or ""

                # First, make the paths relative to the root and not the bot.

                attachment = attachment.replace("../static/", "")
                provided_thumbnail = provided_thumbnail.replace("../static", "")

                # Set the first thumbnail.

                thumbnail = provided_thumbnail or attachment

                if "img/" in attachment:
                    # This is a local file so we can display it with a fancybox. However,
                    # the thumbnail might not appear before we click it so we need to set
                    # placeholders if they are not render-able.

                    # Allow explosion if there's no "." in the filename.

                    extension: str = attachment.split(".")[-1].lower()
                    old_extension: str = (
                        thumbnail.split(".")[-1].lower() if "." in thumbnail else ""
                    )

                    # Overwrite thumbnail with image if the current attachment is one and there
                    # isn't an image attachment thumbnail already.

                    if extension in VALID_INSTANT_THUMBNAILS:
                        if old_extension not in VALID_INSTANT_THUMBNAILS:
                            thumbnail = provided_thumbnail or attachment

                        attachment_text += (
                            '\n{{< fancybox path="'
                            + (provided_thumbnail or attachment)
                            + '" file="'
                            + attachment
                            + '" caption="Placeholder thumbnail for a visual work." >}}\n'
                        )
                    elif extension in ("mp4", "mov", "swf"):
                        if old_extension not in VALID_INSTANT_THUMBNAILS:
                            thumbnail = "img/video-placeholder.png"

                        attachment_text += (
                            '\n{{< fancybox path="img/video-placeholder.png" file="'
                            + attachment
                            + '" caption="Placeholder thumbnail for a video work." >}}\n'
                        )
                    elif extension in ("mp3", "wav", "ogg"):
                        if old_extension not in VALID_INSTANT_THUMBNAILS:
                            thumbnail = "img/audio-placeholder.png"

                        attachment_text += (
                            '\n{{< fancybox path="img/audio-placeholder.png" file="'
                            + attachment
                            + '" caption="Placeholder thumbnail for an audio work." >}}\n'
                        )
                    else:
                        if old_extension not in VALID_INSTANT_THUMBNAILS:
                            thumbnail = "img/other-placeholder.png"

                        attachment_text += (
                            '\n{{< fancybox path="img/other-placeholder.png" file="'
                            + attachment
                            + '" caption="Placeholder thumbnail for a special work." >}}\n'
                        )
                elif "youtu.be" in attachment:
                    code: str = attachment.split("/")[-1]
                    code = code.split("?")[0]

                    attachment_text += "\n{{< youtube " + code + " >}}\n"
                    thumbnail = "img/video-placeholder.png"
                elif "youtube.com" in attachment:
                    code: str = attachment.split("=")[-1]
                    code = code.split("?")[0]

                    attachment_text += "\n{{< youtube " + code + " >}}\n"
                    thumbnail = "img/video-placeholder.png"
                elif "vimeo" in attachment:
                    code: str = attachment.split("/")[-1]
                    code = code.split("?")[0]

                    attachment_text += "\n{{< vimeo " + code + " >}}\n"
                    thumbnail = "img/video-placeholder.png"
                elif "soundcloud" in attachment:
                    attachment_text += f"\n[View on SoundCloud.]({attachment})\n"
                    thumbnail = "img/audio-placeholder.png"
                elif "itch.io" in attachment:
                    attachment_text += f"\n[View on Itch.]({attachment})\n"
                    thumbnail = "img/other-placeholder.png"
                elif "imgur" in attachment:
                    attachment_text += f"\n[View on Imgur.]({attachment})\n"
                    thumbnail = "img/other-placeholder.png"
                elif "docs.google.com" in attachment:
                    attachment_text += f"\n[View on Google Docs.]({attachment})\n"
                    thumbnail = "img/other-placeholder.png"
                elif "webtoons.com" in attachment:
                    attachment_text += f"\n[View on Webtoons.]({attachment})\n"
                    thumbnail = "img/other-placeholder.png"
                else:
                    attachment_text += f"\n[View on External Website.]({attachment})\n"
                    thumbnail = "img/other-placeholder.png"

            # Handle poetry/prose.

            if not submission["attachments"]:
                thumbnail = "img/other-placeholder.png"

                attachment_text += "## Poetry/Prose\n\n"
                attachment_text += "{{< highlight txt >}}\n"
                attachment_text += description.strip()
                attachment_text += "\n{{< /highlight >}}"

            thumbnail_text = f"""
            [[images]]
              src = "{provided_thumbnail or thumbnail}"
              href = "/blog/{submission['id']}"
              alt = "{title}"
              stretch = "cover"
            """.strip()

            # Handle socials.

            user_socials: List[dict] = parsed_json["users"].get(
                submission["author"], []
            )

            socials_list: List[str] = []
            for social in user_socials:
                provider: str = social["provider"]
                username: str = social["username"]

                # Handle parsed but invalid socials:

                if provider.lower() == "everywhere":
                    continue

                # Handle other social providers:

                # tumblr, instagram, twitch, twitter

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
                socials_text = "- N/A."
            else:
                socials_text = "\n".join(socials_list)

            # Write each post to a file using tag substitutions.

            output_post_file.write(
                FRONTMATTER.replace("<!TITLE>", title)
                .replace("<!SHORT_DESCRIPTION>", short_description)
                .replace("<!AUTHOR>", short_author)
                .replace("<!SUBMITTED_DATE>", submission["created_at"])
                .replace(
                    "<!THEME>",
                    f"Week {submission['week']:02d}: {WEEK_TO_THEME_MAP[submission['week']]}",
                )
                .replace("<!WEEK>", str(week_number))
                .replace("<!MEDIUM>", medium)
                .replace("<!ID>", submission["id"])
                .replace("<!SOCIALS>", socials_text)
                .replace("<!DESCRIPTION>", description)
                .replace("<!RAW_DESCRIPTION>", submission["raw_content"])
                .replace("<!THEME_ONLY>", WEEK_TO_THEME_MAP[submission["week"]])
                .replace("<!MEDIA>", attachment_text)
                .replace("<!IMG_SRC>", thumbnail)
                .replace("<!PREVIEW>", thumbnail_text)
            )


if __name__ == "__main__":
    create_all_posts()
