#!/usr/bin/env python3
"""
Instagram Native Music — Search and attach trending music from Instagram's catalog.

Uses instagrapi's built-in music methods:
  - search_music()          — Search by keyword
  - music_trending()        — Get trending tracks
  - music_clips_audio_browser() — Browse music for Reels
  - clip_upload_as_reel_with_music() — Download track, mux audio, upload (MOST RELIABLE)
  - clip_upload_with_music()    — Upload with music metadata (server-side mixing)
  - track_download_by_url()     — Download track audio for manual muxing

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
    """
    if history is None:
        history = _load_history()
    
    track = None
    
    if not track:
        track = _try_preferred_tracks(cl, history)
    if not track:
        track = _try_trending(cl, history)
    if not track:
        track = _try_search(cl, history)
    if not track:
        track = _try_browse(cl, history)
    
    return track


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
    if not hasattr(cl, 'search_music'):
        return None
    preferred = PREFERRED_TRACK_NAMES.copy()
    random.shuffle(preferred)
    for track_name in preferred[:3]:
        try:
            logger.info(f"   🎵 Insta Music: Looking for '{track_name}'...")
            results = cl.search_music(track_name)
            if not results:
                continue
            tracks = _extract_tracks(results)
            if not tracks:
                continue
            fresh_tracks = [t for t in tracks if not _is_recently_used_track(_get_track_id(t), history)]
            if fresh_tracks:
                tracks = fresh_tracks
            return _format_track(tracks[0])
        except Exception as e:
            logger.warning(f"   ⚠️ Search for '{track_name}' failed: {e}")
    return None


def _try_trending(cl, history):
    if not hasattr(cl, 'music_trending'):
        return None
    try:
        logger.info("   🎵 Insta Music: Checking trending tracks...")
        result = cl.music_trending(product="story_camera_clips_v2")
        if not result:
            return None
        tracks = _extract_tracks(result)
        if not tracks:
            return None
        fresh_tracks = [t for t in tracks if not _is_recently_used_track(_get_track_id(t), history)]
        if fresh_tracks:
            tracks = fresh_tracks
        selected = random.choice(tracks[:min(10, len(tracks))])
        return _format_track(selected)
    except Exception as e:
        logger.warning(f"   ⚠️ Insta trending failed: {e}")
        return None


def _try_search(cl, history):
    queries = MUSIC_SEARCH_QUERIES.copy()
    random.shuffle(queries)
    for query in queries[:5]:
        try:
            logger.info(f"   🎵 Insta Music: Searching '{query}'...")
            results = cl.search_music(query)
            if not results:
                continue
            tracks = _extract_tracks(results)
            if not tracks:
                continue
            fresh_tracks = [t for t in tracks if not _is_recently_used_track(_get_track_id(t), history)]
            if fresh_tracks:
                tracks = fresh_tracks
            selected = random.choice(tracks[:min(5, len(tracks))])
            return _format_track(selected)
        except Exception as e:
            logger.warning(f"   ⚠️ Insta search '{query}' failed: {e}")
    return None


def _try_browse(cl, history):
    if not hasattr(cl, 'music_clips_audio_browser'):
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
        fresh_tracks = [t for t in tracks if not _is_recently_used_track(_get_track_id(t), history)]
        if fresh_tracks:
            tracks = fresh_tracks
        selected = random.choice(tracks[:min(10, len(tracks))])
        return _format_track(selected)
    except Exception as e:
        logger.warning(f"   ⚠️ Insta browse failed: {e}")
        return None


# ─── Track Helpers ────────────────────────────────────────────────────────────

def _extract_tracks(result):
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for key in ['tracks', 'items', 'audio']:
            if key in result and isinstance(result[key], list):
                return result[key]
    return []


def _get_track_id(track):
    if isinstance(track, dict):
        return track.get('id') or track.get('audio_asset_id') or track.get('pk', '')
    return getattr(track, 'id', '') or getattr(track, 'pk', '') or ''


