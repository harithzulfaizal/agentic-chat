import re
import yaml
import os
import ssl
from typing import List, Optional
from functools import lru_cache
from googlesearch import search
import httpx
from bs4 import BeautifulSoup
import markdownify
import asyncio
from pydantic import BaseModel
from openai import AsyncOpenAI
from aiohttp import ClientSession, TCPConnector
from cachetools import TTLCache
from ratelimit import limits, sleep_and_retry

# Cache for URLs, TTL of 1 hour
url_cache = TTLCache(maxsize=100, ttl=3600)

class WebPage(BaseModel):
    url: str
    content: str
    timestamp: float

# Load config once at module level
def load_config():
    with open(os.getenv("MODEL_CONFIG_PATH"), "r") as file:
        configs = yaml.safe_load(file)
        return configs["models"]["gpt-4o-mini"]

model_config = load_config()
async_client = AsyncOpenAI(api_key=model_config["config"]["api_key"])

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Rate limiting decorator
@sleep_and_retry
@limits(calls=10, period=1)  # 10 requests per second
@lru_cache(maxsize=100)
async def fetch_url(url: str, session: ClientSession) -> Optional[str]:
    try:
        async with session.get(url, timeout=5, ssl=ssl_context) as response:
            if response.status == 200:
                return await response.text()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

async def extract_content(html: str, query: str) -> Optional[str]:
    if not html:
        return None
    
    soup = BeautifulSoup(html, "lxml")  # lxml is faster than html.parser
    
    # Remove unnecessary elements
    for tag in soup.find_all(['script', 'style', 'nav', 'footer']):
        tag.decompose()
    
    content = str(soup.body) if soup.body else str(soup)
    markdown = markdownify.markdownify(content, heading_style="ATX")
    
    try:
        completion = await async_client.chat.completions.create(
            model=model_config["config"]["model"],
            messages=[{
                "role": "user", 
                "content": f"Summarize the following content in 300 words specifically for information related to the '{query}':\n{markdown}"
            }],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error summarizing content: {e}")
        return None

async def get_relevant_web_pages(query: str) -> List[WebPage]:
    url_pattern = re.compile(
        r"^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!$&'()*+,;=.]+$",
        re.IGNORECASE,
    )

    urls = [query] if bool(url_pattern.match(query)) else list(search(query, num_results=3, region="my"))
    
    async with ClientSession(connector=TCPConnector(limit=5, ssl=ssl_context)) as session:
        tasks = []
        for url in urls:
            if url in url_cache:
                tasks.append(url_cache[url])
            else:
                task = asyncio.create_task(fetch_url(url, session))
                tasks.append(task)
                
        htmls = await asyncio.gather(*tasks)
        
        content_tasks = [
            extract_content(html, query) 
            for html, url in zip(htmls, urls) 
            if html
        ]
        
        contents = await asyncio.gather(*content_tasks)
        
        results = []
        for url, content in zip(urls, contents):
            if content:
                webpage = WebPage(
                    url=url,
                    content=content,
                    timestamp=asyncio.get_event_loop().time()
                )
                url_cache[url] = webpage
                results.append(webpage)
                
        return results