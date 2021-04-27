+++
title = "About"
description = "So, what is the 2021 Design Refresh, anyway?"
author = "FiveClawD"
date = "2021-04-26"
layout = "about"
+++

## Refwesh

![](/img/clown.png)

Cindy is a professional clown, freelance graphic designer, and Twitch streamer.

The 2021 Design Refresh is a community centered weekly art challenge.  It ran online from January to May and was 
organised by Cindy Xu. This website hosts the themes and showcases all the entries from the #2021DesignRefresh.

## For Nerds

This site was written and deployed by me. Ya boi. [Thomas "papapastry" Wang](/artists/papapastry/).

It uses a three-stage Python pipeline to create Markdown files, and uses the Go programming language with the Hugo 
static site generator (SSG) to process and create blog posts representing submissions.

The stages are:

- Extract from Discord all submissions.
- Use a complex algorithm to parse submissions into a structured format.
  - This part also does thumbnail generation which is required because these artists don't know the meaning of the 
    word "restraint" when they send in 99 MB submissions.
  - Just kidding. Not going to butcher art, but the list views need to be faster for viewers, especially on mobile.
- Format the parsed output into blog posts.

The benefit of SSGs is that hosting more than 1.5 gigabytes of files on a server is very expensive and slow. SSGs 
don't require application servers at all, meaning you're essentially just getting raw files. It's kinda magical: the 
search feature, for example, works by processing all possible data, indexing it on each build before a user performs 
a search. No external HTTP calls are made.

Stonks.

## Site's Fucked

Ah shit.

There are edge cases when dealing with unstructured user data. There are cases that fell through the cracks. If you 
find any of these, feel free to [raise a bug ticket][bug-report].

You can see upcoming features and bug fixes in [GitHub Issues][issues-list], if you're interested.

[bug-report]: https://github.com/teaminkling/web-refresh/issues/new?assignees=&labels=bug&template=problem-report.md
[issues-list]: https://github.com/teaminkling/web-refresh/issues
