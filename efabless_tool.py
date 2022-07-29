#!/usr/bin/env python3
from bs4 import BeautifulSoup
from selenium import webdriver
from scrapingant_client import ScrapingAntClient
import os, shutil, pickle, time, sys, logging, argparse
import asyncio
import aiohttp
import requests
from tokens import scraping_token

projects_db = 'projects.pkl'
index_url = 'https://platform.efabless.com/projects/public'
project_base_url = 'https://platform.efabless.com'
cached_project_dir = 'cached_pages'

# some projects don't have all keys, so set them to none
minimum_project_keys = ['Last MPW Precheck', 'Last Tapeout', 'Git URL', 'MPW']

# async code from https://gist.github.com/wfng92/2d2ae4385badd0f78612e447444c195f
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

# uses scraping ant web service because index page is dynamically generated and pyppeteer, playwright didn't work
def get_urls_from_index():
    logging.info("making request with selenium controlled chrome for url %s" % index_url)


    driver = webdriver.Chrome()
    driver.get(index_url)

    for i in range(10):
        page_content = driver.page_source
        urls = parse_index(page_content)
        if len(urls) != 0:
            break
        logging.info("waiting for page to load")
        time.sleep(1.0)
    else: 
        logging.error("couldn't fetch URLs")
        exit(1)

    return urls

def parse_index(page_content):
    logging.info("parsing index for project URLs")
    soup = BeautifulSoup(page_content, 'html.parser')
    divs = soup.find_all("div", {"class": "col-12 col-md-6 col-xl-4 col-xxl-3 mb-3"})
    urls = []
    for div in divs:
        url = div.find("a").get('href')
        urls.append(project_base_url + url)

    logging.info("found %d urls" % len(urls))
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
                project[key] = value

            mpw_header = soup.find("h1", {"class": "card-label h1 font-weight-bold pt-3 text-center"})
            if mpw_header is not None:
                project['MPW'] = mpw_header.text.strip()

            for key in minimum_project_keys:
                if not key in project:
                    project[key] = None

            projects.append(project)

    logging.info("dumping project info to local cache %s" % projects_db)
    with open(projects_db, 'wb') as fh:
        pickle.dump(projects, fh)

def show_project(projects, id):
    for project in projects:
        if project['id'] == id:
            for key in project:
                logging.info("%-20s = %s" % (key, project[key]))

def list_projects(projects):
    for project in projects:
        logging.info("%-5s %-5s %-40s %-10s %-10s" % (project["id"], project["MPW"], project["Owner"], project["Last MPW Precheck"], project["Last Tapeout"]))

def get_pins_in_lef(projects):
    from get_pins import get_pins
    max_pins = 0
    max_id = None
    for project in projects:
        if not project["Last Tapeout"] == "Succeeded":
            continue
   
        pins = get_pins(project)
        if pins > max_pins:
            max_pins = pins
            max_id = project["id"]
        logging.info("%-5s %-80s %-5s" % (project["id"], project["Git URL"], pins))
    logging.info("max pins was %d in project id %s" % (max_pins, max_id))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Efabless project tool")

    parser.add_argument('--list', help="list basic project info", action='store_const', const=True)
    parser.add_argument('--show', help="show all data for a specific project")
    parser.add_argument('--get-pins', help="dump number of pins found in user project wrapper lef file", action='store_const', const=True)
    parser.add_argument('--update-cache', help='fetch the project data', action='store_const', const=True)
    parser.add_argument('--limit-update', help='just fetch the given number of projects', type=int, default=0)
    parser.add_argument('--debug', help="debug logging", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.INFO)

    args = parser.parse_args()

    # setup log
    log_format = logging.Formatter('%(asctime)s - %(levelname)-8s - %(message)s')
    # configure the client logging
    log = logging.getLogger('')
    # has to be set to debug as is the root logger
    log.setLevel(args.loglevel)

    # create console handler and set level to info
    ch = logging.StreamHandler(sys.stdout)
    # create formatter for console
    ch.setFormatter(log_format)
    log.addHandler(ch)

    if args.update_cache:
        urls = get_urls_from_index()
        asyncio.run(fetch_project_urls(urls, args.limit_update))
        projects = parse_project_page()

    try:
        projects = pickle.load(open(projects_db, 'rb'))
    except FileNotFoundError:
        logging.error("project cache %s not found, use --update-cache to build it" % projects_db)

    # sort the projects by id
    projects.sort(key=lambda x: int(x['id']))

    logging.debug("debug")
    if args.list:
        list_projects(projects)

    if args.show:
        show_project(projects, args.show)

    if args.get_pins:
        get_pins_in_lef(projects)
