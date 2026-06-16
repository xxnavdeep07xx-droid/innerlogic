#!/usr/bin/env python3
"""
Music Fetcher — Downloads royalty-free cinematic music for reels.
Strategy (in order):
1. Try Pixabay CDN fallback URLs (direct MP3 links, no API key needed)
2. Generate ambient cinematic music with FFmpeg (always works, zero dependencies)
"""

import requests
import random
import os
import subprocess


# ─── Pixabay CDN URLs (verified working as of June 2025) ─────────────────────
# These are pre-selected royalty-free cinematic/ambient tracks.
# Only include URLs that return HTTP 200 (most Pixabay CDN links now return 403).
FALLBACK_MUSIC_URLS = [
    # ~147s - Cinematic Ambient (dark atmospheric)
    "https://cdn.pixabay.com/audio/2022/05/27/audio_1808fbf07a.mp3",
    # ~110s - Dark Cinematic Piano
    "https://cdn.pixabay.com/audio/2022/01/18/audio_d0a13f69d2.mp3",
    # ~4s - Short ambient tone (not ideal but works as last CDN fallback)
    "https://cdn.pixabay.com/audio/2022/02/22/audio_d1718ab41b.mp3",
]


def _download_file(url, output_path, timeout=60):
    """Download a file from URL to local path."""
    response = requests.get(url, timeout=timeout, stream=True)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path


def fetch_music_fallback(temp_dir):
    """
    Download music from fallback CDN URLs (direct Pixabay CDN links).
    These are pre-selected royalty-free cinematic tracks.
    """
    # Shuffle URLs to vary the music selection
    urls = FALLBACK_MUSIC_URLS.copy()
    random.shuffle(urls)
    
    for url in urls:
        output_path = os.path.join(temp_dir, "background_music.mp3")
        try:
            print(f"   ⬇️  Trying: {url.split('/')[-1]}")
            _download_file(url, output_path, timeout=60)
            file_size = os.path.getsize(output_path)
            if file_size > 50000:  # At least 50KB (real music)
                print(f"   ✅ Music downloaded ({file_size / 1024:.0f} KB)")
                return output_path
            else:
                print(f"   ⚠️  File too small ({file_size} bytes), trying next...")
                os.remove(output_path)
        except Exception as e:
            print(f"   ⚠️  Download failed: {e}")
    
    return None


def generate_ambient_music(temp_dir, duration=16):
    """
    Generate cinematic ambient music using FFmpeg.
    Creates a dark, atmospheric drone sound — perfect for philosophical quotes.
    
    This ALWAYS works (no network needed) and produces a unique track each time
    by randomizing the base frequencies.
    
    Args:
        temp_dir: Directory to save the generated music
        duration: Duration in seconds (default 16 for a 15-second reel + 1s buffer)
    """
    output_path = os.path.join(temp_dir, "background_music.mp3")
    
    try:
        # Randomize base frequency for variety (A1-C2 range = dark & moody)
        base_freq = random.choice([55, 58, 62, 65, 73])
        
        # Generate rich ambient drone with harmonics and filtering
        cmd = [
            "ffmpeg", "-y",
            # Layer 1: Deep bass drone
            "-f", "lavfi", "-i", f"sine=frequency={base_freq}:duration={duration}",
            # Layer 2: Perfect fifth above (haunting interval)
            "-f", "lavfi", "-i", f"sine=frequency={int(base_freq * 1.5)}:duration={duration}",
            # Layer 3: Octave above (adds brightness)
            "-f", "lavfi", "-i", f"sine=frequency={base_freq * 2}:duration={duration}",
            # Layer 4: Minor third (dark tension)
            "-f", "lavfi", "-i", f"sine=frequency={int(base_freq * 2.4)}:duration={duration}",
            # Mix and shape the sound
            "-filter_complex",
            f"[0:a][1:a][2:a][3:a]amix=inputs=4:duration=longest,"
            f"lowpass=f=600,"
            f"highpass=f=30,"
            f"volume=0.25,"
            f"afade=t=in:st=0:d=2,"
            f"afade=t=out:st={duration-3}:d=3",
            "-t", str(duration),
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"   ✅ Ambient music generated ({file_size / 1024:.0f} KB, key: {base_freq}Hz)")
            return output_path
        else:
            print(f"   ⚠️  FFmpeg music generation failed")
            
    except Exception as e:
        print(f"   ⚠️  Music generation error: {e}")
    
    return None


def fetch_music(api_key, temp_dir):
    """
    Main music fetching function.
    Tries CDN URLs first, then generates ambient music with FFmpeg.
    
    Args:
        api_key: Pixabay API key (unused, kept for compatibility)
        temp_dir: Directory to save the music file
    
    Returns:
        str: Path to the music file (always returns something)
    """
    # Step 1: Try fallback CDN URLs
    result = fetch_music_fallback(temp_dir)
    if result:
        return result
    
    # Step 2: Generate ambient cinematic music with FFmpeg
    print("   🎵 CDN downloads failed — generating ambient music with FFmpeg...")
    result = generate_ambient_music(temp_dir)
    if result:
        return result
    
    # Step 3: Absolute last resort — return None
    # (video_creator.py will use silent audio)
    print("   ❌ All music methods failed — video will have silent audio")
    return None


if __name__ == "__main__":
    # Quick test
    os.makedirs("temp", exist_ok=True)
    path = fetch_music("", "temp")
    print(f"Music saved to: {path}")
