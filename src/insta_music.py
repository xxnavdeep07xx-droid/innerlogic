#!/usr/bin/env python3
"""
Instagram Native Music — Search and attach trending music from Instagram's catalog.

Uses instagrapi's built-in music methods:
  - search_music()          — Search by keyword
  - music_trending()        — Get trending tracks
  - music_clips_audio_browser() — Browse music for Reels
  - clip_upload_with_music()    — Upload reel with music (server-side mixing)

Track History: Avoids repeating the same song within the next 5 reels.
"""

import os
import json
import random
import logging
from pathlib import Path

logger = logging.getLogger("innerlogic")


# ─── Configuration ────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"
HISTORY_FILE = DATA_DIR / "music_history.json"

# Max number of recent tracks to remember (no repeat within N reels)
NO_REPEAT_WINDOW = 5

# Search queries for philosophical/cinematic content
# Prioritize specific popular tracks known to work well for philosophical reels
MUSIC_SEARCH_QUERIES = [
    "Homage",
    "Golden Brown",
    "Maritza",
    "Blue",
    "Interstellar",
    "Time Hans Zimmer",
    "Experience Ludovico",
    "Nuvole Bianche",
    "River Flows in You",
    "Cinematic Piano",
    "Epic Emotional",
    "Dark Atmospheric",
    "Melancholy Piano",
    "Mysterious Cinematic",
    "Philosophical Ambient",
    "Haunting Beautiful",
    "Sad Classical",
    "Deep Thought",
    "Meditative Calm",
    "Ethereal Dream",
]

# Browse product types for reels
BROWSE_PRODUCTS = [
    "story_camera_clips_v2",
    "clips_audio_browser",
]


# ─── History Management ──────────────────────────────────────────────────────

def _load_history():
    """Load music history from file."""
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "recent_urls": [],
        "recent_mixkit_ids": [],
        "recent_styles": [],
        "recent_insta_track_ids": [],
        "recent_insta_track_names": [],
    }


