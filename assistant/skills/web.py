"""Web skills: open a URL or run a web search in the default browser."""
from __future__ import annotations

import urllib.parse
import webbrowser

from assistant.registry import skill


@skill(
    "Open a URL in the default web browser.",
    params={"url": "The address to open (http/https)."},
)
def open_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}"


@skill(
    "Search the web for a query (opens Google results in the browser).",
    params={"query": "What to search for."},
)
def web_search(query: str) -> str:
    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    webbrowser.open(url)
    return f"Searched the web for: {query}"
