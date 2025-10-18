import re
import aiohttp
from typing import List

from bs4 import BeautifulSoup, NavigableString
from langchain_core.tools import tool
from langchain_tavily import TavilySearch

# ==============================================================================
# 1. WEB SCRAPER TOOL AND HELPER FUNCTIONS
# ==============================================================================

def convert_html_to_markdown(element):
    """
    Recursively traverses a BeautifulSoup element and its children to convert
    it into simple Markdown text.
    """
    if isinstance(element, NavigableString):
        return element.string.strip()
    
    children_markdown = "".join(convert_html_to_markdown(child) for child in element.children)
    tag_name = element.name

    if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        level = int(tag_name[1])
        return f"\n\n{'#' * level} {children_markdown}\n\n"
    elif tag_name == 'p':
        return f"\n\n{children_markdown}\n\n"
    elif tag_name in ['strong', 'b']:
        return f"**{children_markdown}**"
    elif tag_name in ['em', 'i']:
        return f"*{children_markdown}*"
    elif tag_name == 'li':
        return f"\n* {children_markdown}"
    elif tag_name in ['ul', 'ol']:
        return f"\n\n{children_markdown}\n\n"
    elif tag_name == 'a':
        href = element.get('href', '')
        return f"[{children_markdown}]({href})"
    elif tag_name == 'br':
        return "\n"
    else:
        return children_markdown

@tool
async def web_scraper(url: str) -> str:
    """
    Scrapes the main content of a web page and returns it as structured Markdown text.

    This tool fetches HTML from a given URL, identifies the primary content area
    (like an article or main body), and converts it into clean Markdown. It strips
    away irrelevant elements like scripts, styles, headers, and footers to isolate
    the core information. Use this tool to read the contents of a webpage.

    Args:
        url (str): The single, complete URL of the web page to be scraped.

    Returns:
        str: The cleaned main content of the page in Markdown format. If scraping
             fails due to a network error, inaccessible content, or if the main
             content cannot be identified, it returns an error message detailing the issue.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as response:
                response.raise_for_status()
                html = await response.text()
    except Exception as e:
        return f"Error: A problem occurred while fetching content from the URL: {url}. Details: {e}"

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()

    content_selectors = [
        "article", "main", "[role='main']", "#main-content", "#content", 
        ".main-content", ".post-content", ".entry-content", ".article-body"
    ]
    content_area = next((soup.select_one(s) for s in content_selectors if soup.select_one(s)), soup.body)
    
    if not content_area:
        return "Error: Could not find the main content area on the page."

    markdown_output = convert_html_to_markdown(content_area)
    cleaned_markdown = re.sub(r'\n{3,}', '\n\n', markdown_output).strip()
    return cleaned_markdown

# ==============================================================================
# 2. WEB SEARCH TOOL
# ==============================================================================

FORBIDDEN_KEYWORDS = {
    "403 forbidden", "access denied", "captcha",
    "has been denied", "not authorized", "verify you are a human"
}


@tool
def web_search(query: str, max_results: int = 4) -> List[str]:
    """
    Performs a web search using the Tavily API and returns a list of relevant URLs.

    This tool takes a search query, enhances it to exclude PDF files, and uses the
    TavilySearch API to find a specified number of results. It also filters out
    results that point to pages that are likely to be blocked or require CAPTCHA verification.

    Args:
        query (str): The search term or question to look up online.
        max_results (int, optional): The maximum number of URLs to return.
                                     Defaults to 4. The value is clamped between 4 and 8.

    Returns:
        List[str]: A list of URL strings from the search results, ready for scraping.
    """

    search_query = f"{query} -filetype:pdf"
    max_results = max(1, min(max_results, 8))
    tavily = TavilySearch(max_results=max_results)
    raw = tavily.invoke({"query": search_query})
    results_list = raw if isinstance(raw, list) else raw.get("results", [])
    urls = [
        page["url"] for page in results_list
        if not any(
            k in ((page.get("content") or "").lower())
            for k in FORBIDDEN_KEYWORDS
        )
    ]
    return urls