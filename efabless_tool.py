#!/usr/bin/env python3
from bs4 import BeautifulSoup
from scrapingant_client import ScrapingAntClient
import os
import asyncio
import aiohttp
import time
import requests
from tokens import scraping_token
import logging,sys

# setup log
log_format = logging.Formatter('%(asctime)s - %(module)-15s - %(levelname)-8s - %(message)s')
# configure the client logging
log = logging.getLogger('')
# has to be set to debug as is the root logger
log.setLevel(logging.INFO)

# create console handler and set level to info
ch = logging.StreamHandler(sys.stdout)
# create formatter for console
ch.setFormatter(log_format)
log.addHandler(ch)

index_cache = "index.html"
index_url = 'https://platform.efabless.com/projects/public'
project_base_url = 'https://platform.efabless.com'
cached_project_dir = 'cached_pages'

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
def get_index():
    if os.path.exists(index_cache):
        logging.info("using cached index")
        with open(index_cache) as fh:
            return fh.read()
    else:
        logging.info("making request to scraping ant for url %s, takes around 10 seconds" % index_url)

        # Create a ScrapingAntClient instance
        client = ScrapingAntClient(token=scraping_token)

        # Get the HTML page rendered content
        page_content = client.general_request(index_url).content
        with open(index_cache, 'w') as fh:
            fh.write(page_content)
        logging.info("done, writing to cache")
        return page_content

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

async def fetch_project_urls(urls):
    conn = aiohttp.TCPConnector(limit=None, ttl_dns_cache=300)
    session = aiohttp.ClientSession(connector=conn)
    results = {}

    conc_req = 100
    logging.info("starting to fetch async")
    now = time.time()
    await gather_with_concurrency(conc_req, *[get_async(i, session, results) for i in urls])
    time_taken = time.time() - now

    logging.info("time taken = %d s" % time_taken)
    await session.close()

    logging.info("writing all pages to local cache %s" % cached_project_dir)
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
            for div in divs:
                key = div.h6.text
                value = div.p.text
                project[key] = value

    logging.info("done")
    return projects

page_content = get_index()
urls = parse_index(page_content)
#asyncio.run(fetch_project_urls(urls))
projects = parse_project_page()

