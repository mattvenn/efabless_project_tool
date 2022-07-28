#!/usr/bin/env python3
from bs4 import BeautifulSoup
from scrapingant_client import ScrapingAntClient
import os
import asyncio
import aiohttp
import time
import requests
from tokens import scraping_token

index_cache = "index.html"
index_url = 'https://platform.efabless.com/projects/public'

# async code from https://gist.github.com/wfng92/2d2ae4385badd0f78612e447444c195f
async def gather_with_concurrency(n, *tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


async def get_async(url, session, results):
    async with session.get(url) as response:
        i = url.split('/')[-1]
        obj = await response.text()
        results[i] = obj



def get_index():
    # Launch the browser

    if os.path.exists(index_cache):
        with open(index_cache) as fh:
            return fh.read()
    else:
        print("making request to scraping ant for url %s, takes around 10 seconds" % index_url)

        # Create a ScrapingAntClient instance
        client = ScrapingAntClient(token=scraping_token)

        # Get the HTML page rendered content
        page_content = client.general_request(index_url).content
        with open(index_cache, 'w') as fh:
            fh.write(page_content)
        print("done")
        return page_content

def parse_index(page_content):
    soup = BeautifulSoup(page_content, 'html.parser')
    divs = soup.find_all("div", {"class": "col-12 col-md-6 col-xl-4 col-xxl-3 mb-3"})
    urls = []
    for div in divs:
        url = div.find("a").get('href')
        urls.append(url)

    print("found %d urls" % len(urls))
    return urls

async def main(urls):
    conn = aiohttp.TCPConnector(limit=None, ttl_dns_cache=300)
    session = aiohttp.ClientSession(connector=conn)
    results = {}

    conc_req = 40
    print("starting to fetch")
    now = time.time()
    await gather_with_concurrency(conc_req, *[get_async(i, session, results) for i in urls])
    time_taken = time.time() - now

    print(time_taken)
    await session.close()

    for key in results:
        print(key)
        soup = BeautifulSoup(results[key], 'html.parser')
        print(soup.title)
        divs = soup.find_all("div", {"class": "list-group-item py-2"})
        print(len(divs))
        print(divs[0].h6)
        print(divs[0].p)

page_content = get_index()
urls = parse_index(page_content)
asyncio.run(main(urls))
