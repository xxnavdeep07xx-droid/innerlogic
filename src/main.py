#!/usr/bin/env python3
"""
Inner Logic — Instagram Reel Automation
========================================
Main orchestrator that ties together all pipeline steps:
1. Pick a philosophical quote
2. Generate a dark cinematic background image
3. Download royalty-free music
4. Create a 15-second reel with FFmpeg
5. Upload video to temporary hosting
6. Post reel to Instagram via Graph API
7. Clean up temporary files
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

from reddit_scraper import pick_quote_from_reddit
from quote_picker import pick_quote
from image_generator import generate_image
from music_fetcher import fetch_music
from video_creator import create_reel
from caption_generator import generate_caption
from uploader import upload_video
from instagram import post_reel
from token_refresh import refresh_access_token

# ─── Configuration ───────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
TEMP_DIR = PROJECT_ROOT / "temp"
DATA_DIR = PROJECT_ROOT / "data"
FONTS_DIR = PROJECT_ROOT / "fonts"
QUOTES_FILE = DATA_DIR / "quotes.json"
USED_QUOTES_FILE = DATA_DIR / "used_quotes.json"
USED_REDDIT_FILE = DATA_DIR / "used_reddit_quotes.json"

# Instagram credentials from environment variables
ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
IG_BUSINESS_ACCOUNT_ID = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
FB_APP_ID = os.environ.get("FACEBOOK_APP_ID", "")
FB_APP_SECRET = os.environ.get("FACEBOOK_APP_SECRET", "")

# Pixabay API key (optional, for music)
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")

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
    if not ACCESS_TOKEN:
        missing.append("INSTAGRAM_ACCESS_TOKEN")
    if not IG_BUSINESS_ACCOUNT_ID:
        missing.append("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    if not FB_APP_ID:
        missing.append("FACEBOOK_APP_ID")
    if not FB_APP_SECRET:
        missing.append("FACEBOOK_APP_SECRET")
    
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
        
        # Step 1: Refresh access token
        logger.info("🔄 Step 1/7: Refreshing access token...")
        current_token = refresh_access_token(
            ACCESS_TOKEN, FB_APP_ID, FB_APP_SECRET
        )
        os.environ["INSTAGRAM_ACCESS_TOKEN"] = current_token
        
        # Step 2: Scrape a unique quote from Reddit
        logger.info("💡 Step 2/7: Scraping a unique quote from Reddit...")
        quote = pick_quote_from_reddit(str(USED_REDDIT_FILE))
        logger.info(f"   📝 \"{quote['text'][:60]}...\" — {quote['author']}")
        logger.info(f"   🔗 Source: {quote.get('source', 'unknown')}")
        
        # Step 3: Generate background image
        logger.info("🎨 Step 3/7: Generating dark cinematic image...")
        image_path = generate_image(quote, str(TEMP_DIR))
        logger.info(f"   🖼️  Image saved: {image_path}")
        
        # Step 4: Fetch music
        logger.info("🎵 Step 4/7: Downloading royalty-free music...")
        music_path = fetch_music(PIXABAY_API_KEY, str(TEMP_DIR))
        logger.info(f"   🎶 Music saved: {music_path}")
        
        # Step 5: Create video reel
        logger.info("🎬 Step 5/7: Creating 15-second reel...")
        video_path = create_reel(
            image_path=image_path,
            music_path=music_path,
            quote=quote,
            temp_dir=str(TEMP_DIR),
            fonts_dir=str(FONTS_DIR)
        )
        logger.info(f"   📹 Video saved: {video_path}")
        
        # Step 6: Upload video
        logger.info("☁️  Step 6/7: Uploading video to temporary hosting...")
        video_url = upload_video(video_path)
        logger.info(f"   🔗 Video URL: {video_url}")
        
        # Step 7: Post to Instagram
        logger.info("📱 Step 7/7: Posting reel to Instagram...")
        caption = generate_caption(quote)
        result = post_reel(
            access_token=current_token,
            ig_business_account_id=IG_BUSINESS_ACCOUNT_ID,
            video_url=video_url,
            caption=caption
        )
        logger.info(f"   ✅ Reel posted successfully! ID: {result.get('id', 'unknown')}")
        
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
