import base64
from tokens import git_token, git_username
from urllib.parse import urlparse
from def_parser import DefParser
import logging
import requests
import tempfile

def fetch_file_from_git(user_name, repo, path):
    # authenticate for rate limiting
    auth_string = git_username + ':' + git_token
    encoded = base64.b64encode(auth_string.encode('ascii'))
    headers = {"authorization" : 'Basic ' + encoded.decode('ascii')}
    api_url = 'https://api.github.com/repos/%s/%s/contents/%s' % (user_name, repo, path)

    logging.debug(api_url)
    r = requests.get(api_url, headers=headers)
    requests_remaining = int(r.headers['X-RateLimit-Remaining'])
    if requests_remaining == 0:
        logging.error("no API requests remaining")
        exit()
        
    logging.debug("API requests remaining %d" % requests_remaining)
    data = r.json()
    if 'content' not in data:
        logging.warning("file %s not found in repo %s" % (repo, path))
        return None
    file_content = data['content']
    file_content_encoding = data.get('encoding')
    if file_content_encoding == 'base64':
        file_content = base64.b64decode(file_content).decode()
    return file_content

def get_pins(project):
    # get the basics
    git_url = project['Git URL']
    res = urlparse(git_url)
    try:
        _, user_name, repo = res.path.split('/')
    except ValueError:
        logging.error("couldn't split repo from %s" % git_url)
        return 0

    repo = repo.strip('.git')
    
    # fetch the def
    def_file = fetch_file_from_git(user_name, repo, 'def/user_project_wrapper.def')
    if def_file is None:
        return 0

    # write to temp file for DefParser
    fp = tempfile.NamedTemporaryFile(mode='w')
    fp.write(def_file)
    fp.seek(0)
    d = DefParser(fp.name)
    d.parse()
    fp.close()
    macros = []

    # now we have macros
    try:
        for macro in d.components.comps:
            macros.append(macro.macro) 
    except AttributeError:
        logging.warning("no macros found")
        return 0

    # for each macro, fetch the lef
    max_pin = 0
    for macro in macros:
        lef_file = fetch_file_from_git(user_name, repo, 'lef/' + macro + '.lef')
        if lef_file is None:
            pin_count = 0
        else:
            pin_count = lef_file.count('PIN')

        if pin_count > max_pin:
            max_pin = pin_count
      
    return max_pin
