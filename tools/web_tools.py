import re
import requests
import webbrowser
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

def search_web(query: str) -> str:
    """
    Performs a real-time live web search and returns current facts, articles, and snippets.
    """
    if not query or not query.strip():
        return "No search query provided."

    try:
        results = []
        raw_results = list(DDGS().text(query, max_results=4))
            
        if raw_results:
            for i, res in enumerate(raw_results, 1):
                title = res.get("title", "Untitled")
                body = res.get("body", "")
                results.append(f"[{i}] {title}: {body}")
            formatted_output = "\n".join(results)
            return f"Live web search results for '{query}':\n" + formatted_output.encode("ascii", "ignore").decode("ascii")
    except Exception:
        pass

    # Fallback to direct HTML scrape
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            snippets = soup.find_all("a", class_="result__snippet")
            results = [f"[{i}] {s.get_text().strip()}" for i, s in enumerate(snippets[:4], 1)]
            if results:
                return f"Live search results for '{query}':\n" + "\n".join(results).encode("ascii", "ignore").decode("ascii")
    except Exception as e:
        return f"Search error: {e}"

    return f"No results found for '{query}'."

def search_videos(query: str) -> str:
    """
    Searches YouTube and online video platforms for videos, channels, and uploads.
    """
    if not query or not query.strip():
        return "No video query provided."

    # Strategy 1: Direct YouTube search page extraction (most reliable, zero rate limit)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        search_term = query.replace(' ', '+')
        url = f"https://www.youtube.com/results?search_query={search_term}"
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            matches = re.findall(r'"title":\{"runs":\[\{"text":"(.*?)"\}\]', resp.text)
            # Filter out non-video UI titles
            video_titles = [m for m in matches if len(m) > 4 and not any(x in m.lower() for x in ["shorts", "filter", "search"])]
            
            # Deduplicate preserving order
            seen = set()
            unique_titles = []
            for t in video_titles:
                if t not in seen:
                    seen.add(t)
                    unique_titles.append(t)

            if unique_titles:
                top_vids = unique_titles[:5]
                formatted = "\n".join([f"[{i}] {t}" for i, t in enumerate(top_vids, 1)])
                clean_output = formatted.encode("ascii", "ignore").decode("ascii")
                return f"Recent YouTube videos found for '{query}':\n{clean_output}"
    except Exception:
        pass

    # Strategy 2: DDGS video search
    try:
        raw_videos = list(DDGS().videos(query, max_results=4))
        if raw_videos:
            results = [f"[{i}] {v.get('title')}: {v.get('description', '')}" for i, v in enumerate(raw_videos, 1)]
            return f"Videos found for '{query}':\n" + "\n".join(results).encode("ascii", "ignore").decode("ascii")
    except Exception:
        pass

    # Strategy 3: Web search fallback
    return search_web(f"{query} YouTube videos latest uploads")

def search_news(topic: str = "world news") -> str:
    """
    Fetches real-time latest news headlines and summaries on any topic.
    """
    try:
        news_items = list(DDGS().news(topic, max_results=4))
        if news_items:
            results = [f"[{i}] ({item.get('date', '')}) {item.get('title')}: {item.get('body')}" for i, item in enumerate(news_items, 1)]
            return f"Latest news on '{topic}':\n" + "\n".join(results).encode("ascii", "ignore").decode("ascii")
    except Exception:
        pass
    return search_web(f"latest breaking news {topic}")

def read_webpage(url: str) -> str:
    """Visits any given website URL and extracts the main readable text content."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code != 200:
            return f"Failed to access webpage (HTTP {response.status_code})."

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        truncated_text = text[:2500] + ("..." if len(text) > 2500 else "")
        return f"Content of {url}:\n" + truncated_text.encode("ascii", "ignore").decode("ascii")
    except Exception as e:
        return f"Unable to read webpage: {e}"

def get_weather(location: str = "current location") -> str:
    """Fetches real-time weather information for any city or location."""
    try:
        clean_loc = location.replace(" ", "+").strip() if location else ""
        url = f"https://wttr.in/{clean_loc}?format=%l:+%t,+%C,+wind+%w"
        response = requests.get(url, timeout=5)
        if response.status_code == 200 and response.text.strip():
            clean_output = response.text.strip().encode("ascii", "ignore").decode("ascii")
            return f"Weather report for {clean_output}"
        return "Could not retrieve weather data at this moment."
    except Exception as e:
        return f"Unable to fetch weather: {e}"

def google_search_in_browser(query: str) -> str:
    """Opens a new Google search tab directly in the user's web browser."""
    try:
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open_new_tab(search_url)
        return f"Opened Google search for '{query}' in your browser."
    except Exception as e:
        return f"Failed to open search in browser: {e}"
