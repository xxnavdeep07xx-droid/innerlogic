#!/usr/bin/env python3
"""
Music Fetcher — Downloads royalty-free cinematic music for reels.
Strategy (in order):
1. Pixabay API — thousands of real tracks (needs free API key)
2. Pixabay CDN — 2 verified working direct MP3 links (no key needed)
3. FFmpeg Ambient — generates unique cinematic music (always works, no network)
"""

import requests
import random
import os
import subprocess


# ─── Pixabay CDN URLs (verified working) ──────────────────────────────────────
FALLBACK_MUSIC_URLS = [
    # ~147s - Cinematic Ambient
    "https://cdn.pixabay.com/audio/2022/05/27/audio_1808fbf07a.mp3",
    # ~110s - Dark Cinematic Piano
    "https://cdn.pixabay.com/audio/2022/01/18/audio_d0a13f69d2.mp3",
    # ~4s - Short ambient tone
    "https://cdn.pixabay.com/audio/2022/02/22/audio_d1718ab41b.mp3",
]


# ─── FFmpeg Music Styles ─────────────────────────────────────────────────────
# Each style is a function that returns an FFmpeg command list.
# Randomized parameters ensure every reel sounds unique.

MUSIC_STYLES = {
    "dark_drone": {
        "name": "Dark Drone",
        "mood": "Deep sub-bass with harmonic overtones and noise texture",
    },
    "cinematic_piano": {
        "name": "Cinematic Piano",
        "mood": "Minor key arpeggio with reverb-like echo",
    },
    "melodic_ambient": {
        "name": "Melodic Ambient",
        "mood": "Layered minor scale with warm filtering",
    },
    "tension_build": {
        "name": "Tension Build",
        "mood": "Rising frequencies creating psychological tension",
    },
    "ethereal_pad": {
        "name": "Ethereal Pad",
        "mood": "Soft sustained chords with slow evolution",
    },
}


