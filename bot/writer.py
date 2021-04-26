"""Using an input JSON, writes Markdown blog posts representing submissions."""

# TODO: Social links must be removed from the final blog post.

import json
from typing import Dict, List

GITHUB_REPO_URL: str = "https://github.com/teaminkling/web-refresh"

GITHUB_EDIT_URL: str = f"{GITHUB_REPO_URL}/edit/main/blog/content/blog/"

GITHUB_BUG_URL: str = (
    f"{GITHUB_REPO_URL}/issues/new?assignees=&labels=bug&template=problem-report.md&title="
)

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
categories =  ["<!THEME>"]
tags =        ["<!AUTHOR>"]
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

{{{{< highlight markdown >}}}}
<!RAW_DESCRIPTION>
{{{{< /highlight >}}}}
""".strip()


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
    10: "Folds & Folds",
    11: "Atmos. Spectrum",
    12: "Visual Words",
    13: "Look At Me",
    14: "Absolute Fire",
    15: "Back to Basics",
    16: "Scaling Giants",
    17: "The 4 R's",
}
"""A mapping from the week integer to the name of the theme."""


def create_all_posts():
    with open("out/parsed.json") as parsed_json_file:
        parsed_json: dict = json.load(parsed_json_file)

    for submission in parsed_json["submissions"]:
        filename: str = f"{submission['id']}.md"

        with open(f"../blog/content/blog/{filename}", "w") as output_post_file:
            # Extract some shorthand information.

            week_number: int = submission["week"]
            theme_name: str = WEEK_TO_THEME_MAP[submission['week']]
            short_author: str = submission["author"][:-5]
            description: str = submission["description"]
            medium: str = submission["medium"] or "unknown medium"

            # Handle invalid values.

            title = submission["title"].replace("_", "").replace("*", "").replace('"', "")
            medium = medium.replace('"', "")

            # Determine a short description.

            short_description: str = (
                f"\\\"{title}\\\" is a work by {short_author} for week {week_number}: "
                f"{theme_name}. This art was lovingly-created using medium: {medium}."
            )

            # Determine the media to show.

            # TODO: all of these require a thumbnail image of some sort.
            #       images and gifs are easy, but videos we need to "get" a thumbnail for as well
            #       as youtube, vimeo, and others. Is it even possible?

            attachment_text: str = ""
            thumbnail: str = ""
            for attachment in submission["attachments"]:
                if "blog/static" in attachment:
                    # TODO: PDF handling.

                    attachment = attachment.replace("../blog/static", "")

                    attachment_text += (
                        "\n{{< fancybox path=\"/\" file=\"" + attachment + "\" >}}\n"
                    )

                    thumbnail = attachment
                elif "youtu.be" in attachment:
                    code: str = attachment.split("/")[-1]
                    code = code.split("?")[0]

                    attachment_text += "\n{{< youtube " + code + " >}}\n"
                elif "youtube.com" in attachment:
                    code: str = attachment.split("=")[-1]
                    code = code.split("?")[0]

                    attachment_text += "\n{{< youtube " + code + " >}}\n"
                elif "vimeo" in attachment:
                    code: str = attachment.split("/")[-1]
                    code = code.split("?")[0]

                    attachment_text += "\n{{< vimeo " + code + " >}}\n"
                elif "soundcloud" in attachment:
                    attachment_text += f"\n[View on SoundCloud.]({attachment})\n"
                elif "itch.io" in attachment:
                    attachment_text += f"\n[View on Itch.]({attachment})\n"
                elif "imgur" in attachment:
                    attachment_text += f"\n[View on Imgur.]({attachment})\n"
                elif "docs.google.com" in attachment:
                    attachment_text += f"\n[View on Google Docs.]({attachment})\n"
                elif "webtoons.com" in attachment:
                    attachment_text += f"\n[View on Webtoons.]({attachment})\n"
                else:
                    attachment_text += f"\n[View on External Website.]({attachment})\n"

            # Handle thumbnail types and edit the title if required.

            thumbnail_text: str = ""
            if thumbnail and "." in thumbnail:
                extension: str = thumbnail.split(".")[-1]

                if extension in ("png", "jpg", "svg", "jpeg", "bmp", "gif"):
                    thumbnail_text = f"""
                    [[images]]
                      src = "{thumbnail}"
                      alt = "{thumbnail}"
                      stretch = "cover"
                    """.strip()
                else:
                    pass  # TODO

            # Handle socials.

            user_socials: List[dict] = parsed_json["users"].get(submission["author"], [])

            socials_text: str = ""
            for social in user_socials:
                provider: str = social["provider"]
                username: str = social["username"]

                socials_text += f"- **{provider}**: [{username}]()\n"

            if not socials_text:
                socials_text = "- N/A."

            # Write each post to a file using tag substitutions.

            output_post_file.write(
                FRONTMATTER.replace("<!TITLE>", title)
                .replace("<!SHORT_DESCRIPTION>", short_description)
                .replace("<!AUTHOR>", short_author)
                .replace("<!SUBMITTED_DATE>", submission["created_at"])
                .replace(
                    "<!THEME>",
                    f"W{submission['week']:02d}: {WEEK_TO_THEME_MAP[submission['week']]}"
                )
                .replace("<!WEEK>", str(week_number))
                .replace("<!MEDIUM>", medium)
                .replace("<!ID>", submission["id"])
                .replace("<!SOCIALS>", socials_text)
                .replace("<!DESCRIPTION>", description)
                .replace("<!RAW_DESCRIPTION>", submission["raw_content"])
                .replace("<!THEME_ONLY>", WEEK_TO_THEME_MAP[submission['week']])
                .replace("<!MEDIA>", attachment_text)
                .replace("<!IMG_SRC>", thumbnail)
                .replace("<!PREVIEW>", thumbnail_text)
            )


if __name__ == "__main__":
    create_all_posts()
