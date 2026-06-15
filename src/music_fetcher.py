#!/usr/bin/env python3
"""
Music Fetcher — Downloads royalty-free cinematic music for reels.
Uses Pixabay API (free) or falls back to bundled tracks.
"""

import requests
import random
import os
import json
from pathlib import Path


# Pixabay API endpoint for music
PIXABAY_API_URL = "https://pixabay.com/api/videos/"

# Search queries for cinematic/philosophical background music
MUSIC_SEARCH_TERMS = [
    "cinematic dark ambient",
    "dark piano emotional",
    "cinematic melancholic",
    "ambient dark atmospheric",
    "cinematic sad strings",
    "dark cinematic drone",
    "philosophical ambient",
    "cinematic deep bass",
    "dark atmospheric piano",
    "epic dark cinematic",
]

# Fallback: Free music URLs (royalty-free, no API key needed)
# These are from Free Music Archive and other free sources
FALLBACK_MUSIC_URLS = [
    "https://cdn.pixabay.com/audio/2022/02/22/audio_d1718ab41b.mp3",  # Dark Ambient
    "https://cdn.pixabay.com/audio/2022/05/27/audio_1808fbf07a.mp3",  # Cinematic Piano
    "https://cdn.pixabay.com/audio/2023/09/04/audio_5cfa1c0e34.mp3",  # Dark Atmosphere
    "https://cdn.pixabay.com/audio/2023/10/07/audio_0e1d6e2d9c.mp3",  # Emotional Piano
    "https://cdn.pixabay.com/audio/2022/03/10/audio_0ae8d9a8c8.mp3",  # Cinematic Dark
    "https://cdn.pixabay.com/audio/2024/01/10/audio_e8f46e4d74.mp3",  # Melancholic Strings
    "https://cdn.pixabay.com/audio/2023/04/14/audio_79df3d0ac6.mp3",  # Dark Ambient Soundscape
    "https://cdn.pixabay.com/audio/2022/10/09/audio_d0253e9bc7.mp3",  # Sad Piano
    "https://cdn.pixabay.com/audio/2023/06/07/audio_78e63679c7.mp3",  # Deep Cinematic
    "https://cdn.pixabay.com/audio/2022/01/18/audio_d0a13f69d2.mp3",  # Atmospheric Dark
]

# Track which music we've used recently
MUSIC_HISTORY_FILE = None  # Set dynamically


def _download_file(url, output_path, timeout=60):
    """Download a file from URL to local path."""
    response = requests.get(url, timeout=timeout, stream=True)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path


def fetch_music_pixabay(api_key, temp_dir):
    """
    Fetch music from Pixabay API.
    Searches for cinematic/ambient tracks and downloads one.
    """
    search_term = random.choice(MUSIC_SEARCH_TERMS)
    
    params = {
        "key": api_key,
        "q": search_term,
        "category": "film",
        "min_width": 0,
        "per_page": 20,
        "safesearch": "true",
    }
    
    try:
        response = requests.get(PIXABAY_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("hits"):
            # Pick a random video that has music
            hit = random.choice(data["hits"])
            video_url = hit.get("videos", {}).get("medium", {}).get("url")
            
            if video_url:
                output_path = os.path.join(temp_dir, "background_music.mp3")
                _download_file(video_url, output_path)
                print(f"   ✅ Music downloaded from Pixabay (search: {search_term})")
                return output_path
        
        print("   ⚠️  No suitable music found on Pixabay, using fallback...")
        
    except Exception as e:
        print(f"   ⚠️  Pixabay API error: {e}, using fallback...")
    
    return None


def fetch_music_fallback(temp_dir):
    """
    Download music from fallback URLs (direct Pixabay CDN links).
    These are pre-selected royalty-free cinematic tracks.
    """
    url = random.choice(FALLBACK_MUSIC_URLS)
    output_path = os.path.join(temp_dir, "background_music.mp3")
    
    try:
        _download_file(url, output_path, timeout=60)
        file_size = os.path.getsize(output_path)
        if file_size > 10000:  # At least 10KB
            print(f"   ✅ Fallback music downloaded ({file_size / 1024:.0f} KB)")
            return output_path
        else:
            print(f"   ⚠️  Downloaded music too small ({file_size} bytes)")
    except Exception as e:
        print(f"   ⚠️  Fallback download failed: {e}")
    
    return None


def generate_silent_audio(temp_dir, duration=15):
    """
    Generate a silent audio file as absolute last resort.
    FFmpeg will create a 15-second silent AAC file.
    """
    output_path = os.path.join(temp_dir, "background_music.mp3")
    
    try:
        import subprocess
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=30)
        print(f"   ✅ Silent audio generated (no music available)")
        return output_path
    except Exception as e:
        print(f"   ⚠️  Could not generate silent audio: {e}")
        return None


def fetch_music(api_key, temp_dir):
    """
    Main music fetching function.
    Tries Pixabay API first, then fallback URLs, then silent audio.
    
    Args:
        api_key: Pixabay API key (can be empty string)
        temp_dir: Directory to save the music file
    
    Returns:
        str: Path to the music file, or None if all methods fail
    """
    # Try Pixabay API if key is available
    if api_key and api_key.strip():
        result = fetch_music_pixabay(api_key, temp_dir)
        if result:
            return result
    
    # Try fallback URLs
    result = fetch_music_fallback(temp_dir)
    if result:
        return result
    
    # Last resort: generate silent audio
    result = generate_silent_audio(temp_dir)
    if result:
        return result
    
    # If absolutely nothing works, return None
    # The video creator will handle missing music gracefully
    print("   ❌ Could not fetch any music — video will be silent")
    return None


if __name__ == "__main__":
    # Quick test
    path = fetch_music("", "temp")
    print(f"Music saved to: {path}")