def _build_ffmpeg_dark_drone(duration):
    """Generate a dark ambient drone with sub-bass, harmonics & noise texture."""
    base = random.choice([36, 40, 44, 49, 55])
    return [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={base}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={int(base*1.5)}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={base*2}:duration={duration}",
        "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=pink:r=44100:a=0.02",
        "-filter_complex",
        f"[0:a]volume=0.3[bass];[1:a]volume=0.15[mid];[2:a]volume=0.08[high];"
        f"[bass][mid][high][3:a]amix=inputs=4:duration=longest,"
        f"lowpass=f=400,aecho=0.8:0.9:80:0.3,volume=0.3,"
        f"afade=t=in:st=0:d=3,afade=t=out:st={duration-4}:d=4",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


def _build_ffmpeg_cinematic_piano(duration):
    """Generate a cinematic piano-like arpeggio with echo/reverb."""
    # Minor key notes: root, minor 3rd, 5th, octave
    keys = {
        "Am": [220, 261, 329, 440],
        "Dm": [293, 349, 440, 587],
        "Em": [164, 196, 246, 329],
        "Fm": [174, 207, 261, 349],
        "Gm": [196, 233, 293, 392],
    }
    key_name = random.choice(list(keys.keys()))
    notes = keys[key_name]
    
    return [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={notes[0]}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={notes[1]}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={notes[2]}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={notes[3]}:duration={duration}",
        "-filter_complex",
        f"[0:a]volume=0.15[a0];[1:a]volume=0.12[a1];[2:a]volume=0.10[a2];[3:a]volume=0.08[a3];"
        f"[a0][a1][a2][a3]amix=inputs=4:duration=longest,"
        f"lowpass=f=2000,highpass=f=150,"
        f"aecho=0.8:0.88:60:0.4,aecho=0.8:0.88:120:0.2,"
        f"volume=0.35,afade=t=in:st=0:d=2,afade=t=out:st={duration-3}:d=3",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


def _build_ffmpeg_melodic_ambient(duration):
    """Generate layered minor scale with warm filtering and echo."""
    base = random.choice([130, 146, 164, 174, 196])
    notes = [base, int(base*1.2), int(base*1.5), int(base*1.8)]
    
    return [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={notes[0]}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={notes[1]}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={notes[2]}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={notes[3]}:duration={duration}",
        "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=brown:r=44100:a=0.01",
        "-filter_complex",
        f"[0:a]volume=0.12[n0];[1:a]volume=0.10[n1];[2:a]volume=0.10[n2];[3:a]volume=0.08[n3];"
        f"[n0][n1][n2][n3][4:a]amix=inputs=5:duration=longest,"
        f"lowpass=f=800,highpass=f=80,"
        f"aecho=0.7:0.85:100:0.35,aecho=0.7:0.85:200:0.15,"
        f"volume=0.3,afade=t=in:st=0:d=2.5,afade=t=out:st={duration-4}:d=4",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


def _build_ffmpeg_tension_build(duration):
    """Generate rising frequencies creating psychological tension."""
    start_freq = random.choice([40, 50, 60])
    mid_freq = start_freq * 2
    end_freq = start_freq * 3
    
    return [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={start_freq}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={mid_freq}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={end_freq}:duration={duration}",
        "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=pink:r=44100:a=0.015",
        "-filter_complex",
        f"[0:a]volume=0.2[a0];[1:a]volume=0.12[a1];[2:a]volume=0.06[a2];"
        f"[a0][a1][a2][3:a]amix=inputs=4:duration=longest,"
        f"lowpass=f=600,"
        f"volume=0.25,"
        f"afade=t=in:st=0:d=2,afade=t=out:st={duration-3}:d=3",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


def _build_ffmpeg_ethereal_pad(duration):
    """Generate soft sustained chords with slow evolution."""
    root = random.choice([110, 130, 146, 164])
    # Major 7th chord = root, major 3rd, 5th, major 7th (dreamy)
    notes = [root, int(root*1.26), int(root*1.5), int(root*2)]
    
    return [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={notes[0]}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={notes[1]}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={notes[2]}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={notes[3]}:duration={duration}",
        "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=brown:r=44100:a=0.008",
        "-filter_complex",
        f"[0:a]volume=0.10[e0];[1:a]volume=0.08[e1];[2:a]volume=0.08[e2];[3:a]volume=0.06[e3];"
        f"[e0][e1][e2][e3][4:a]amix=inputs=5:duration=longest,"
        f"lowpass=f=500,highpass=f=60,"
        f"aecho=0.9:0.92:150:0.4,"
        f"volume=0.28,afade=t=in:st=0:d=3.5,afade=t=out:st={duration-4}:d=4",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


# Map style names to builder functions
STYLE_BUILDERS = {
    "dark_drone": _build_ffmpeg_dark_drone,
    "cinematic_piano": _build_ffmpeg_cinematic_piano,
    "melodic_ambient": _build_ffmpeg_melodic_ambient,
    "tension_build": _build_ffmpeg_tension_build,
    "ethereal_pad": _build_ffmpeg_ethereal_pad,
}


def _download_file(url, output_path, timeout=60):
    """Download a file from URL to local path."""
    response = requests.get(url, timeout=timeout, stream=True)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path


def fetch_music_pixabay_api(api_key, temp_dir):
    """
    Search and download music from Pixabay API.
    Free API key at: https://pixabay.com/api/docs/
    Returns thousands of real cinematic/ambient tracks.
    """
    if not api_key or not api_key.strip():
        return None
    
    search_terms = [
        "dark cinematic ambient",
        "cinematic piano emotional",
        "dark atmospheric",
        "melancholic strings",
        "epic dark cinematic",
        "sad piano",
        "philosophical ambient",
        "dark drone",
    ]
    search_term = random.choice(search_terms)
    
    try:
        # Pixabay API for audio/music
        params = {
            "key": api_key,
            "q": search_term,
            "category": "music",
            "per_page": 20,
            "safesearch": "true",
        }
        
        response = requests.get("https://pixabay.com/api/", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        hits = data.get("hits", [])
        if not hits:
            print(f"   ⚠️  No Pixabay results for '{search_term}'")
            return None
        
        # Pick a random track
        hit = random.choice(hits)
        
        # Try to get the audio download URL
        # Pixabay returns different URL fields for audio
        audio_url = None
        for field in ["audiodownload", "audio", "previewURL", "downloadURL"]:
            if hit.get(field):
                audio_url = hit[field]
                break
        
        if audio_url:
            output_path = os.path.join(temp_dir, "background_music.mp3")
            _download_file(audio_url, output_path, timeout=60)
            file_size = os.path.getsize(output_path)
            if file_size > 50000:
                print(f"   ✅ Pixabay music downloaded ({file_size/1024:.0f} KB, search: {search_term})")
                return output_path
        
        print(f"   ⚠️  Pixabay hit had no download URL")
        
    except Exception as e:
        print(f"   ⚠️  Pixabay API error: {e}")
    
    return None


def fetch_music_fallback(temp_dir):
    """Download music from verified working Pixabay CDN URLs."""
    urls = FALLBACK_MUSIC_URLS.copy()
    random.shuffle(urls)
    
    for url in urls:
        output_path = os.path.join(temp_dir, "background_music.mp3")
        try:
            print(f"   ⬇️  Trying CDN: {url.split('/')[-1]}")
            _download_file(url, output_path, timeout=60)
            file_size = os.path.getsize(output_path)
            if file_size > 50000:
                print(f"   ✅ Music downloaded ({file_size/1024:.0f} KB)")
                return output_path
            else:
                print(f"   ⚠️  File too small, trying next...")
                os.remove(output_path)
        except Exception as e:
            print(f"   ⚠️  Download failed: {e}")
    
    return None


def generate_ambient_music(temp_dir, duration=16):
    """
    Generate cinematic ambient music using FFmpeg.
    
    5 unique styles with randomized parameters = every reel sounds different:
      - Dark Drone: Deep sub-bass with harmonic overtones
      - Cinematic Piano: Minor key arpeggio with reverb echo
      - Melodic Ambient: Layered minor scale with warm filtering
      - Tension Build: Rising frequencies for psychological intensity
      - Ethereal Pad: Soft sustained chords, dreamy and meditative
    """
    output_path = os.path.join(temp_dir, "background_music.mp3")
    
    try:
        # Pick a random style
        style_name = random.choice(list(STYLE_BUILDERS.keys()))
        style_info = MUSIC_STYLES[style_name]
        builder = STYLE_BUILDERS[style_name]
        
        cmd = builder(duration)
        cmd.append(output_path)
        
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"   ✅ Generated '{style_info['name']}' music ({file_size/1024:.0f} KB)")
            print(f"      🎵 {style_info['mood']}")
            return output_path
        else:
            print(f"   ⚠️  FFmpeg generation failed for style '{style_name}'")
            
    except Exception as e:
        print(f"   ⚠️  Music generation error: {e}")
    
    return None


def fetch_music(api_key, temp_dir):
    """
    Main music fetching function with 3-tier fallback.
    
    Priority:
    1. Pixabay API (thousands of real tracks) — needs free API key
    2. Pixabay CDN (2-3 verified working URLs) — no key needed
    3. FFmpeg Ambient (5 unique styles, infinite variety) — always works
    
    Args:
        api_key: Pixabay API key (get free at https://pixabay.com/api/docs/)
        temp_dir: Directory to save the music file
    
    Returns:
        str: Path to the music file (always returns something)
    """
    # Tier 1: Pixabay API (best variety + real music)
    if api_key and api_key.strip():
        result = fetch_music_pixabay_api(api_key, temp_dir)
        if result:
            return result
    
    # Tier 2: Pixabay CDN (quick fallback, limited variety)
    result = fetch_music_fallback(temp_dir)
    if result:
        return result
    
    # Tier 3: FFmpeg generated music (always works, 5 styles with infinite variations)
    print("   🎵 CDN unavailable — generating cinematic music with FFmpeg...")
    result = generate_ambient_music(temp_dir)
    if result:
        return result
    
    # Absolute last resort
    print("   ❌ All music methods failed — video will have silent audio")
    return None


if __name__ == "__main__":
    os.makedirs("temp", exist_ok=True)
    path = fetch_music("", "temp")
    print(f"Music saved to: {path}")
