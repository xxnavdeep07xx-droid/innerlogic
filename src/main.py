#!/usr/bin/env python3
"""
Inner Logic — Instagram Reel Automation
========================================
Main orchestrator that ties together all pipeline steps:

Weekly Schedule:
    Monday    = 🤖 AI Day     (FFmpeg-generated original music)
    Tuesday   = 🎵 Insta Day  (Instagram's native trending music)
    Wednesday = 🤖 AI Day     (FFmpeg-generated original music)
    Thursday  = 🎵 Insta Day  (Instagram's native trending music)
    Friday    = 🤖 AI Day     (FFmpeg-generated original music)
    Saturday  = 🎵 Insta Day  (Instagram's native trending music)
    Sunday    = 📊 Rest Day   (No posting — weekly summary only)

Pipeline Steps (AI Day):
    1. Scrape a unique philosophical quote from the web
    2. Download fonts (Cormorant Garamond + Montserrat)
    3. Generate a dark cinematic background image
    4. Generate original music with FFmpeg (10 styles)
    5. Create a 15-second reel with MoviePy/FFmpeg
    6. Wait for best posting time (smart scheduler)
    7. Post reel to Instagram via instagrapi
    8. Record performance for future optimization

Pipeline Steps (Insta Day):
    1. Scrape a unique philosophical quote from the web
    2. Download fonts (Cormorant Garamond + Montserrat)
    3. Generate a dark cinematic background image
    4. Create a 15-second reel WITHOUT music (silent audio)
    5. Wait for best posting time (smart scheduler)
    6. Login to Instagram, search trending music
    7. Upload reel with Instagram native music attached
    8. Record performance for future optimization

Pipeline Steps (Rest Day):
    1. Generate weekly summary (.md)
    2. Done — no reel, no posting
"""

import os
import sys
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quote_scraper import pick_quote_from_web
from quote_picker import pick_quote
from image_generator import generate_image
from music_fetcher import fetch_music, fetch_ai_music
from video_creator import create_reel
from caption_generator import generate_caption
from instagram import post_reel, login
from fonts_setup import ensure_fonts
from smart_scheduler import (
    calculate_best_time,
    wait_until_best_time,
    record_post,
    load_performance_data,
)
from scheduler import (
    get_today_info,
    should_post_today,
    should_use_instagram_music,
    should_use_ai_music,
    is_rest_day,
    record_daily_run,
)
from weekly_summary import generate_weekly_summary

# ─── Configuration ───────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
TEMP_DIR = PROJECT_ROOT / "temp"
DATA_DIR = PROJECT_ROOT / "data"
FONTS_DIR = PROJECT_ROOT / "fonts"
QUOTES_FILE = DATA_DIR / "quotes.json"
USED_QUOTES_FILE = DATA_DIR / "used_quotes.json"

# Instagram credentials (instagrapi — username/password, no tokens!)
INSTAGRAM_USERNAME = os.environ.get("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.environ.get("INSTAGRAM_PASSWORD", "")

# Optional: 2FA TOTP secret
INSTAGRAM_TOTP_SECRET = os.environ.get("INSTAGRAM_TOTP_SECRET", "")

# API keys (optional — used as fallback on AI days)
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
FREESOUND_TOKEN = os.environ.get("FREESOUND_TOKEN", "")

# Smart scheduling: Set to "true" to auto-find the best posting time
SMART_SCHEDULING = os.environ.get("SMART_SCHEDULING", "true").lower() == "true"

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("innerlogic")


# ─── Setup ────────────────────────────────────────────────────────────────────

def validate_env():
    """Validate that all required environment variables are set."""
    missing = []
    if not INSTAGRAM_USERNAME:
        missing.append("INSTAGRAM_USERNAME")
    if not INSTAGRAM_PASSWORD:
        missing.append("INSTAGRAM_PASSWORD")
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)
    
    logger.info("✅ All environment variables validated")


def setup_temp_dir():
    """Create and clean the temporary directory."""
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ Temp directory ready: {TEMP_DIR}")


def cleanup():
    """Remove all temporary files."""
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    logger.info("✅ Cleanup complete")


# ─── AI Day Pipeline (FFmpeg Music) ─────────────────────────────────────────

