#!/usr/bin/env python3
import os, shutil, pickle, time, sys, logging, argparse, re

# pipe handling
from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE, SIG_DFL)

mpw_ids = [1, 2, 5, 6, 9, 10, 11]
projects_db = 'projects.pkl'
cached_project_dir = 'cached_pages'

# some projects don't have all keys, so set them to none
key_map = {
    'Last MPW Precheck' : 'precheck',
    'Last Tapeout'      : 'tapeout',
    'Git URL'           : 'giturl',
    'MPW'               : 'mpw',
    'Owner'             : 'owner',
    'Process'           : 'process',
    'Summary'           : 'summary',
    'Selected'          : 'selected'
    }

format_map = {
    'id'        : '{:5.5}',
    'precheck'  : '{:10.10}',
    'tapeout'   : '{:10.10}',
    'giturl'    : '{:80.80}',
    'mpw'       : '{:6.6}',
    'owner'     : '{:20.20}',
    'process'   : '{:8.8}',
    'summary'   : '{:80.80}',
    'selected'  : '{:4.4}',
    }


# async code from
# https://gist.github.com/wfng92/2d2ae4385badd0f78612e447444c195f
async def gather_with_concurrency(n, *tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


async def get_async(url, session, results):
    logging.debug("fetching URL %s" % url)
    async with session.get(url) as response:
        i = url.split('/')[-1]
        obj = await response.text()
        results[i] = obj


def get_urls_from_index():
    urls = []
    # shuttle encoding is found from inspecting the link of the 'showcase' button on https://platform.efabless.com/
    for shuttle, mpw in enumerate(mpw_ids):
        data = urllib.parse.urlencode({'filters': f'shuttle_{mpw}'}).encode('utf-8')
        request = urllib.request.Request('https://platform.efabless.com/projects/projects_search_results', data)
        with urllib.request.urlopen(request) as f:
            shuttle_soup = BeautifulSoup(f.read(), 'html.parser')
            paths = [p['href'] for p in shuttle_soup.select('a[href^="/projects/"]')]
            paths = ['https://platform.efabless.com' + x for x in paths]
            logging.info("fetched {} urls for shuttle {}".format(len(paths), shuttle))
        urls += paths
    return urls


async def fetch_project_urls(urls, limit):
    conn = aiohttp.TCPConnector(limit=None, ttl_dns_cache=300)
    session = aiohttp.ClientSession(connector=conn)
    results = {}

    # allow limiting for testing
    if limit != 0:
        urls = urls[0:limit]

    conc_req = 40
    logging.info("starting to fetch async, max requests %d" % conc_req)
    now = time.time()
    await gather_with_concurrency(conc_req, *[get_async(i, session, results) for i in urls])
    time_taken = time.time() - now

    logging.info("time taken = %d s" % time_taken)
    await session.close()

    logging.info("writing all pages to local cache %s" % cached_project_dir)

    if os.path.exists(cached_project_dir):
        shutil.rmtree(cached_project_dir)

    os.makedirs(cached_project_dir)

    for key in results:
        with open(os.path.join(cached_project_dir, key), 'w') as fh:
            fh.write(results[key])


def parse_project_page():
    logging.info("parsing project pages")
    projects = []
    selected = []

    # get list of selected projects
    with open('selected') as fh:
        for id in fh.readlines():
            selected.append(id.strip())

    for filename in os.listdir(cached_project_dir):
        with open(os.path.join(cached_project_dir, filename)) as fh:
            project = {}
            content = fh.read()
            soup = BeautifulSoup(content, 'html.parser')
            assert 'Project Detail | Efabless' in soup.title.text
            divs = soup.find_all("div", {"class": "list-group-item py-2"})
            project['id'] = filename
            logging.info(filename)
            for div in divs:
                key = div.h6.text
                value = div.p.text.strip()
                if key in key_map:
                    project[key_map[key]] = value


            mpw_header = soup.find_all("span",{"class": "text-dark-50 font-weight-bold"})
            if len(mpw_header) > 0:
                project['mpw'] = mpw_header[1].text.strip()

            if project['id'] in selected:
                project['selected'] = 'yes'

            # fill in any blanks
            for key in key_map.values():
                if key not in project:
                    project[key] = 'n/a'

            # remove newlines from summary
            project['summary'] = project['summary'].replace('\n', ' ')

            projects.append(project)

    logging.info("dumping project info to local cache %s" % projects_db)
    with open(projects_db, 'wb') as fh:
        pickle.dump(projects, fh)


def show_project(projects):
    for project in projects:
        for key in project:
            logging.info("{:20}{}".format(key, project[key]))


def list_projects(projects, fields):
    # always include id as first field
    fields = 'id,' + fields
    for project in projects:
        log = ''
        for field in fields.split(','):
            if field in project:
                log += format_map[field].format(project[field])
                log += " "
        logging.info(log)


def list_by_ip(projects, ip):
    ip = re.sub("-", "", ip)
    for project in projects:
        log = ''
        if re.search(ip, project["summary"], re.IGNORECASE):
            for field in ["id", "owner", "giturl"]:
                log += format_map[field].format(project[field])
                if re.search("n/a", log):
                    log = re.sub("n/a", "[github link not found] https://platform.efabless.com/projects/{0}".format(project["id"]), log)
                log += " "
            logging.info(log)


def get_file(projects, path):
    from get_pins import fetch_file_from_git
    for project in projects:
        fetched = fetch_file_from_git(project, path)
        logging.info(project['giturl'])
        print(fetched.decode('utf-8'))


def get_pins_in_lef(projects):
    from get_pins import get_pins
    max_pins = 0
    max_id = None
    for project in projects:
        pins = get_pins(project)
        if pins > max_pins:
            max_pins = pins
            max_id = project["id"]
        logging.info("%-5s %-80s %-5s" % (project["id"], project["giturl"], pins))
    logging.info("max pins was %d in project id %s" % (max_pins, max_id))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Efabless project tool")

    parser.add_argument('--list', help="list basic project info", action='store_const', const=True)
    parser.add_argument('--fields', help="comma separated list of fields to show. To see all available fields, use the --show option", default='mpw,owner,summary,tapeout,selected')
    parser.add_argument('--show', help="show all data for given projects", action='store_const', const=True)
    parser.add_argument('--id', help="select a project by id", type=int)
    parser.add_argument('--get-pins', help="dump number of pins found in user project wrapper lef file", action='store_const', const=True)
    parser.add_argument('--get-file', help="get the specified file from the git repo")
    parser.add_argument('--update-cache', help='fetch the project data', action='store_const', const=True)
    parser.add_argument('--limit-update', help='just fetch the given number of projects', type=int, default=0)
    parser.add_argument('--debug', help="debug logging", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.INFO)
    parser.add_argument('--ip', help="get the list of all projects that has relation with the IP", type=str)
    args = parser.parse_args()

    # change directory to the script's path
    os.chdir((os.path.dirname(os.path.realpath(__file__))))

    # setup log
    log_format = logging.Formatter('%(message)s')
    # configure the client logging
    log = logging.getLogger('')
    # has to be set to debug as is the root logger
    log.setLevel(args.loglevel)

    # create console handler and set level to info
    ch = logging.StreamHandler(sys.stdout)
    # create formatter for console
    ch.setFormatter(log_format)
    log.addHandler(ch)

    # load projects from cache
    try:
        projects = pickle.load(open(projects_db, 'rb'))
    except FileNotFoundError:
        logging.error("project cache %s not found, use --update-cache to build it" % projects_db)

    # sort the projects by ID

    projects.sort(key=lambda x: int(x['id']))

    # handle ID selection by stdin
    if not sys.stdin.isatty():
        pre_filtered_projects = projects
        projects = []
        lines = sys.stdin.readlines()
        for line in lines:
            m = re.search(r'^(\d+)\s', line)
            if m is not None:
                for project in pre_filtered_projects:
                    if project['id'] == m.group(1):
                        projects.append(project)

    # handle ID by argument
    if args.id:
        for project in projects:
            if project['id'] == str(args.id):
                projects = [project]

    # deal with arguments
    if args.list:
        list_projects(projects, args.fields)

    elif args.show:
        show_project(projects)

    elif args.get_pins:
        get_pins_in_lef(projects)

    elif args.get_file:
        get_file(projects, args.get_file)

    elif args.ip:
        list_by_ip(projects, args.ip)

    elif args.update_cache:
        from bs4 import BeautifulSoup
        import asyncio
        import aiohttp
        import urllib
        #urls = get_urls_from_index()
        #asyncio.run(fetch_project_urls(urls, args.limit_update))
        projects = parse_project_page()

    else:
        parser.print_help()