def _get_track_attr(track, attr):
    """Get an attribute from a track object or dict."""
    if isinstance(track, dict):
        return track.get(attr)
    return getattr(track, attr, None)


def _format_track(track):
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


def _mux_audio_ffmpeg(video_path, audio_path, temp_dir):
    """
    Use FFmpeg to replace the video's audio with the downloaded music track.
    Returns path to muxed video, or None if failed.
    """
    import subprocess
    
    output_path = os.path.join(temp_dir, "reel_with_music.mp4")
    
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"   🎵 FFmpeg: muxed audio into video ({file_size / (1024*1024):.1f} MB)")
            return output_path
        else:
            logger.warning(f"   ⚠️ FFmpeg mux failed: {result.stderr[-200:]}")
            return None
    except Exception as e:
        logger.warning(f"   ⚠️ FFmpeg mux error: {e}")
        return None


def upload_reel_with_instagram_music(cl, video_path, caption, track_info, history=None):
    """
    Upload a reel with Instagram's native music attached.
    
    Tries multiple upload methods in order:
    1. clip_upload_as_reel_with_music() — downloads track, muxes audio with MoviePy, uploads
       (Most reliable — video has actual audio baked in + proper metadata)
    2. FFmpeg audio mux + clip_upload_with_music() — manual audio muxing fallback
    3. clip_upload_with_music() — metadata-only (less reliable with silent video audio)
    4. clip_upload() without music — graceful fallback
    
    WHY Method 1 is best: clip_upload_with_music() only adds METADATA about the music
    track. It does NOT mux audio into the video. When the video has a silent/empty
    audio track, Instagram's server-side audio mixing often fails silently, resulting
    in the music showing as attached but not being audible. Method 1 actually downloads
    the music, muxes it into the video file, and uploads with proper metadata.
    """
    import time
    
    if history is None:
        history = _load_history()
    
    raw_track = track_info.get("raw_track")
    track_name = track_info.get("name", "Unknown")
    track_artist = track_info.get("artist", "")
    track_id = track_info.get("id", "")
    
    logger.info(f"   🎵 Attaching Instagram music: {track_name} by {track_artist}")
    
    thumbnail_path = _generate_thumbnail(video_path)
    errors = []
    
    # ── Method 1: clip_upload_as_reel_with_music (BEST — muxes audio locally) ──
    if raw_track and hasattr(cl, 'clip_upload_as_reel_with_music'):
        try:
            logger.info("   🎵 Method 1: clip_upload_as_reel_with_music (downloads & muxes audio)...")
            track_uri = _get_track_attr(raw_track, "uri")
            if track_uri:
                media = cl.clip_upload_as_reel_with_music(
                    path=video_path,
                    caption=caption,
                    track=raw_track,
                    extra_data={
                        "source_type": "4",
                        "delivery_class": "organic",
                    }
                )
                if media:
                    logger.info(f"   ✅ Reel uploaded with music (muxed)! ID: {media.pk}")
                    _mark_track_used(track_id, f"{track_name} - {track_artist}", history)
                    return {
                        "id": media.pk,
                        "code": media.code,
                        "status": "uploaded_with_music_muxed",
                        "music_track": track_name,
                        "music_artist": track_artist,
                    }
            else:
                logger.warning("   ⚠️ Track has no URI — can't download for muxing")
                errors.append("track has no uri")
        except Exception as e:
            errors.append(f"clip_upload_as_reel_with_music: {str(e)[:100]}")
            logger.warning(f"   ⚠️ Method 1 failed: {str(e)[:100]}")
    elif not raw_track:
        errors.append("no raw_track provided")
    else:
        errors.append("clip_upload_as_reel_with_music not available")
    
    # ── Method 2: FFmpeg audio mux + clip_upload_with_music ──────────────────
    if raw_track and hasattr(cl, 'track_download_by_url') and hasattr(cl, 'clip_upload_with_music'):
        try:
            logger.info("   🔄 Method 2: FFmpeg audio mux + clip_upload_with_music...")
            track_uri = _get_track_attr(raw_track, "uri")
            if track_uri:
                import tempfile
                import shutil
                tmp_dir = tempfile.mkdtemp()
                try:
                    tmpaudio = cl.track_download_by_url(track_uri, "track", tmp_dir)
                    if tmpaudio and os.path.exists(str(tmpaudio)):
                        muxed_path = _mux_audio_ffmpeg(video_path, str(tmpaudio), tmp_dir)
                        if muxed_path:
                            highlight_start = _get_track_attr(raw_track, "highlight_start_times_in_ms") or [0]
                            audio_start = int(highlight_start[0]) if highlight_start else 0
                            media = cl.clip_upload_with_music(
                                path=muxed_path,
                                caption=caption,
                                track=raw_track,
                                thumbnail=thumbnail_path,
                                music_volume=1.0,
                                original_volume=0.0,
                                audio_asset_start_time=audio_start,
                                extra_data={
                                    "source_type": "4",
                                    "delivery_class": "organic",
                                }
                            )
                            if media:
                                logger.info(f"   ✅ Reel uploaded (FFmpeg muxed + metadata)! ID: {media.pk}")
                                _mark_track_used(track_id, f"{track_name} - {track_artist}", history)
                                return {
                                    "id": media.pk,
                                    "code": media.code,
                                    "status": "uploaded_with_music_ffmpeg_muxed",
                                    "music_track": track_name,
                                    "music_artist": track_artist,
                                }
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            else:
                errors.append("track has no uri for download")
        except Exception as e:
            errors.append(f"ffmpeg_mux: {str(e)[:80]}")
            logger.warning(f"   ⚠️ Method 2 failed: {str(e)[:80]}")
    
    # ── Method 3: clip_upload_with_music (metadata-only) ─────────────────────
    if raw_track and hasattr(cl, 'clip_upload_with_music'):
        try:
            logger.info("   🔄 Method 3: clip_upload_with_music (metadata-only)...")
            media = cl.clip_upload_with_music(
                path=video_path,
                caption=caption,
                track=raw_track,
                thumbnail=thumbnail_path,
                music_volume=1.0,
                original_volume=0.0,
                # audio_asset_start_time=None -> uses track's highlight_start_times_in_ms
                extra_data={
                    "source_type": "4",
                    "delivery_class": "organic",
                }
            )
            if media:
                logger.info(f"   ✅ Reel uploaded (metadata music)! ID: {media.pk}")
                _mark_track_used(track_id, f"{track_name} - {track_artist}", history)
                return {
                    "id": media.pk,
                    "code": media.code,
                    "status": "uploaded_with_music_metadata",
                    "music_track": track_name,
                    "music_artist": track_artist,
                }
        except Exception as e:
            errors.append(f"clip_upload_with_music: {str(e)[:80]}")
            logger.warning(f"   ⚠️ Method 3 failed: {str(e)[:80]}")
    
    # ── Method 4: Plain clip_upload without music (graceful fallback) ────────
    if hasattr(cl, 'clip_upload'):
        try:
            logger.info("   🔄 Method 4: Uploading without music (plain clip_upload)...")
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
                logger.warning("   ⚠️  Music was NOT attached — all music methods failed")
                return {
                    "id": media.pk,
                    "code": media.code,
                    "status": "uploaded_no_music",
                    "music_track": None,
                    "music_artist": None,
                }
        except Exception as e:
            errors.append(f"clip_upload: {str(e)[:80]}")
            logger.error(f"   ❌ Method 4 also failed: {e}")
    
    error_summary = " | ".join(errors)
    raise RuntimeError(f"All upload methods failed: {error_summary}")


if __name__ == "__main__":
    print("This module is used by main.py. Run main.py instead.")