def _save_history(history):
    """Save music history to file."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


def _is_recently_used_track(track_id, history):
    """Check if a track was used in the last N reels."""
    recent_ids = history.get("recent_insta_track_ids", [])
    return track_id in recent_ids


def _mark_track_used(track_id, track_name, history):
    """Mark a track as recently used."""
    history.setdefault("recent_insta_track_ids", []).append(track_id)
    history["recent_insta_track_ids"] = history["recent_insta_track_ids"][-NO_REPEAT_WINDOW:]
    
    history.setdefault("recent_insta_track_names", []).append(track_name)
    history["recent_insta_track_names"] = history["recent_insta_track_names"][-NO_REPEAT_WINDOW:]
    
    _save_history(history)


# ─── Music Search & Selection ────────────────────────────────────────────────

def search_and_select_track(cl, history=None):
    """
    Search Instagram's music catalog and select a track.
    Uses multiple strategies to find a good track:
    
    1. Try searching for specific popular tracks (Homage, Golden Brown, etc.)
    2. Try trending music
    3. Try keyword search with curated queries
    4. Try browsing the clips audio browser
    
    Avoids tracks used in the last 5 reels.
    
    Args:
        cl: Authenticated instagrapi Client
        history: Music history dict (loaded if None)
    
    Returns:
        dict: Track info with keys: id, name, artist, subtitle, 
              or None if no track found
    """
    if history is None:
        history = _load_history()
    
    track = None
    
    # Strategy 0: Search for specific preferred tracks first
    if not track:
        track = _try_preferred_tracks(cl, history)
    
    # Strategy 1: Trending music
    if not track:
        track = _try_trending(cl, history)
    
    # Strategy 2: Keyword search
    if not track:
        track = _try_search(cl, history)
    
    # Strategy 3: Browse clips audio
    if not track:
        track = _try_browse(cl, history)
    
    return track


# Preferred tracks — known to work well for philosophical/cinematic reels
PREFERRED_TRACK_NAMES = [
    "Homage",
    "Golden Brown",
    "Maritza",
    "Blue",
    "Interstellar",
    "Experience",
    "Nuvole Bianche",
    "Time",
]


def _try_preferred_tracks(cl, history):
    """Try to find specific preferred tracks by name."""
    if not hasattr(cl, 'search_music'):
        return None
    
    # Shuffle preferred tracks to vary selection
    preferred = PREFERRED_TRACK_NAMES.copy()
    random.shuffle(preferred)
    
    for track_name in preferred[:3]:  # Try top 3
        try:
            logger.info(f"   🎵 Insta Music: Looking for '{track_name}'...")
            results = cl.search_music(track_name)
            
            if not results:
                continue
            
            tracks = _extract_tracks(results)
            
            if not tracks:
                continue
            
            # Filter out recently used
            fresh_tracks = [
                t for t in tracks 
                if not _is_recently_used_track(_get_track_id(t), history)
            ]
            
            if fresh_tracks:
                tracks = fresh_tracks
            
            # Pick the first result (most relevant match)
            selected = tracks[0]
            return _format_track(selected)
            
        except Exception as e:
            logger.warning(f"   ⚠️ Search for '{track_name}' failed: {e}")
            continue
    
    return None


def _try_trending(cl, history):
    """Try to find a track from Instagram's trending music."""
    if not hasattr(cl, 'music_trending'):
        logger.warning("   ⚠️ music_trending not available in this instagrapi version")
        return None
    try:
        logger.info("   🎵 Insta Music: Checking trending tracks...")
        result = cl.music_trending(product="story_camera_clips_v2")
        
        if not result:
            return None
        
        # result can be a dict with 'tracks' or a list of Track objects
        tracks = _extract_tracks(result)
        
        if not tracks:
            return None
        
        # Filter out recently used
        fresh_tracks = [
            t for t in tracks 
            if not _is_recently_used_track(_get_track_id(t), history)
        ]
        
        if fresh_tracks:
            tracks = fresh_tracks
        
        # Pick a random track from top options
        selected = random.choice(tracks[:min(10, len(tracks))])
        return _format_track(selected)
        
    except Exception as e:
        logger.warning(f"   ⚠️ Insta trending failed: {e}")
        return None


def _try_search(cl, history):
    """Try to find a track via keyword search."""
    queries = MUSIC_SEARCH_QUERIES.copy()
    random.shuffle(queries)
    
    for query in queries[:3]:  # Try up to 3 queries
        try:
            logger.info(f"   🎵 Insta Music: Searching '{query}'...")
            results = cl.search_music(query)
            
            if not results:
                continue
            
            tracks = _extract_tracks(results)
            
            if not tracks:
                continue
            
            # Filter out recently used
            fresh_tracks = [
                t for t in tracks 
                if not _is_recently_used_track(_get_track_id(t), history)
            ]
            
            if fresh_tracks:
                tracks = fresh_tracks
            
            selected = random.choice(tracks[:min(5, len(tracks))])
            return _format_track(selected)
            
        except Exception as e:
            logger.warning(f"   ⚠️ Insta search '{query}' failed: {e}")
            continue
    
    return None


def _try_browse(cl, history):
    """Try to find a track from the clips audio browser."""
    if not hasattr(cl, 'music_clips_audio_browser'):
        logger.warning("   ⚠️ music_clips_audio_browser not available in this instagrapi version")
        return None
    try:
        product = random.choice(BROWSE_PRODUCTS)
        logger.info(f"   🎵 Insta Music: Browsing clips audio ({product})...")
        result = cl.music_clips_audio_browser(product=product)
        
        if not result:
            return None
        
        tracks = _extract_tracks(result)
        
        if not tracks:
            return None
        
        # Filter out recently used
        fresh_tracks = [
            t for t in tracks 
            if not _is_recently_used_track(_get_track_id(t), history)
        ]
        
        if fresh_tracks:
            tracks = fresh_tracks
        
        selected = random.choice(tracks[:min(10, len(tracks))])
        return _format_track(selected)
        
    except Exception as e:
        logger.warning(f"   ⚠️ Insta browse failed: {e}")
        return None


