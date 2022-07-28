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

    logging.info(api_url)
    r = requests.get(api_url, headers=headers)
    logging.info("API requests remaining %s" % r.headers['X-RateLimit-Remaining'])
    data = r.json()
    file_content = data['content']
    file_content_encoding = data.get('encoding')
    if file_content_encoding == 'base64':
        file_content = base64.b64decode(file_content).decode()
    return file_content

def get_pins(project):
    # get the basics
    git_url = project['Git URL']
    res = urlparse(git_url)
    _, user_name, repo = res.path.split('/')
    repo = repo.strip('.git')
    
    # fetch the def
    def_file = fetch_file_from_git(user_name, repo, 'def/user_project_wrapper.def')

    # write to temp file for DefParser
    fp = tempfile.NamedTemporaryFile(mode='w')
    fp.write(def_file)
    fp.seek(0)
    d = DefParser(fp.name)
    d.parse()
    macros = []

    # now we have macros
    for macro in d.components.comps:
        macros.append(macro.macro) 

    fp.close()

    # for each macro, fetch the lef
    for macro in macros:
        lef_file = fetch_file_from_git(user_name, repo, 'lef/' + macro + '.lef')
        logging.info(lef_file.count('PIN'))
   
