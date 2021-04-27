## web-refresh

Source code for the `#2021DesignRefresh`'s supplementary software tools and marketing web frontend.

## Components

### Discord Bot (`/bot`)

This Discord Bot lives in Cindy's server and allows us to grab all the posts in the `#submissions` channel 
programmatically.

Despite it being called a "bot" it does not display as online in the Discord server. It is solely used to access 
Discord's authenticated public API.

All files are directly invoked without arguments on the command line. It is a typical `Pipenv` project.

`parser.py` and `writer.py` also handling the parsing of raw Discord-retrieved content and writing of blog posts 
respectively.

### Showcase Website (`/blog`)

A static website powered by the [Hugo](https://gohugo.io/) static site generator.

#### Build

Obviously, you need `hugo`. Once you have that, to run the development server, run:

```shell
hugo server
```

#### Deploy

Each push to `main` causes a re-build and re-deploy of the server using GitHub Actions. As of writing, each 
deployment takes around about 5 minutes from the push until it hits production.