def run_ai_day_pipeline(today_info):
    """
    Run the pipeline for AI Day (Mon/Wed/Fri).
    
    Uses FFmpeg-generated music. No external APIs needed.
    The music is baked into the video, then uploaded normally.
    """
    start_time = datetime.now()
    mode = today_info["mode"]
    
    logger.info(f"🤖 AI Day Pipeline — {today_info['day_name']}, {today_info['date_ist']}")
    
    try:
        # Step 1: Scrape a unique quote
        logger.info("💡 Step 1/8: Scraping a unique philosophical quote...")
        quote = pick_quote_from_web(str(USED_QUOTES_FILE))
        logger.info(f"   📝 \"{quote['text'][:60]}...\" — {quote['author']}")
        logger.info(f"   🔗 Source: {quote.get('source', 'unknown')}")
        
        # Step 2: Download fonts
        logger.info("🔤 Step 2/8: Ensuring fonts are available...")
        font_paths = ensure_fonts(str(FONTS_DIR))
        logger.info("   ✅ Fonts ready")
        
        # Step 3: Generate background image
        logger.info("🎨 Step 3/8: Generating dark cinematic image...")
        image_path = generate_image(quote, str(TEMP_DIR))
        logger.info(f"   🖼️  Image saved: {image_path}")
        
        # Step 4: Generate AI music (FFmpeg only)
        logger.info("🎵 Step 4/8: Generating original AI music with FFmpeg...")
        music_path, music_detail = fetch_ai_music(str(TEMP_DIR))
        if music_path:
            logger.info(f"   🎶 AI music generated: {music_detail}")
        else:
            logger.warning("   ⚠️ AI music generation failed — will use fallback")
        
        # Step 5: Create video reel
        logger.info("🎬 Step 5/8: Creating 15-second reel...")
        
        # If we have AI music, use it. Otherwise try the full fallback chain.
        if music_path:
            video_path = create_reel(
                image_path=image_path,
                music_path=music_path,
                quote=quote,
                temp_dir=str(TEMP_DIR),
                font_paths=font_paths
            )
        else:
            # Fallback: use the full 6-tier music fetcher
            logger.info("   🔄 Falling back to full music fetcher chain...")
            fallback_music = fetch_music(PIXABAY_API_KEY, str(TEMP_DIR), FREESOUND_TOKEN)
            video_path = create_reel(
                image_path=image_path,
                music_path=fallback_music,
                quote=quote,
                temp_dir=str(TEMP_DIR),
                font_paths=font_paths
            )
            music_detail = "fallback_chain"
        
        logger.info(f"   📹 Video saved: {video_path}")
        
        # Step 6: Generate caption
        logger.info("📝 Step 6/8: Generating caption & hashtags...")
        caption = generate_caption(quote)
        logger.info(f"   📋 Caption: {caption[:80]}...")
        
        # Step 7: Smart scheduling
        logger.info("⏰ Step 7/8: Smart scheduling — finding the best time to post...")
        
        if SMART_SCHEDULING:
            logger.info("   📊 Analyzing past reel performance...")
            best_hour = calculate_best_time()
            logger.info(f"   🏆 Best time today: {best_hour:02d}:00 IST")
            wait_until_best_time(best_hour)
        else:
            logger.info("   📋 Smart scheduling disabled — posting now")
        
        # Step 8: Post reel to Instagram (normal upload — music is baked in)
        logger.info("📱 Step 8/8: Posting reel to Instagram...")
        result = post_reel(
            video_path=video_path,
            caption=caption
        )
        logger.info(f"   ✅ Reel posted successfully! ID: {result.get('id', 'unknown')}")
        
        # Record this post
        try:
            media_code = result.get("code", "")
            if media_code:
                record_post(
                    media_code=media_code,
                    posted_at_utc=datetime.utcnow(),
                    hour_ist=None,
                )
                logger.info("   📊 Post recorded for future scheduling optimization")
        except Exception as e:
            logger.warning(f"   ⚠️  Could not record post performance: {e}")
        
        # Record in schedule state
        record_daily_run(
            mode=mode,
            quote_text=quote.get("text", ""),
            quote_author=quote.get("author", ""),
            music_source="ffmpeg",
            music_detail=music_detail or "unknown",
            post_result=result,
        )
        
        # Done!
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"🎉 AI Day pipeline complete! Total time: {elapsed:.1f}s")
        
    except Exception as e:
        logger.error(f"❌ AI Day pipeline failed: {str(e)}")
        record_daily_run(mode=mode, error=str(e))
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


