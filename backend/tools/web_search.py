"""Web Search tool — DuckDuckGo (free, no API key) with optional Tavily upgrade."""
import logging

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 5, tavily_api_key: str = "") -> str:
    """Search the web. Uses Tavily if an API key is set, otherwise DuckDuckGo."""
    if tavily_api_key:
        result = _tavily_search(query, max_results, tavily_api_key)
        if result:
            return result
    return _duckduckgo_search(query, max_results)


def _tavily_search(query: str, max_results: int, api_key: str) -> str:
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results)
        results = response.get("results", [])
        if not results:
            return ""
        parts = [
            f"**{r['title']}**\n{r['content']}\nSource: {r['url']}"
            for r in results
        ]
        logger.info("Tavily returned %d results for: %s", len(results), query[:60])
        return "\n\n".join(parts)
    except Exception as exc:
        logger.warning("Tavily search failed: %s — falling back to DuckDuckGo", exc)
        return ""


def _duckduckgo_search(query: str, max_results: int) -> str:
    try:
        from ddgs import DDGS
        with DDGS() as ddg:
            results = list(ddg.text(query, max_results=max_results))
        if not results:
            return "No web search results found."
        parts = [
            f"**{r['title']}**\n{r['body']}\nSource: {r['href']}"
            for r in results
        ]
        logger.info("DuckDuckGo returned %d results for: %s", len(results), query[:60])
        return "\n\n".join(parts)
    except Exception as exc:
        logger.error("DuckDuckGo search failed: %s", exc)
        return f"Web search failed: {exc}"
