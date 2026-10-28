import re
import urllib.parse
import requests
import xml.etree.ElementTree as ET

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_live_news(limit: int = 3) -> str:
    """Fetch real-time top headlines from Google News India RSS feed."""
    try:
        url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
        res = requests.get(url, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            items = root.findall('.//item')[:limit]
            if items:
                headlines = []
                for idx, it in enumerate(items, 1):
                    raw_title = it.find('title').text or ""
                    # Remove trailing source like " - The Hindu" or " - NDTV"
                    clean_title = re.sub(r'\s*-\s*[^-]+$', '', raw_title).strip()
                    headlines.append(f"{idx}. {clean_title}")
                return "Boss, aaj ki top headlines suniye:\n" + "\n".join(headlines)
    except Exception as e:
        print(f"[LiveInfo] News fetch error: {e}")
    return "Maaf karna boss, abhi live news fetch nahi ho pa rahi. Internet connection check karo!"

def get_live_weather(city: str = "") -> str:
    """Fetch real-time local weather using wttr.in."""
    try:
        target = urllib.parse.quote(city) if city else ""
        url = f"https://wttr.in/{target}?format=3"
        res = requests.get(url, headers={"User-Agent": "curl/8.0"}, timeout=5)
        if res.status_code == 200 and res.text.strip():
            # Clean coordinate prefix if present
            raw = res.text.strip()
            if ":" in raw:
                raw = raw.split(":")[-1].strip()
            loc_str = f"{city} mein" if city else "aaj"
            return f"Boss, {loc_str} mausam hai: {raw}."
    except Exception as e:
        print(f"[LiveInfo] Weather fetch error: {e}")
    return "Mausam ki jaankari lene mein dikkat aa rahi hai boss."

def get_instant_answer(query: str) -> str:
    """Look up factual knowledge, definitions, and people from DuckDuckGo & Wikipedia."""
    clean_q = re.sub(r'kya hai|kaun hai|kya hota hai|what is|who is|tell me about|batao|explain', '', query, flags=re.IGNORECASE).strip()
    if not clean_q:
        clean_q = query

    # Pass 1: DuckDuckGo Instant Answer
    try:
        ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean_q)}&format=json"
        res = requests.get(ddg_url, headers=HEADERS, timeout=4)
        if res.status_code == 200:
            data = res.json()
            abstract = data.get("AbstractText") or data.get("Abstract")
            if abstract and len(abstract.strip()) > 20:
                first_sentence = abstract.split(". ")[0] + "."
                return f"{first_sentence}"
    except Exception:
        pass

    # Pass 2: Wikipedia Summary
    try:
        wiki_title = clean_q.replace(" ", "_")
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(wiki_title)}"
        res = requests.get(wiki_url, headers={"User-Agent": "JarvisAssistant/1.0"}, timeout=4)
        if res.status_code == 200:
            data = res.json()
            extract = data.get("extract")
            if extract and len(extract.strip()) > 20:
                sentences = extract.split(". ")
                short_summary = ". ".join(sentences[:2]) + "."
                return f"{short_summary}"
    except Exception:
        pass

    return ""
