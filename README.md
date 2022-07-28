# Efabless Project Tool

Efabless don't yet have an API, so I've written this as a quick hack to get bulk project data from the Google sponsored MPW projects.

# To set up

## Install Python dependencies

    pip3 install -r requirements.txt

## Get Scraping Ant token

Efabless index page is dynamically generated and can't be fetched with a simple get.
I tried pyppeteer and playwright, then used Scraping Ant.

You will need to get your own token from https://app.scrapingant.com/login

Then create a file called tokens.py and add a line like:

    scraping_token = "your token"

I have commited the pickled database [projects.pkl](projects.pkl), so you can just use that, but it will go out of date.

## GitHub token

If you want to use the GitHub functionality, you'll also need a git_token and git_username added to tokens.py. Get yours from https://github.com/settings/tokens/new

    git_token = "token"
    git_username = "username"

# Use

    ./efabless_tool.py --list   # list all projects along with tapeout and precheck status

    ./efabless_tool.py --update # update the cache - requires the scraping ant token

# Credits

* async URL fetch code from https://gist.github.com/wfng92/2d2ae4385badd0f78612e447444c195f

# License

[Apache 2](LICENSE)
