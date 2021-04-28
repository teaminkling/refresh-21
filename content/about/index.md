+++
title = "About"
description = "So, what is the 2021 Design Refresh, anyway?"
author = "FiveClawD"
date = "2021-04-26"
layout = "about"
+++

## Refwesh?

![](/img/clown.png)

Cindy is a professional clown, freelance graphic designer, and Twitch streamer.

The 2021 Design Refresh is a community centered weekly art challenge.  It ran online from January to May and was 
organised by Cindy Xu. This website hosts the themes and showcases all the entries from the #2021DesignRefresh.

## Site Updates

The site is updated automatically on changes to the individual blog pages in around 5 to 10 minutes after the change 
is made. The blog pages, however, are parsed from Discord. This happens about once a day.

Every time a change is made, we review the metafile changes to see what has changed. It is _incredibly easy_ to see 
if somebody is trying to troll the system so just be careful with what content is uploaded please.

If you would like a change on next site update in 24 to 48 hours, then just edit the Discord post you initially 
posted. Otherwise, you can directly use the "suggest an edit" link on any page or contact the developer 
(papapastry#8888) directly to have problems fixed faster.

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
