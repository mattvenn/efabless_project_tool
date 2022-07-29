# Efabless Project Tool

Efabless don't yet have an API, so I've written this as a quick hack to get bulk project data from the Google sponsored MPW projects.

# To set up

## Install Python dependencies

    pip3 install -r requirements.txt

## Install Selenium Driver

Efabless index page is dynamically generated and can't be fetched with a simple get.
I tried pyppeteer and playwright, Scraping Ant and finally Selenium.

You will need to install the driver that works with the browser you have installed, see these instructions: https://selenium-python.readthedocs.io/installation.html.

I have commited the pickled database [projects.pkl](projects.pkl), so you can just use that, but it will go out of date.

## GitHub token

If you want to use the GitHub functionality, you'll also need a git_token and git_username added to tokens.py. Get yours from https://github.com/settings/tokens/new

    git_token = "token"
    git_username = "username"

This gives you 5000 requests per hour. When it runs out, you won't know unless you use --verbose

# Use

    ./efabless_tool.py --list                       # list all projects along with tapeout and precheck status

    ./efabless_tool.py --update                     # update the cache - requires the scraping ant token

    ./efabless_tool.py --get-pin                    # get max number of pins in a user project's macros (needs GitHub token)

    ./efabless_too.py --list --fields mpw,process   # show only mpw and process for all projects

Also accepts project IDs on the standard input, so you can build pipelines like

    ./efabless_tool.py --list --fields owner,tapeout,process | grep Matt | grep Succeeded | grep 130B

Which would show only successful tapeouts by me on Sky130B process.

## Get Pin

For each project that has a successful tapeout:

* fetching the def file of user_project_wrapper from the git repo
* use def_parser to get macros
* count occurences of PIN in each macro lef
* return biggest count.

Only works if user_project_wrapper.def and all macro.lefs are commited to the repo.

# Credits

* async URL fetch code from https://gist.github.com/wfng92/2d2ae4385badd0f78612e447444c195f
* lef/def parser from TrimCao https://github.com/trimcao/lef-parser

# License

[Apache 2](LICENSE)
