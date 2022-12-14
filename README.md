# Project is out of date and doesn't work anymore.

The website changes too much for me to keep the scraping up to date.


# Efabless Project Tool

Efabless don't yet have an API, so I've written this as a quick hack to get bulk project data from the Google sponsored MPW projects.

Also, while there are around 700 public projects (As of September 2022), only 240ish have been selected to be made. The selected status isn't
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

Print the macro.cfg for all projects on MPW7 that have passed tapeout (requires github token, see below)

    ./efabless_tool.py  --list | egrep MPW-7.*Succeeded | ./efabless_tool.py --get-file openlane/user_project_wrapper/macro.cfg
    
## Get Pin

For each project:

* fetch the def file of user_project_wrapper from the git repo,
* use [def_parser](/blob/sel_set/def/user_project_wrapper.def) to get macros,
* count occurences of PIN in each macro lef,
* return biggest count.

Only works if user_project_wrapper.def and all macro.lefs are commited to the repo.

# To refresh the cache

The [GitHub Action](.github/workflows/efabless_tool.yaml) runs every night to rebuild the cache. So you just need to do a `git pull` in your cloned repo to update.

## Manually refresh the cache

    pip3 install -r requirements.txt
    ./efabless_tool.py --update-cache # takes a few minutes

## GitHub token

If you want to use the GitHub functionality (currently only used for the get-pin option), you'll also need a git_token and git_username added to tokens.py. Get yours from https://github.com/settings/tokens/new . You don't need to tick any boxes in the form, the default is fine.

    git_token = "token"
    git_username = "username"

This gives you 5000 requests per hour.

# Credits

* async URL fetch code from https://gist.github.com/wfng92/2d2ae4385badd0f78612e447444c195f
* lef/def parser from TrimCao https://github.com/trimcao/lef-parser

# License

[Apache 2](LICENSE)
