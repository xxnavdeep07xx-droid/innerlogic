#!/usr/bin/env python3
"""
Inner Logic — Instagram Reel Automation
========================================
Main orchestrator that ties together all pipeline steps:
1. Scrape a unique philosophical quote from the web
2. Download fonts (Cormorant Garamond + Montserrat from Google Fonts)
3. Generate a dark cinematic background image
4. Download royalty-free music
5. Create a 15-second reel with FFmpeg
6. Wait for the best posting time (smart scheduler)
7. Post reel to Instagram via instagrapi (no API tokens needed!)
8. Record performance for future scheduling optimization
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
from music_fetcher import fetch_music
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

# API keys (optional)
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

# Smart scheduling: Set to "true" to auto-find the best posting time
SMART_SCHEDULING = os.environ.get("SMART_SCHEDULING", "true").lower() == "true"

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("innerlogic")


# ─── Main Pipeline ──────────────────────────────────────────────────────────

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


def main():
    """Run the full Instagram reel automation pipeline."""
    start_time = datetime.now()
    logger.info("🚀 Inner Logic — Starting daily reel pipeline")
    logger.info(f"📅 Date: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 0: Validate environment
        validate_env()
        setup_temp_dir()
        
        # Step 1: Scrape a unique quote from the web
        logger.info("💡 Step 1/8: Scraping a unique philosophical quote...")
        quote = pick_quote_from_web(str(USED_QUOTES_FILE))
        logger.info(f"   📝 \"{quote['text'][:60]}...\" — {quote['author']}")
        logger.info(f"   🔗 Source: {quote.get('source', 'unknown')}")
        
        # Step 2: Download fonts (if not cached)
        logger.info("🔤 Step 2/8: Ensuring fonts are available...")
        font_paths = ensure_fonts(str(FONTS_DIR))
        logger.info("   ✅ Fonts ready")
        
        # Step 3: Generate background image
        logger.info("🎨 Step 3/8: Generating dark cinematic image...")
        image_path = generate_image(quote, str(TEMP_DIR))
        logger.info(f"   🖼️  Image saved: {image_path}")
        
        # Step 4: Fetch music
        logger.info("🎵 Step 4/8: Downloading royalty-free music...")
        music_path = fetch_music("", str(TEMP_DIR))
        logger.info(f"   🎶 Music saved: {music_path}")
        
        # Step 5: Create video reel
        logger.info("🎬 Step 5/8: Creating 15-second reel...")
        video_path = create_reel(
            image_path=image_path,
            music_path=music_path,
            quote=quote,
            temp_dir=str(TEMP_DIR),
            font_paths=font_paths
        )
        logger.info(f"   📹 Video saved: {video_path}")
        
        # Step 6: Generate caption
        logger.info("📝 Step 6/8: Generating caption & hashtags...")
        caption = generate_caption(quote)
        logger.info(f"   📋 Caption: {caption[:80]}...")
        
        # Step 7: Smart scheduling — calculate and wait for the best time
        logger.info("⏰ Step 7/8: Smart scheduling — finding the best time to post...")
        
        if SMART_SCHEDULING:
            # Login early to fetch performance data for scheduling
            logger.info("   📊 Analyzing past reel performance...")
            best_hour = calculate_best_time()
            logger.info(f"   🏆 Best time today: {best_hour:02d}:00 IST")
            
            # Wait until the best posting time
            wait_until_best_time(best_hour)
        else:
            logger.info("   📋 Smart scheduling disabled — posting now")
        
        # Step 8: Post reel to Instagram
        logger.info("📱 Step 8/8: Posting reel to Instagram...")
        result = post_reel(
            video_path=video_path,
            caption=caption
        )
        logger.info(f"   ✅ Reel posted successfully! ID: {result.get('id', 'unknown')}")
        
        # Record this post for future scheduling optimization
        try:
            media_code = result.get("code", "")
            if media_code:
                record_post(
                    media_code=media_code,
                    posted_at_utc=datetime.utcnow(),
                    hour_ist=None,  # Auto-calculated from posted_at_utc
                )
                logger.info("   📊 Post recorded for future scheduling optimization")
        except Exception as e:
            logger.warning(f"   ⚠️  Could not record post performance: {e}")
        
        # Done!
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"🎉 Pipeline complete! Total time: {elapsed:.1f}s")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    finally:
        cleanup()


if __name__ == "__main__":
    main()
