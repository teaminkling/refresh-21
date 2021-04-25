"""Using an input JSON, writes Markdown blog posts representing submissions."""

# TODO: Social links must be removed from the final blog post.
# TODO: blog posts need to be spaced correctly.
# TODO: thumbnail algorithm needs to be created.

import json

FRONTMATTER: str = """
+++
title = "<!TITLE>"
description = "<!SHORT_DESCRIPTION>"
author = "<!AUTHOR>"
date = "<!SUBMITTED_DATE>"
categories = ["<!THEME>"]
tags = []
+++
""".strip()


def create_all_posts():
    with open("out/parsed.json") as parsed_json_file:
        parsed_json: dict = json.load(parsed_json_file)

    for submission in parsed_json["submissions"]:
        filename: str = f"{submission['id']}.md"

        with open(f"../blog/content/blog/{filename}", "w") as output_post_file:
            description: str = submission["description"]
            short_description: str = description

            if len(description) > 256:
                short_description = f"{description[:255]}..."

            short_description = short_description.replace(
                "\n", " ",
            ).replace(
                "\\", "\\\\",
            ).replace(
                '"', "\\\"",
            )

            output_post_file.write(
                FRONTMATTER.replace("<!TITLE>", submission["title"])
                .replace("<!SHORT_DESCRIPTION>", short_description)
                .replace("<!AUTHOR>", submission["author"])
                .replace("<!SUBMITTED_DATE>", submission["created_at"])
                .replace("<!THEME>", f"Week {int(submission['week']):02d}: TODO")
            )

            output_post_file.write("\n\n")
            output_post_file.write(submission["description"])
            output_post_file.write("\n")


if __name__ == "__main__":
    create_all_posts()
