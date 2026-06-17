#!/usr/bin/env python3
"""
Music Fetcher — Downloads royalty-free cinematic music for reels.

6-Tier Strategy (in order of quality & variety):
1. Freesound API  — 500K+ CC-licensed sounds (free API token)
2. Pixabay API    — thousands of real tracks (needs free API key)
3. Mixkit SFX     — 20+ atmospheric/ambient tracks, free, no auth (WAV)
4. Pixabay CDN    — 2 verified working direct MP3 links (no key needed)
5. FFmpeg Ambient — 10 unique generated styles with infinite variations
6. Silent audio   — last resort (never actually silent thanks to Tier 5)

Track History: Rotates through sources to avoid repeating the same track.
"""

import requests
import random
import os
import subprocess
import json
import time


# ─── Track History ────────────────────────────────────────────────────────────
# Tracks recently used URLs/IDs to avoid repeats across consecutive posts
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "music_history.json")


def _load_history():
    """Load recently used music tracks."""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"recent_urls": [], "recent_mixkit_ids": [], "recent_styles": []}


def _save_history(history):
    """Save recently used music tracks."""
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


def _is_recently_used(key, value, history):
    """Check if a specific track was used recently."""
    if key == "url":
        return value in history.get("recent_urls", [])
    elif key == "mixkit_id":
        return value in history.get("recent_mixkit_ids", [])
    elif key == "style":
        return value in history.get("recent_styles", [])
    elif key == "freesound_id":
        return value in history.get("recent_freesound_ids", [])
    elif key == "insta_track_id":
        return value in history.get("recent_insta_track_ids", [])
    return False


def _mark_used(key, value, history):
    """Mark a track as recently used and trim old entries."""
    max_history = 5  # Remember last 5 tracks per category
    if key == "url":
        history.setdefault("recent_urls", []).append(value)
        history["recent_urls"] = history["recent_urls"][-max_history:]
    elif key == "mixkit_id":
        history.setdefault("recent_mixkit_ids", []).append(value)
        history["recent_mixkit_ids"] = history["recent_mixkit_ids"][-max_history:]
    elif key == "style":
        history.setdefault("recent_styles", []).append(value)
        history["recent_styles"] = history["recent_styles"][-max_history:]
    elif key == "freesound_id":
        history.setdefault("recent_freesound_ids", []).append(value)
        history["recent_freesound_ids"] = history["recent_freesound_ids"][-max_history:]
    elif key == "insta_track_id":
        history.setdefault("recent_insta_track_ids", []).append(value)
        history["recent_insta_track_ids"] = history["recent_insta_track_ids"][-max_history:]
        history.setdefault("recent_insta_track_names", []).append(str(value))
        history["recent_insta_track_names"] = history["recent_insta_track_names"][-max_history:]
    _save_history(history)


