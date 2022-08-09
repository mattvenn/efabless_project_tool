# Efabless Project Tool

Efabless don't yet have an API, so I've written this as a quick hack to get bulk project data from the Google sponsored MPW projects.

Also, while there are around 600 public projects (As of July 2022), only 240ish have been selected to be made. The selected status isn't
a secret but it's also not easily available, so I have put a list of (most of) the ids in the [selected](selected) file, which is merged
into the data from the website. I'll manually update this after every shuttle selection.

# Watch the demo!

https://youtu.be/laAQLVO7aQo

# Example use

List all projects along with tapeout and precheck status:

    ./efabless_tool.py --list                       

Show only mpw and process for all projects:

    ./efabless_tool.py --list --fields mpw,process  

Show all fields for project 1000:

    ./efabless_tool.py --id 1000 --show

Update the cache - requires the selenium setup, takes about 3 minutes.

    ./efabless_tool.py --update
Get max number of pins in a user project's macros (needs GitHub token)

    ./efabless_tool.py --get-pin                    

How many public projects are there?

    ./efabless_tool.py --list | wc -l

How many successful tapeouts by me on Sky130B process?

    ./efabless_tool.py --list --fields owner,tapeout,process | grep Matt | grep Succeeded | grep 130B

How many reram projects were selected to be manufactured?

    ./efabless_tool.py --list --field summary,selected | grep -i reram | grep yes

Use the built in search:

    ./efabless_tool.py --ip op-amp
    
## Get Pin

For each project:

* fetch the def file of user_project_wrapper from the git repo,
* use [def_parser](/blob/sel_set/def/user_project_wrapper.def) to get macros,
* count occurences of PIN in each macro lef,
* return biggest count.

Only works if user_project_wrapper.def and all macro.lefs are commited to the repo.

# To set up

The tool comes with a database of projects, that will go out of date. If you want to refresh the cache, you
will need to install the dependencies.

## Install Python dependencies

    pip3 install -r requirements.txt

## Install Selenium Driver

Efabless index page is dynamically generated and can't be fetched with a simple get.
I tried pyppeteer and playwright, Scraping Ant and finally Selenium.

You will need to install the driver that works with the browser you have installed, see these instructions: https://selenium-python.readthedocs.io/installation.html.

## GitHub token

If you want to use the GitHub functionality (currently only used for the get-pin option), you'll also need a git_token and git_username added to tokens.py. Get yours from https://github.com/settings/tokens/new

    git_token = "token"
    git_username = "username"

This gives you 5000 requests per hour.

# Credits

* async URL fetch code from https://gist.github.com/wfng92/2d2ae4385badd0f78612e447444c195f
* lef/def parser from TrimCao https://github.com/trimcao/lef-parser

# License

[Apache 2](LICENSE)
