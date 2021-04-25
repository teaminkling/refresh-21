## web-refresh

Source code for the `#2021DesignRefresh`'s supplementary software tools and marketing web frontend.

## Components

### Discord Bot (`/bot`)

This Discord Bot lives in Cindy's server and allows us to grab all the posts in the `#submissions` channel 
programmatically.

Despite it being called a "bot" it does not display as online in the Discord server. It is solely used to access 
Discord's authenticated public API.

All files are directly invoked without arguments on the command line. It is a typical `Pipenv` project.

### Showcase Website (`/blog`)

A static website powered by the [Hugo](https://gohugo.io/) static site generator based on the
[Codex theme](https://github.com/jakewies/hugo-theme-codex) created  and maintained by
[Jake Wiesler](https://github.com/jakewies).

#### Build

To run the development server:

```shell
brew install hugo
hugo server -D
```

#### Deploy

Each push to `main` causes a re-build and re-deploy of the server using GitHub Actions. Should you want to manually 
build during local development:

```shell
# TBD
```

#### Customisation

- Home page:

The site's home page can be configured by creating a `content/_index.md` file. This file can use the following
frontmatter:

```md
---
heading: "Hi, I'm Codex"
subheading: "A minimal blog theme for hugo."
handle: "hugo-theme-codex"
---
```

- Social Icons:

```toml
# config.toml

[params]
  twitter = "https://twitter.com/GoHugoIO"
  github = "https://github.com/jakewies/hugo-theme-codex"
  # ...

  iconOrder = ["Twitter", "GitHub"]
```

These will be placed in the footer.

You can also create additional social icons by:

1. Adding your own SVGs in `static/svg/`, for example `static/svg/reddit.svg`.
2. Modifying your site's config as follows:
   ```toml
   [params]
      # ...
      reddit = "<url to your reddit>"
   
      iconOrder = ["Reddit"]
   ```

Make sure that the icon title must match the icon's file name. If the title contains more than one word, e.g., "My 
Awesome Site", you can use a hyphen for the icon name: `my-awesome-site.svg`. 

#### Posts/Submissions

You can manually create a new blog post page by going to the root of your project and typing:

```
hugo new blog/:blog-post.md
```

Where `:blog-post.md` is the name of the file of your new post. 

This will execute the theme's `blog` archetype to create a new markdown file in `contents/blog/:blog-post.md` with
the following frontmatter:

```md
# Default post frontmatter:

# The title of your post. Default value is generated
# From the markdown filename
title: "{{ replace .TranslationBaseName "-" " " | title }}"
# The date the post was created
date: {{ .Date }}
# The post filename
slug: ""
# Post description used for seo
description: ""
# Post keywords used for seo
keywords: []
# If true, the blog post will not be included in static build
draft: true
# Categorize your post with tags
tags: []
# Uses math typesetting
math: false
# Includes a table of contents on screens >1024px
toc: false
```

The frontmatter above is the default for a new post, but all values can be changed.

#### Sections

In your site's `config.toml`, add a new menu definition for say, "photos":
```toml
# config.toml

[[menu.main]]
    identifier = "photos"
    name = "photos"
    title = "Photos"
    url = "/photos"
```

Then, put your posts under "content/photos". 

#### Styles

You have two options for custom styling. The first is to create an `assets/scss/custom.scss` in your project and put
your custom styling there. For example, the snippet below changes the dot's color on your About to blue:

```scss
// custom.scss
.fancy {
  color: #1e88e5;
}
```

You can even use Hugo variables/params in your custom styles too!

```scss
// custom.scss
.fancy {
  color: {{ .Site.Params.colors.fancy | default "#1e88e5" }}
}
```

```toml
# config.toml
[params.colors]
    fancy = "#f06292"
```

The second option is to use the supported scss overrides. You can do this by creating an `assets/scss/overrides/scss`
file in your project. The following overrides are supported:

```scss
// overrides.scss

// The primary accent color used throughout the site
$primary: ''
```

### Tags

Right now the blog uses the `tags` taxonomy for blog posts. You can view all the blog posts of a given tag by going 
to `/tags/:tag-name`, where `:tag-name` is the name of your tag.