# ─── Mixkit SFX Library ──────────────────────────────────────────────────────
# Free atmospheric/cinematic sound effects from Mixkit (no auth needed)
# These are WAV files verified to work with direct download
# Duration and mood verified by testing
MIXKIT_TRACKS = [
    # Long atmospheric tracks (30s+)
    {"id": 350,  "duration": 85,  "mood": "cinematic_atmosphere",  "desc": "Deep cinematic atmosphere"},
    {"id": 800,  "duration": 98,  "mood": "dark_ambient",          "desc": "Dark ambient soundscape"},
    {"id": 1900, "duration": 112, "mood": "epic_cinematic",        "desc": "Epic cinematic texture"},
    {"id": 300,  "duration": 40,  "mood": "dark_cinematic",        "desc": "Dark cinematic ambience"},
    {"id": 1250, "duration": 39,  "mood": "suspense_atmosphere",   "desc": "Suspenseful atmosphere"},
    # Medium atmospheric tracks (15-30s)
    {"id": 450,  "duration": 30,  "mood": "cinematic_tension",     "desc": "Cinematic tension build"},
    {"id": 850,  "duration": 29,  "mood": "mysterious_ambient",    "desc": "Mysterious ambient pad"},
    {"id": 1050, "duration": 31,  "mood": "dark_atmosphere",       "desc": "Dark atmospheric texture"},
    {"id": 1200, "duration": 30,  "mood": "philosophical_ambient", "desc": "Philosophical ambience"},
    {"id": 1000, "duration": 25,  "mood": "melancholic_drone",     "desc": "Melancholic drone"},
    {"id": 1600, "duration": 25,  "mood": "ethereal_pad",          "desc": "Ethereal pad texture"},
    {"id": 700,  "duration": 16,  "mood": "dark_transition",       "desc": "Dark transition hit"},
    # Shorter cinematic accents (10-15s) — still useful for 15s reels
    {"id": 313,  "duration": 17,  "mood": "dramatic_hit",          "desc": "Dramatic impact"},
    {"id": 325,  "duration": 45,  "mood": "dark_dronescape",       "desc": "Dark droning soundscape"},
    {"id": 326,  "duration": 24,  "mood": "eerie_ambient",         "desc": "Eerie ambient texture"},
    {"id": 304,  "duration": 15,  "mood": "cinematic_hit",         "desc": "Cinematic bass hit"},
    {"id": 310,  "duration": 18,  "mood": "deep_rumble",           "desc": "Deep bass rumble"},
    {"id": 312,  "duration": 22,  "mood": "dark_pad",              "desc": "Dark synth pad"},
    {"id": 341,  "duration": 14,  "mood": "suspense_rise",         "desc": "Suspense rising tone"},
    {"id": 346,  "duration": 80,  "mood": "ambient_flow",          "desc": "Flowing ambient texture"},
    {"id": 347,  "duration": 60,  "mood": "meditative_drone",      "desc": "Meditative deep drone"},
]


# ─── Pixabay CDN URLs (verified working) ──────────────────────────────────────
PIXABAY_CDN_URLS = [
    # ~147s - Cinematic Ambient (large, full track)
    "https://cdn.pixabay.com/audio/2022/05/27/audio_1808fbf07a.mp3",
    # ~110s - Dark Cinematic Piano (large, full track)
    "https://cdn.pixabay.com/audio/2022/01/18/audio_d0a13f69d2.mp3",
]


