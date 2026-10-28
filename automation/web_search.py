import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import webbrowser

KNOWN_SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://www.github.com",
    "chatgpt": "https://chatgpt.com",
    "stackoverflow": "https://stackoverflow.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://twitter.com",
    "instagram": "https://www.instagram.com"
}

def get_chrome_executable() -> str:
    """Find Google Chrome executable on Windows."""
    candidates = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LocalAppData", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    which_chrome = shutil.which("chrome")
    if which_chrome:
        return which_chrome
    return ""

def open_url(url: str):
    """Open URL preferring Google Chrome instead of Microsoft Edge."""
    chrome_path = get_chrome_executable()
    if chrome_path:
        try:
            subprocess.Popen([chrome_path, url], shell=False)
            return True
        except Exception:
            pass
    webbrowser.open(url)
    return True

def open_website(site_name: str) -> tuple[bool, str]:
    site_key = site_name.lower().strip()
    url = KNOWN_SITES.get(site_key)
    if not url:
        if "." in site_key:
            url = f"https://{site_key}"
        else:
            url = f"https://www.google.com/search?q={urllib.parse.quote(site_name)}"
    open_url(url)
    return True, f"Opened {site_name} in Chrome."

def search_web(query: str) -> tuple[bool, str]:
    encoded = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded}"
    open_url(url)
    return True, f"Searching for '{query}' on Google in Chrome."

def parse_duration_to_seconds(duration_str: str) -> int:
    """Parse duration like '3:45' or '1:12:30' into total seconds."""
    try:
        parts = [int(p) for p in str(duration_str).strip().split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 1:
            return parts[0]
    except Exception:
        pass
    return 0

def extract_top_full_video_id(html: str) -> str | None:
    """Extract the first true full video ID from YouTube search HTML, strictly excluding Shorts."""
    import json

    # 1. Gather all Short IDs present on the page to blacklist them
    shorts_ids = set(re.findall(r'/shorts/([a-zA-Z0-9_-]{11})', html))
    shorts_ids.update(re.findall(r'"reelItemRenderer":\s*\{[^\}]*?"videoId":\s*"([a-zA-Z0-9_-]{11})"', html))
    shorts_ids.update(re.findall(r'"shortsLockupViewModel":\s*\{[^\}]*?"entityId":\s*"[^\"]*?([a-zA-Z0-9_-]{11})"', html))

    # 2. Try parsing ytInitialData JSON for videoRenderer
    data = None
    try:
        match = re.search(r'var ytInitialData\s*=\s*({.*?});</script>', html)
        if not match:
            match = re.search(r'window\["ytInitialData"\]\s*=\s*({.*?});', html)
        if match:
            data = json.loads(match.group(1))
    except Exception:
        data = None

    if data:
        try:
            sections = (
                data.get("contents", {})
                .get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {})
                .get("sectionListRenderer", {})
                .get("contents", [])
            )
            for section in sections:
                contents = section.get("itemSectionRenderer", {}).get("contents", [])
                for item in contents:
                    if "videoRenderer" in item:
                        vr = item["videoRenderer"]
                        vid = vr.get("videoId")
                        if not vid or vid in shorts_ids:
                            continue

                        # Check duration if available - reject Shorts (<= 60s)
                        length_obj = vr.get("lengthText", {})
                        simple_len = length_obj.get("simpleText", "")
                        if simple_len:
                            sec = parse_duration_to_seconds(simple_len)
                            if 0 < sec <= 60:
                                continue

                        # Verify endpoint is not a short
                        nav = vr.get("navigationEndpoint", {})
                        cmd_meta = nav.get("commandMetadata", {}).get("webCommandMetadata", {})
                        page_type = cmd_meta.get("webPageType", "")
                        url_path = cmd_meta.get("url", "")
                        if "SHORTS" in str(page_type).upper() or "/shorts/" in str(url_path):
                            continue

                        return vid
        except Exception:
            pass

    # 3. Fallback regex: Look specifically for videoRenderer blocks (full standard videos only)
    vr_blocks = re.findall(r'"videoRenderer":\s*(\{.*?\})(?=,\s*"videoRenderer"|,\s*"reelItemRenderer"|,\s*"reelShelfRenderer"|,\s*"shelfRenderer"|\])', html, re.DOTALL)
    for block in vr_blocks:
        vid_m = re.search(r'"videoId":\s*"([a-zA-Z0-9_-]{11})"', block)
        if not vid_m:
            continue
        vid = vid_m.group(1)
        if vid in shorts_ids:
            continue
        len_m = re.search(r'"lengthText":\s*\{[^\}]*?"simpleText":\s*"([0-9:]+)"', block)
        if len_m:
            sec = parse_duration_to_seconds(len_m.group(1))
            if 0 < sec <= 60:
                continue
        return vid

    # 4. Secondary fallback: First /watch?v= ID not in shorts_ids
    all_watch_ids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
    for vid in all_watch_ids:
        if vid not in shorts_ids:
            return vid

    return None

def get_direct_youtube_video_url(query: str) -> str:
    """Resolve direct YouTube top FULL video URL so video plays immediately without showing search results and strictly avoiding Shorts."""
    clean_query = query.strip()
    encoded = urllib.parse.quote(clean_query)
    # Using sp=EgIQAQ%253D%253D filter forces YouTube server to return Type: Video (Full videos, no shorts shelves)
    search_url = f"https://www.youtube.com/results?search_query={encoded}&sp=EgIQAQ%253D%253D"
    try:
        req = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9,hi;q=0.8"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode("utf-8", errors="ignore")
            top_vid = extract_top_full_video_id(html)
            if top_vid:
                return f"https://www.youtube.com/watch?v={top_vid}"
    except Exception as e:
        print(f"[YouTube] Direct playback link note: {e}")
    return search_url

def play_music_or_video(query: str) -> tuple[bool, str]:
    clean_query = query.lower()
    for prefix in ["play", "chala do", "chalao", "gaana", "gana", "song", "youtube pe", "youtube par", "kholo", "aur", "pe", "par", "video", "videos", "full", "top"]:
        clean_query = clean_query.replace(prefix, " ")
    clean_query = " ".join(clean_query.split()).strip()
    if not clean_query:
        clean_query = "top trending songs"

    direct_url = get_direct_youtube_video_url(clean_query)
    open_url(direct_url)
    return True, f"Playing '{clean_query}' full video directly on YouTube in Chrome."

