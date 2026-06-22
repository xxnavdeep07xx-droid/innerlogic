#!/usr/bin/env python3
"""
Video Background Fetcher — fetches mood-matched vertical video clips from
Pexels (free, royalty-free, no API key beyond PEXELS_API_KEY).

Why video backgrounds instead of static images?
  - Watch-time is THE algorithm signal. Static image + Ken Burns = boring
    after 3 seconds. Video backgrounds (rain, fog, candle, ocean) hold
    attention 2-3x longer.
  - Pexels has thousands of free 5-15s vertical videos perfectly suited
    for IG Reels backgrounds.

Strategy:
  1. Map the quote's category → mood keyword(s)
  2. Search Pexels /videos/search with those keywords + orientation=portrait
  3. Pick a random video from the top 15 results
  4. Download the smallest vertical file (usually 540p or 720p HD — plenty
     for a 1080x1920 reel where the video is darkened + text-overlay'd)
  5. Fallback: return None — the pipeline will use a static image instead

History: avoids repeating the same video URL within the last 5 reels.
"""

import os
import json
import random
import logging
import urllib.request
import urllib.parse
from pathlib import Path

logger = logging.getLogger("innerlogic")


# ─── Mood → Pexels search keyword mapping ────────────────────────────────────
# Maps each InnerLogic quote category to a list of mood-evocative search
# queries that Pexels has good vertical video coverage for.
MOOD_KEYWORDS = {
    "stoicism": ["rain window", "fog forest", "ocean waves slow", "mountain clouds"],
    "existentialism": ["dark clouds", "empty road night", "starry sky", "lonely desert"],
    "eastern": ["candle flame", "bamboo forest", "koi pond", "incense smoke"],
    "psychology": ["rain on glass", "foggy lake", "dark water", "shadow forest"],
    "classical": ["ancient ruins", "marble statue", "old library", "Greek columns"],
    "mysticism": ["candle light dark", "smoke slow", "stars night sky", "aurora"],
    "transcendentalism": ["forest sunlight", "waterfall slow", "river flowing", "autumn forest"],
    "motivation": ["sunrise mountain", "ocean waves", "city timelapse night", "running sunrise"],
    "rationalism": ["ink in water", "geometric patterns", "clouds time lapse", "mathematical"],
    "courage": ["stormy ocean", "lightning", "rocky cliff", "eagle flying"],
    "default": ["dark cinematic", "fog night", "rain slow", "candle dark"],
}

# Cache file for tracking recently used videos (avoid repeats)
HISTORY_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "video_bg_history.json")
)

# Pexels API endpoint
PEXELS_VIDEO_SEARCH_URL = "https://api.pexels.com/videos/search"


def _load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {"recent_urls": [], "recent_ids": []}


def _save_history(history):
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


def _is_recently_used(url, vid_id, history):
    return url in history.get("recent_urls", []) or str(vid_id) in history.get("recent_ids", [])


def _mark_used(url, vid_id, history):
    history.setdefault("recent_urls", []).append(url)
    history["recent_urls"] = history["recent_urls"][-5:]
    history.setdefault("recent_ids", []).append(str(vid_id))
    history["recent_ids"] = history["recent_ids"][-5:]
    _save_history(history)


def _search_pexels_videos(query, api_key, per_page=15, timeout=20):
    """Search Pexels for vertical videos matching the query."""
    params = urllib.parse.urlencode({
        "query": query,
        "orientation": "portrait",  # vertical — for Reels
        "per_page": per_page,
        "size": "medium",  # don't need 4K, save bandwidth
    })
    url = f"{PEXELS_VIDEO_SEARCH_URL}?{params}"
    req = urllib.request.Request(url, headers={"Authorization": api_key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("videos", [])
    except Exception as e:
        logger.warning(f"   ⚠️ Pexels video search failed for '{query}': {str(e)[:80]}")
        return []


def _pick_best_video_file(video):
    """
    From a Pexels video object, pick the best vertical file for our use.
    Prefer HD (720p+) vertical files with a reasonable size.
    """
    files = video.get("video_files", [])
    if not files:
        return None

    # Filter for vertical aspect ratio (height > width)
    vertical = [f for f in files if f.get("height", 0) > f.get("width", 0)]
    if not vertical:
        # Fallback: take any file
        vertical = files

    # Prefer 720p (good quality, reasonable size)
    preferred = [f for f in vertical if 720 <= f.get("height", 0) <= 1080]
    if preferred:
        # Pick the smallest of the preferred (saves download time)
        preferred.sort(key=lambda f: f.get("size", 0) or 0)
        return preferred[0]

    # Fallback: pick the smallest vertical file
    vertical.sort(key=lambda f: f.get("size", 0) or 0)
    return vertical[0] if vertical else None


def _download_file(url, output_path, timeout=60):
    """Download a file with a timeout."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "InnerLogic/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            with open(output_path, "wb") as f:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1024
    except Exception as e:
        logger.warning(f"   ⚠️ Video download failed: {str(e)[:80]}")
        return False


def fetch_video_background(category, temp_dir, pexels_api_key=None):
    """
    Fetch a mood-matched vertical video background for the given quote category.

    Args:
        category: quote category (stoicism, existentialism, etc.)
        temp_dir: where to save the downloaded video file
        pexels_api_key: Pexels API key (falls back to PEXELS_API_KEY env var)

    Returns:
        Path to the downloaded .mp4 file, or None if fetching failed
        (the pipeline will fall back to a static image in that case).
    """
    if pexels_api_key is None:
        pexels_api_key = os.environ.get("PEXELS_API_KEY", "")

    if not pexels_api_key:
        logger.info("   ℹ️  No PEXELS_API_KEY — using static image background")
        return None

    keywords = MOOD_KEYWORDS.get(category, MOOD_KEYWORDS["default"])
    random.shuffle(keywords)
    history = _load_history()

    for query in keywords[:3]:  # try up to 3 different mood queries
        videos = _search_pexels_videos(query, pexels_api_key)
        if not videos:
            continue

        # Filter out recently-used videos
        fresh = [v for v in videos if not _is_recently_used(
                    v.get("url", ""), v.get("id", ""), history)]
        if not fresh:
            fresh = videos  # use whatever we have

        # Pick a random video from the top results
        video = random.choice(fresh[:10])
        file_obj = _pick_best_video_file(video)
        if not file_obj or not file_obj.get("link"):
            continue

        video_url = file_obj["link"]
        ext = ".mp4"
        output_path = os.path.join(temp_dir, f"bg_video_{video.get('id', 'x')}{ext}")

        if _download_file(video_url, output_path):
            _mark_used(video_url, video.get("id"), history)
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"   🎥 Video bg: '{query}' → id={video.get('id')} "
                        f"({size_mb:.1f} MB, {file_obj.get('width')}x{file_obj.get('height')})")
            return output_path

    logger.info("   ℹ️  No suitable video bg found — using static image")
    return None


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cat = sys.argv[1] if len(sys.argv) > 1 else "stoicism"
    key = os.environ.get("PEXELS_API_KEY", "")
    if not key:
        print("Set PEXELS_API_KEY env var first")
        sys.exit(1)
    path = fetch_video_background(cat, "temp", key)
    print(f"\nResult: {path}")