# ─── Track Helpers ────────────────────────────────────────────────────────────

def _extract_tracks(result):
    """
    Extract track list from various response formats.
    Handles both dict responses and lists of Track objects.
    """
    if isinstance(result, list):
        return result
    
    if isinstance(result, dict):
        # Could have 'tracks', 'items', or be the track list directly
        for key in ['tracks', 'items', 'audio']:
            if key in result and isinstance(result[key], list):
                return result[key]
    
    return []


def _get_track_id(track):
    """Extract track ID from various track formats."""
    if isinstance(track, dict):
        return track.get('id') or track.get('audio_asset_id') or track.get('pk', '')
    # instagrapi Track object
    return getattr(track, 'id', '') or getattr(track, 'pk', '') or ''


def _format_track(track):
    """
    Format a track into a standardized dict for use with clip_upload_with_music.
    
    Returns:
        dict with keys: id, name, artist, subtitle, raw_track
    """
    if isinstance(track, dict):
        track_id = track.get('id') or track.get('audio_asset_id') or track.get('pk', '')
        name = track.get('title') or track.get('name', 'Unknown')
        artist = track.get('subtitle') or track.get('artist', '')
        subtitle = track.get('subtitle', '')
        
        return {
            "id": track_id,
            "name": name,
            "artist": artist,
            "subtitle": subtitle,
            "raw_track": track,
        }
    
    # instagrapi Track object
    track_id = getattr(track, 'id', '') or getattr(track, 'pk', '')
    name = getattr(track, 'title', '') or getattr(track, 'name', 'Unknown')
    artist = getattr(track, 'subtitle', '') or getattr(track, 'artist', '')
    subtitle = getattr(track, 'subtitle', '')
    
    return {
        "id": track_id,
        "name": name,
        "artist": artist,
        "subtitle": subtitle,
        "raw_track": track,
    }


# ─── Upload with Music ───────────────────────────────────────────────────────

def _generate_thumbnail(video_path):
    """Generate a thumbnail from the video using FFmpeg."""
    import subprocess
    thumbnail_path = None
    try:
        thumbnail_path = video_path + ".jpg"
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-ss", "0.5",
             "-vframes", "1", "-q:v", "2", thumbnail_path],
            capture_output=True, timeout=30
        )
        if result.returncode == 0 and os.path.exists(thumbnail_path):
            logger.info("   🖼️  Thumbnail generated")
        else:
            thumbnail_path = None
    except Exception:
        thumbnail_path = None
    return thumbnail_path