# ─── Insta Day Pipeline (Instagram Native Music) ────────────────────────────

def run_insta_day_pipeline(today_info):
    """
    Run the pipeline for Insta Day (Tue/Thu/Sat).
    
    Creates reel WITHOUT music, then attaches Instagram's native
    trending music during upload via clip_upload_with_music().
    """
    start_time = datetime.now()
    mode = today_info["mode"]
    
    logger.info(f"🎵 Insta Day Pipeline — {today_info['day_name']}, {today_info['date_ist']}")
    
    try:
        # Step 1: Scrape a unique quote
        logger.info("💡 Step 1/8: Scraping a unique philosophical quote...")
        quote = pick_quote_from_web(str(USED_QUOTES_FILE))
        logger.info(f"   📝 \"{quote['text'][:60]}...\" — {quote['author']}")
        logger.info(f"   🔗 Source: {quote.get('source', 'unknown')}")
        
        # Step 2: Download fonts
        logger.info("🔤 Step 2/8: Ensuring fonts are available...")
        font_paths = ensure_fonts(str(FONTS_DIR))
        logger.info("   ✅ Fonts ready")
        
        # Step 3: Generate background image
        logger.info("🎨 Step 3/8: Generating dark cinematic image...")
        image_path = generate_image(quote, str(TEMP_DIR))
        logger.info(f"   🖼️  Image saved: {image_path}")
        
        # Step 4: Create SILENT reel (no music — Instagram will add it)
        logger.info("🎬 Step 4/8: Creating silent reel (IG will add music)...")
        
        # Generate a minimal silent audio track for the video container
        # Instagram needs a valid audio stream even if it's quiet
        silent_music_path = _generate_minimal_audio(str(TEMP_DIR))
        
        video_path = create_reel(
            image_path=image_path,
            music_path=silent_music_path,
            quote=quote,
            temp_dir=str(TEMP_DIR),
            font_paths=font_paths
        )
        logger.info(f"   📹 Silent video saved: {video_path}")
        
        # Step 5: Generate caption
        logger.info("📝 Step 5/8: Generating caption & hashtags...")
        caption = generate_caption(quote)
        logger.info(f"   📋 Caption: {caption[:80]}...")
        
        # Step 6: Smart scheduling
        logger.info("⏰ Step 6/8: Smart scheduling — finding the best time to post...")
        
        if SMART_SCHEDULING:
            logger.info("   📊 Analyzing past reel performance...")
            best_hour = calculate_best_time()
            logger.info(f"   🏆 Best time today: {best_hour:02d}:00 IST")
            wait_until_best_time(best_hour)
        else:
            logger.info("   📋 Smart scheduling disabled — posting now")
        
        # Step 7: Login and search Instagram music
        logger.info("🎵 Step 7/8: Searching Instagram's native music catalog...")
        
        from insta_music import search_and_select_track, upload_reel_with_instagram_music
        
        cl = login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        logger.info("   ✅ Logged into Instagram")
        
        track_info = search_and_select_track(cl)
        
        if track_info:
            track_name = track_info.get("name", "Unknown")
            track_artist = track_info.get("artist", "")
            logger.info(f"   🎶 Selected: \"{track_name}\" by {track_artist}")
        else:
            logger.warning("   ⚠️ Could not find Instagram music — posting without music")
        
        # Step 8: Upload reel with Instagram native music
        logger.info("📱 Step 8/8: Uploading reel with Instagram native music...")
        
        if track_info:
            result = upload_reel_with_instagram_music(
                cl=cl,
                video_path=video_path,
                caption=caption,
                track_info=track_info,
            )
            music_detail = f"IG: {track_info.get('name', '?')} - {track_info.get('artist', '?')}"
        else:
            # Fallback: upload without music
            result = _upload_without_music(cl, video_path, caption)
            music_detail = "no_music_found"
        
        logger.info(f"   ✅ Reel posted! ID: {result.get('id', 'unknown')}")
        if result.get("music_track"):
            logger.info(f"   🎵 Music: {result['music_track']} by {result.get('music_artist', '')}")
        
        # Record this post
        try:
            media_code = result.get("code", "")
            if media_code:
                record_post(
                    media_code=media_code,
                    posted_at_utc=datetime.utcnow(),
                    hour_ist=None,
                )
                logger.info("   📊 Post recorded for future scheduling optimization")
        except Exception as e:
            logger.warning(f"   ⚠️  Could not record post performance: {e}")
        
        # Record in schedule state
        record_daily_run(
            mode=mode,
            quote_text=quote.get("text", ""),
            quote_author=quote.get("author", ""),
            music_source="instagram" if track_info else "none",
            music_detail=music_detail,
            post_result=result,
        )
        
        # Save session
        try:
            from instagram import SESSION_FILE
            os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
            cl.dump_settings(SESSION_FILE)
        except Exception:
            pass
        
        # Done!
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"🎉 Insta Day pipeline complete! Total time: {elapsed:.1f}s")
        
    except Exception as e:
        logger.error(f"❌ Insta Day pipeline failed: {str(e)}")
        record_daily_run(mode=mode, error=str(e))
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