# ─── FFmpeg Music Styles ─────────────────────────────────────────────────────
# Each style produces unique music every time thanks to randomized parameters.

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
    "deep_space": {
        "name": "Deep Space",
        "mood": "Vast cosmic ambience with slow pulsing tones",
    },
    "rain_meditation": {
        "name": "Rain Meditation",
        "mood": "Gentle rain-like texture with soft melodic undertones",
    },
    "suspense_pulse": {
        "name": "Suspense Pulse",
        "mood": "Rhythmic low pulse with eerie high harmonics",
    },
    "nostalgic_dream": {
        "name": "Nostalgic Dream",
        "mood": "Bittersweet chord progression with echo decay",
    },
    "void_ambience": {
        "name": "Void Ambience",
        "mood": "Empty space texture with distant resonant frequencies",
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
        f"lowpass=f=400,aecho=0.8:0.9:80:0.3,volume=1.5,"
        f"afade=t=in:st=0:d=3,afade=t=out:st={duration-4}:d=4,loudnorm=I=-14:TP=-1.5:LRA=11",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


def _build_ffmpeg_cinematic_piano(duration):
    """Generate a cinematic piano-like arpeggio with echo/reverb."""
    keys = {
        "Am": [220, 261, 329, 440],
        "Dm": [293, 349, 440, 587],
        "Em": [164, 196, 246, 329],
        "Fm": [174, 207, 261, 349],
        "Gm": [196, 233, 293, 392],
        "Bbm": [233, 277, 349, 466],
        "Cm": [261, 311, 392, 523],
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
        f"volume=1.5,afade=t=in:st=0:d=2,afade=t=out:st={duration-3}:d=3,loudnorm=I=-14:TP=-1.5:LRA=11",
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
        f"volume=1.5,afade=t=in:st=0:d=2.5,afade=t=out:st={duration-4}:d=4,loudnorm=I=-14:TP=-1.5:LRA=11",
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
        f"volume=1.5,"
        f"afade=t=in:st=0:d=2,afade=t=out:st={duration-3}:d=3,loudnorm=I=-14:TP=-1.5:LRA=11",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


def _build_ffmpeg_ethereal_pad(duration):
    """Generate soft sustained chords with slow evolution."""
    root = random.choice([110, 130, 146, 164])
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
        f"volume=1.5,afade=t=in:st=0:d=3.5,afade=t=out:st={duration-4}:d=4,loudnorm=I=-14:TP=-1.5:LRA=11",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


def _build_ffmpeg_deep_space(duration):
    """Generate vast cosmic ambience with slow pulsing tones."""
    base = random.choice([27, 30, 33, 36, 40])
    pulse = random.choice([0.05, 0.08, 0.1])
    return [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={base}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={int(base*2)}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={int(base*3)}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={int(base*4)}:duration={duration}",
        "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=brown:r=44100:a=0.015",
        "-filter_complex",
        f"[0:a]volume=0.25[s0];[1:a]volume=0.12[s1];[2:a]volume=0.06[s2];[3:a]volume=0.03[s3];"
        f"[s0][s1][s2][s3][4:a]amix=inputs=5:duration=longest,"
        f"lowpass=f=300,highpass=f=20,"
        f"aecho=0.9:0.95:200:0.5,aecho=0.8:0.9:400:0.3,"
        f"volume=1.5,afade=t=in:st=0:d=4,afade=t=out:st={duration-5}:d=5,loudnorm=I=-14:TP=-1.5:LRA=11",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


def _build_ffmpeg_rain_meditation(duration):
    """Generate gentle rain-like texture with soft melodic undertones."""
    base = random.choice([196, 220, 246, 261, 293])
    return [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={base}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={int(base*1.5)}:duration={duration}",
        "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=white:r=44100:a=0.04",
        "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=brown:r=44100:a=0.03",
        "-filter_complex",
        f"[0:a]volume=0.08[r0];[1:a]volume=0.06[r1];"
        f"[2:a]lowpass=f=3000[vn];[3:a]lowpass=f=800[bn];"
        f"[r0][r1][vn][bn]amix=inputs=4:duration=longest,"
        f"lowpass=f=2500,highpass=f=100,"
        f"volume=1.5,afade=t=in:st=0:d=2,afade=t=out:st={duration-3}:d=3,loudnorm=I=-14:TP=-1.5:LRA=11",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


def _build_ffmpeg_suspense_pulse(duration):
    """Generate rhythmic low pulse with eerie high harmonics."""
    base = random.choice([55, 62, 73, 82])
    harmonic = random.choice([base*4, base*5, base*6])
    return [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={base}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={int(harmonic)}:duration={duration}",
        "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=pink:r=44100:a=0.01",
        "-filter_complex",
        f"[0:a]volume=0.2[p0];[1:a]volume=0.04[p1];"
        f"[p0][p1][2:a]amix=inputs=3:duration=longest,"
        f"lowpass=f=500,highpass=f=30,"
        f"acompressor=threshold=0.1:ratio=4:attack=0.01:release=0.5,"
        f"volume=1.5,afade=t=in:st=0:d=1.5,afade=t=out:st={duration-3}:d=3,loudnorm=I=-14:TP=-1.5:LRA=11",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


def _build_ffmpeg_nostalgic_dream(duration):
    """Generate bittersweet chord progression with echo decay."""
    # Diminished or minor 7th chords for bittersweet feel
    root = random.choice([146, 164, 174, 196, 220])
    notes = [root, int(root*1.2), int(root*1.5), int(root*1.78)]
    return [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={notes[0]}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={notes[1]}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={notes[2]}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={notes[3]}:duration={duration}",
        "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=brown:r=44100:a=0.012",
        "-filter_complex",
        f"[0:a]volume=0.10[d0];[1:a]volume=0.08[d1];[2:a]volume=0.09[d2];[3:a]volume=0.06[d3];"
        f"[d0][d1][d2][d3][4:a]amix=inputs=5:duration=longest,"
        f"lowpass=f=1200,highpass=f=100,"
        f"aecho=0.85:0.9:80:0.45,aecho=0.8:0.88:160:0.25,aecho=0.75:0.85:320:0.1,"
        f"volume=1.5,afade=t=in:st=0:d=3,afade=t=out:st={duration-4}:d=4,loudnorm=I=-14:TP=-1.5:LRA=11",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


def _build_ffmpeg_void_ambience(duration):
    """Generate empty space texture with distant resonant frequencies."""
    base = random.choice([22, 25, 28, 31])
    return [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={base}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={int(base*8)}:duration={duration}",
        "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=brown:r=44100:a=0.02",
        "-filter_complex",
        f"[0:a]volume=0.2[v0];[1:a]volume=0.02[v1];"
        f"[v0][v1][2:a]amix=inputs=3:duration=longest,"
        f"lowpass=f=200,highpass=f=15,"
        f"aecho=0.95:0.97:300:0.6,"
        f"volume=1.5,afade=t=in:st=0:d=5,afade=t=out:st={duration-5}:d=5,loudnorm=I=-14:TP=-1.5:LRA=11",
        "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "128k",
    ]


# Map style names to builder functions
STYLE_BUILDERS = {
    "dark_drone": _build_ffmpeg_dark_drone,
    "cinematic_piano": _build_ffmpeg_cinematic_piano,
    "melodic_ambient": _build_ffmpeg_melodic_ambient,
    "tension_build": _build_ffmpeg_tension_build,
    "ethereal_pad": _build_ffmpeg_ethereal_pad,
    "deep_space": _build_ffmpeg_deep_space,
    "rain_meditation": _build_ffmpeg_rain_meditation,
    "suspense_pulse": _build_ffmpeg_suspense_pulse,
    "nostalgic_dream": _build_ffmpeg_nostalgic_dream,
    "void_ambience": _build_ffmpeg_void_ambience,
}


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _download_file(url, output_path, timeout=60):
    """Download a file from URL to local path."""
    response = requests.get(url, timeout=timeout, stream=True)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path


def _convert_to_mp3(input_path, mp3_path):
    """Convert any audio file to MP3 using FFmpeg (smaller file, Instagram compatible)."""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-c:a", "libmp3lame", "-b:a", "128k",
            mp3_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0 and os.path.exists(mp3_path):
            if input_path != mp3_path:
                os.remove(input_path)  # Clean up original
            return True
    except Exception:
        pass
    return False


# ─── Tier 1: Freesound API ───────────────────────────────────────────────────

# Freesound search queries optimized for philosophical/cinematic content
FREESOUND_QUERIES = [
    {"query": "dark ambient cinematic", "filter": "duration:[10 TO 300]"},
    {"query": "cinematic piano sad", "filter": "duration:[10 TO 180]"},
    {"query": "atmospheric drone", "filter": "duration:[15 TO 300]"},
    {"query": "dark cinematic tension", "filter": "duration:[10 TO 180]"},
    {"query": "ethereal ambient pad", "filter": "duration:[15 TO 300]"},
    {"query": "melancholic strings", "filter": "duration:[10 TO 180]"},
    {"query": "mysterious dark", "filter": "duration:[10 TO 180]"},
    {"query": "philosophical ambient", "filter": "duration:[15 TO 300]"},
    {"query": "rain ambient dark", "filter": "duration:[15 TO 300]"},
    {"query": "space ambient cosmic", "filter": "duration:[15 TO 300]"},
    {"query": "horror ambient atmosphere", "filter": "duration:[10 TO 180]"},
    {"query": "suspense dark background", "filter": "duration:[10 TO 120]"},
    {"query": "meditation drone deep", "filter": "duration:[20 TO 300]"},
    {"query": "cinematic emotional piano", "filter": "duration:[10 TO 180]"},
    {"query": "dark synth pad", "filter": "duration:[10 TO 180]"},
]


def fetch_music_freesound(freesound_token, temp_dir, history=None):
    """
    Search and download CC-licensed sounds from Freesound API.
    Free API token at: https://freesound.org/apiv2/apply/
    
    Access levels with token:
    - Search: Full text search with filters (duration, tags, license)
    - Preview download: HQ MP3 preview (~128kbps) — perfect for 15s reels
    - Full download: Requires OAuth2 (not needed for our use case)
    
    Returns: Path to MP3 file, or None
    """
    if not freesound_token or not freesound_token.strip():
        return None
    
    query_params = random.choice(FREESOUND_QUERIES)
    
    try:
        # Search Freesound API
        search_params = {
            "query": query_params["query"],
            "filter": query_params["filter"],
            "fields": "id,name,duration,previews,tags,license,download",
            "page_size": 15,
            "sort": "rating_desc",
            "token": freesound_token,
        }
        
        response = requests.get(
            "https://freesound.org/apiv2/search/text/",
            params=search_params,
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        if not results:
            print(f"   Freesound: no results for '{query_params['query']}'")
            return None
        
        # Filter out recently used sounds
        if history:
            recent_ids = history.get("recent_freesound_ids", [])
            fresh_results = [r for r in results if r["id"] not in recent_ids]
            if fresh_results:
                results = fresh_results
        
        # Pick a random result
        sound = random.choice(results)
        sound_id = sound["id"]
        sound_name = sound.get("name", "unknown")
        sound_duration = sound.get("duration", 0)
        
        print(f"   Freesound: found '{sound_name}' ({sound_duration:.0f}s, ID={sound_id})")
        
        # Get the preview URL (HQ MP3, 128kbps — excellent for 15s reels)
        previews = sound.get("previews", {})
        preview_url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
        
        if not preview_url:
            print(f"   Freesound: no preview URL available")
            return None
        
        # Download the preview
        output_path = os.path.join(temp_dir, "background_music.mp3")
        _download_file(preview_url, output_path, timeout=60)
        
        file_size = os.path.getsize(output_path)
        if file_size < 30000:
            print(f"   Freesound: preview too small ({file_size/1024:.0f} KB)")
            os.remove(output_path)
            return None
        
        print(f"   Freesound: downloaded '{sound_name}' ({file_size/1024:.0f} KB, {sound_duration:.0f}s)")
        
        if history:
            _mark_used("freesound_id", sound_id, history)
        
        return output_path
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print(f"   Freesound: invalid token — get one at https://freesound.org/apiv2/apply/")
        else:
            print(f"   Freesound: HTTP error {e.response.status_code}")
    except Exception as e:
        print(f"   Freesound: error — {e}")
    
    return None


# ─── Tier 2: Pixabay API ─────────────────────────────────────────────────────

def fetch_music_pixabay_api(api_key, temp_dir, history=None):
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
        "cinematic slow",
        "mysterious dark",
        "ambient cinematic dark",
        "dark background",
        "emotional cinematic",
        "atmospheric dark piano",
    ]
    search_term = random.choice(search_terms)
    
    try:
        params = {
            "key": api_key,
            "q": search_term,
            "category": "music",
            "per_page": 50,
            "safesearch": "true",
        }
        
        response = requests.get("https://pixabay.com/api/", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        hits = data.get("hits", [])
        if not hits:
            print(f"   No Pixabay results for '{search_term}'")
            return None
        
        # Pick a random track
        hit = random.choice(hits)
        
        # Try to get the audio download URL
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
                print(f"   Pixabay API music downloaded ({file_size/1024:.0f} KB, search: {search_term})")
                if history:
                    _mark_used("url", audio_url, history)
                return output_path
        
        print(f"   Pixabay hit had no download URL")
        
    except Exception as e:
        print(f"   Pixabay API error: {e}")
    
    return None


# ─── Tier 2: Mixkit SFX ──────────────────────────────────────────────────────

def fetch_music_mixkit(temp_dir, history=None):
    """
    Download atmospheric/cinematic audio from Mixkit (free, no auth).
    20+ tracks with different moods and durations.
    WAV files are auto-converted to MP3 for Instagram compatibility.
    """
    tracks = MIXKIT_TRACKS.copy()
    
    # Filter out recently used tracks
    if history:
        recent_ids = history.get("recent_mixkit_ids", [])
        fresh_tracks = [t for t in tracks if t["id"] not in recent_ids]
        if fresh_tracks:
            tracks = fresh_tracks
    
    random.shuffle(tracks)
    
    for track in tracks[:5]:  # Try up to 5 tracks
        mixkit_id = track["id"]
        url = f"https://assets.mixkit.co/active_storage/sfx/{mixkit_id}/{mixkit_id}.wav"
        wav_path = os.path.join(temp_dir, "background_music_raw.wav")
        mp3_path = os.path.join(temp_dir, "background_music.mp3")
        
        try:
            print(f"   Mixkit: downloading '{track['desc']}' (ID={mixkit_id}, ~{track['duration']}s)")
            _download_file(url, wav_path, timeout=90)
            file_size = os.path.getsize(wav_path)
            
            if file_size < 50000:
                print(f"   File too small ({file_size/1024:.0f} KB), trying next...")
                os.remove(wav_path)
                continue
            
            # Convert WAV to MP3 for smaller size & Instagram compatibility
            if _convert_to_mp3(wav_path, mp3_path):
                final_size = os.path.getsize(mp3_path)
                print(f"   Mixkit music ready ({final_size/1024:.0f} KB, mood: {track['mood']})")
                if history:
                    _mark_used("mixkit_id", mixkit_id, history)
                return mp3_path
            else:
                # If conversion fails, try using WAV directly
                os.rename(wav_path, mp3_path)
                print(f"   Mixkit music ready (WAV, mood: {track['mood']})")
                if history:
                    _mark_used("mixkit_id", mixkit_id, history)
                return mp3_path
                
        except Exception as e:
            print(f"   Mixkit download failed (ID={mixkit_id}): {e}")
    
    return None


# ─── Tier 3: Pixabay CDN ─────────────────────────────────────────────────────

def fetch_music_pixabay_cdn(temp_dir, history=None):
    """Download music from verified working Pixabay CDN URLs."""
    urls = PIXABAY_CDN_URLS.copy()
    
    # Filter out recently used
    if history:
        recent = history.get("recent_urls", [])
        fresh_urls = [u for u in urls if u not in recent]
        if fresh_urls:
            urls = fresh_urls
    
    random.shuffle(urls)
    
    for url in urls:
        output_path = os.path.join(temp_dir, "background_music.mp3")
        try:
            print(f"   Pixabay CDN: trying {url.split('/')[-1]}")
            _download_file(url, output_path, timeout=60)
            file_size = os.path.getsize(output_path)
            if file_size > 50000:
                print(f"   Pixabay CDN music downloaded ({file_size/1024:.0f} KB)")
                if history:
                    _mark_used("url", url, history)
                return output_path
            else:
                print(f"   File too small, trying next...")
                os.remove(output_path)
        except Exception as e:
            print(f"   CDN download failed: {e}")
    
    return None


# ─── Tier 4: FFmpeg Generated Music ──────────────────────────────────────────

def generate_ambient_music(temp_dir, duration=16, history=None):
    """
    Generate cinematic ambient music using FFmpeg.
    
    10 unique styles with randomized parameters = every reel sounds different:
      - Dark Drone: Deep sub-bass with harmonic overtones
      - Cinematic Piano: Minor key arpeggio with reverb echo
      - Melodic Ambient: Layered minor scale with warm filtering
      - Tension Build: Rising frequencies for psychological intensity
      - Ethereal Pad: Soft sustained chords, dreamy and meditative
      - Deep Space: Vast cosmic ambience with slow pulsing tones
      - Rain Meditation: Rain-like texture with soft melodic undertones
      - Suspense Pulse: Rhythmic low pulse with eerie high harmonics
      - Nostalgic Dream: Bittersweet chords with echo decay
      - Void Ambience: Empty space with distant resonant frequencies
    """
    output_path = os.path.join(temp_dir, "background_music.mp3")
    
    try:
        # Pick a style, avoiding recently used ones
        available_styles = list(STYLE_BUILDERS.keys())
        if history:
            recent_styles = history.get("recent_styles", [])
            fresh_styles = [s for s in available_styles if s not in recent_styles]
            if fresh_styles:
                available_styles = fresh_styles
        
        style_name = random.choice(available_styles)
        style_info = MUSIC_STYLES[style_name]
        builder = STYLE_BUILDERS[style_name]
        
        cmd = builder(duration)
        cmd.append(output_path)
        
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"   Generated '{style_info['name']}' music ({file_size/1024:.0f} KB)")
            print(f"   Mood: {style_info['mood']}")
            if history:
                _mark_used("style", style_name, history)
            return output_path
        else:
            print(f"   FFmpeg generation failed for style '{style_name}'")
            if result.stderr:
                # Print last line of stderr for debugging
                stderr_text = result.stderr.decode('utf-8', errors='replace')
                last_line = stderr_text.strip().split('\n')[-1] if stderr_text.strip() else ""
                if last_line:
                    print(f"   Error: {last_line}")
            
    except Exception as e:
        print(f"   Music generation error: {e}")
    
    return None


# ─── Main Entry Point ────────────────────────────────────────────────────────

def fetch_music(api_key, temp_dir, freesound_token=""):
    """
    Main music fetching function with 6-tier fallback.
    
    Priority:
    1. Freesound API (500K+ CC sounds) — needs free API token
    2. Pixabay API (thousands of real tracks) — needs free API key
    3. Mixkit SFX (20+ atmospheric tracks) — free, no auth, WAV→MP3
    4. Pixabay CDN (2 verified working URLs) — no key needed
    5. FFmpeg Ambient (10 unique styles, infinite variety) — always works
    6. Silent audio — absolute last resort
    
    Track History: Remembers recently used tracks to avoid repeats.
    
    Args:
        api_key: Pixabay API key (get free at https://pixabay.com/api/docs/)
        temp_dir: Directory to save the music file
        freesound_token: Freesound API token (get free at https://freesound.org/apiv2/apply/)
    
    Returns:
        str: Path to the music file (always returns something)
    """
    history = _load_history()
    
    # Tier 1: Freesound API (500K+ CC-licensed sounds — biggest variety)
    if freesound_token and freesound_token.strip():
        print("   [Tier 1/5] Trying Freesound API...")
        result = fetch_music_freesound(freesound_token, temp_dir, history)
        if result:
            return result
    
    # Tier 2: Pixabay API (thousands of real music tracks)
    if api_key and api_key.strip():
        print("   [Tier 2/5] Trying Pixabay API...")
        result = fetch_music_pixabay_api(api_key, temp_dir, history)
        if result:
            return result
    
    # Tier 3: Mixkit SFX (20+ atmospheric tracks, free)
    print("   [Tier 3/5] Trying Mixkit free music library...")
    result = fetch_music_mixkit(temp_dir, history)
    if result:
        return result
    
    # Tier 4: Pixabay CDN (quick fallback)
    print("   [Tier 4/5] Trying Pixabay CDN fallback...")
    result = fetch_music_pixabay_cdn(temp_dir, history)
    if result:
        return result
    
    # Tier 5: FFmpeg generated music (always works, 10 styles)
    print("   [Tier 5/5] Generating cinematic music with FFmpeg...")
    result = generate_ambient_music(temp_dir, history=history)
    if result:
        return result
    
    # Absolute last resort
    print("   All music methods failed — video will have silent audio")
    return None


# ─── AI Day Entry Point (FFmpeg Only) ────────────────────────────────────────

def fetch_ai_music(temp_dir, duration=16):
    """
    Fetch music for AI days using FFmpeg generation ONLY.
    
    No external APIs, no downloads — purely synthesized cinematic music.
    10 unique styles with randomized parameters = infinite variety.
    
    This is used on Mon/Wed/Fri (AI Days) in the weekly schedule.
    
    Args:
        temp_dir: Directory to save the music file
        duration: Duration in seconds (default 16 for 15s reel + 1s buffer)
    
    Returns:
        tuple: (music_path, music_detail) or (None, None) on failure
    """
    history = _load_history()
    
    print("   🤖 AI Day — Generating original music with FFmpeg...")
    result = generate_ambient_music(temp_dir, duration=duration, history=history)
    
    if result:
        # Determine which style was used for the detail string
        recent_styles = history.get("recent_styles", [])
        style_name = recent_styles[-1] if recent_styles else "unknown"
        style_info = MUSIC_STYLES.get(style_name, {"name": "Unknown", "mood": ""})
        music_detail = f"FFmpeg: {style_info['name']}"
        return result, music_detail
    
    # Absolute last resort — silent
    print("   ⚠️ FFmpeg generation failed — creating silent audio")
    return None, None


if __name__ == "__main__":
    os.makedirs("temp", exist_ok=True)
    
    # Test with no API key (tests Tiers 2-4)
    print("=== Testing music fetcher (no API key) ===\n")
    path = fetch_music("", "temp")
    print(f"\nMusic saved to: {path}")
    
    if path:
        # Show file info
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration,size", "-of", "csv=p=0", path],
                capture_output=True, text=True, timeout=10
            )
            print(f"File info: {result.stdout.strip()}")
        except Exception:
            pass