def upload_reel_with_instagram_music(cl, video_path, caption, track_info, history=None):
    """
    Upload a reel with Instagram's native music attached.
    
    Tries multiple upload methods in order:
    1. clip_upload_with_music() — all-in-one upload with music
    2. clip_music_extra_data() + clip_upload() — manual music data attachment
    3. clip_upload() without music — graceful fallback
    
    Args:
        cl: Authenticated instagrapi Client
        video_path: Path to the video file
        caption: Caption text with hashtags
        track_info: Track info dict from search_and_select_track()
        history: Music history dict (loaded if None)
    
    Returns:
        dict: Upload result with media ID
    """
    import time
    
    if history is None:
        history = _load_history()
    
    # Get the raw track object (instagrapi Track or dict)
    raw_track = track_info.get("raw_track")
    
    track_name = track_info.get("name", "Unknown")
    track_artist = track_info.get("artist", "")
    track_id = track_info.get("id", "")
    
    logger.info(f"   🎵 Attaching Instagram music: {track_name} by {track_artist}")
    
    # Generate thumbnail
    thumbnail_path = _generate_thumbnail(video_path)
    
    errors = []
    
    # ── Method 1: clip_upload_with_music (all-in-one) ────────────────────────
    if raw_track and hasattr(cl, 'clip_upload_with_music'):
        try:
            logger.info("   🎵 Method 1: clip_upload_with_music...")
            media = cl.clip_upload_with_music(
                path=video_path,
                caption=caption,
                track=raw_track,
                thumbnail=thumbnail_path,
                music_volume=1.0,
                original_volume=0.0,
                audio_asset_start_time=0,
                extra_data={
                    "source_type": "4",
                    "delivery_class": "organic",
                    "upload_id": str(int(time.time() * 1000)),
                }
            )
            
            if media:
                logger.info(f"   ✅ Reel uploaded with Instagram music! ID: {media.pk}")
                _mark_track_used(track_id, f"{track_name} - {track_artist}", history)
                return {
                    "id": media.pk,
                    "code": media.code,
                    "status": "uploaded_with_music",
                    "music_track": track_name,
                    "music_artist": track_artist,
                }
        except Exception as e:
            errors.append(f"clip_upload_with_music: {str(e)[:80]}")
            logger.warning(f"   ⚠️ Method 1 failed: {str(e)[:80]}")
    elif not raw_track:
        errors.append("no raw_track provided")
    else:
        errors.append("clip_upload_with_music not available")
    
    # ── Method 2: clip_music_extra_data + clip_upload ────────────────────────
    if raw_track and hasattr(cl, 'clip_music_extra_data') and hasattr(cl, 'clip_upload'):
        try:
            logger.info("   🔄 Method 2: clip_music_extra_data + clip_upload...")
            music_data = cl.clip_music_extra_data(
                track=raw_track,
                music_volume=1.0,
                original_volume=0.0,
            )
            
            media = cl.clip_upload(
                path=video_path,
                caption=caption,
                thumbnail=thumbnail_path,
                extra_data={
                    **music_data,
                    "source_type": "4",
                    "delivery_class": "organic",
                    "upload_id": str(int(time.time() * 1000)),
                }
            )
            
            if media:
                logger.info(f"   ✅ Reel uploaded with music (method 2)! ID: {media.pk}")
                _mark_track_used(track_id, f"{track_name} - {track_artist}", history)
                return {
                    "id": media.pk,
                    "code": media.code,
                    "status": "uploaded_with_music_method2",
                    "music_track": track_name,
                    "music_artist": track_artist,
                }
        except Exception as e:
            errors.append(f"clip_music_extra_data: {str(e)[:80]}")
            logger.warning(f"   ⚠️ Method 2 failed: {str(e)[:80]}")
    
    # ── Method 3: Plain clip_upload without music (graceful fallback) ────────
    if hasattr(cl, 'clip_upload'):
        try:
            logger.info("   🔄 Method 3: Uploading without music (plain clip_upload)...")
            media = cl.clip_upload(
                path=video_path,
                caption=caption,
                thumbnail=thumbnail_path,
                extra_data={
                    "source_type": "4",
                    "delivery_class": "organic",
                    "upload_id": str(int(time.time() * 1000)),
                }
            )
            
            if media:
                logger.info(f"   ✅ Reel uploaded (no music attached)! ID: {media.pk}")
                logger.warning("   ⚠️  Music was NOT attached — Instagram music methods failed")
                return {
                    "id": media.pk,
                    "code": media.code,
                    "status": "uploaded_no_music",
                    "music_track": None,
                    "music_artist": None,
                }
        except Exception as e:
            errors.append(f"clip_upload: {str(e)[:80]}")
            logger.error(f"   ❌ Method 3 also failed: {e}")
    
    # All methods failed
    error_summary = " | ".join(errors)
    raise RuntimeError(f"All upload methods failed: {error_summary}")


if __name__ == "__main__":
    print("This module is used by main.py. Run main.py instead.")
    print("To test Instagram music search, use:")
    print("  python3 -c 'from src.insta_music import search_and_select_track'")