# ─── Rest Day Pipeline (Weekly Summary) ─────────────────────────────────────

def run_rest_day_pipeline(today_info):
    """
    Run the pipeline for Rest Day (Sunday).
    
    No reel is created or posted. Only generates a weekly summary.
    """
    logger.info(f"📊 Rest Day — {today_info['day_name']}, {today_info['date_ist']}")
    logger.info("   ☕ No reel today — generating weekly summary instead")
    
    try:
        summary_path = generate_weekly_summary()
        
        if summary_path:
            logger.info(f"   ✅ Weekly summary saved: {summary_path}")
        else:
            logger.warning("   ⚠️ Could not generate weekly summary")
        
        record_daily_run(mode="rest")
        logger.info("😴 Rest day complete. See you tomorrow!")
        
    except Exception as e:
        logger.error(f"❌ Rest day pipeline failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _generate_minimal_audio(temp_dir):
    """
    Generate a truly silent audio file for Insta Day reels.
    
    Instagram needs a valid audio stream in the video, but we want
    it to be completely silent so that the Instagram native music
    can play at full volume without any interference.
    
    Uses digital silence (anullsrc) in AAC format for best compatibility.
    NOTE: With clip_upload_as_reel_with_music (Method 1), the audio
    gets replaced by the downloaded music track anyway. This silent
    audio is just a placeholder for the video container.
    """
    import subprocess
    
    output_path = os.path.join(temp_dir, "silent_audio.m4a")
    
    # Method 1: True digital silence in AAC format
    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "16",
            "-c:a", "aac", "-b:a", "128k",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        if result.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size > 0:
                print(f"   🔇 True silent audio created ({file_size / 1024:.0f} KB)")
                return output_path
    except Exception as e:
        print(f"   ⚠️ Silent audio method 1 failed: {e}")
    
    # Method 2: MP3 format as fallback
    output_path_mp3 = os.path.join(temp_dir, "silent_audio.mp3")
    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", "16",
            "-c:a", "libmp3lame", "-b:a", "128k",
            output_path_mp3
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        if result.returncode == 0 and os.path.exists(output_path_mp3):
            print(f"   🔇 Silent audio (MP3) created")
            return output_path_mp3
    except Exception:
        pass
    
    return None


def _upload_without_music(cl, video_path, caption):
    """Upload reel without Instagram native music (fallback)."""
    from instagram import upload_reel
    return upload_reel(cl, video_path, caption)


# ─── Main Entry Point ────────────────────────────────────────────────────────

def main():
    """Run the Inner Logic daily pipeline based on the weekly schedule."""
    today_info = get_today_info()
    
    logger.info("🚀 Inner Logic — Starting daily pipeline")
    logger.info(f"📅 {today_info['day_name']}, {today_info['date_ist']}")
    logger.info(f"{today_info['emoji']} Mode: {today_info['label']}")
    
    try:
        if is_rest_day():
            # Sunday — rest day, weekly summary only
            run_rest_day_pipeline(today_info)
        elif should_use_ai_music():
            # Mon/Wed/Fri — AI Day (FFmpeg music)
            validate_env()
            setup_temp_dir()
            run_ai_day_pipeline(today_info)
        elif should_use_instagram_music():
            # Tue/Thu/Sat — Insta Day (IG native music)
            validate_env()
            setup_temp_dir()
            run_insta_day_pipeline(today_info)
        else:
            # Should never happen, but handle it
            logger.error(f"❌ Unknown day mode: {today_info['mode']}")
            sys.exit(1)
    
    finally:
        if should_post_today():
            cleanup()


if __name__ == "__main__":
    main()
