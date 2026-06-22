#!/usr/bin/env python3
"""
Refresh Metrics — fetch view/like/comment counts for posts made in the
last 48 hours, so the smart scheduler has real engagement data to learn from.

Runs as a separate GitHub Actions cron job (once daily, in the morning),
separate from the reel-posting workflow.

Why this matters: without actual view/like/comment numbers, the smart
scheduler can't optimize posting time. This module closes that loop.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("innerlogic")

# Reuse paths from sibling modules
from instagram import login, SESSION_FILE
from smart_scheduler import PERFORMANCE_FILE, load_performance_data, save_performance_data


def _is_within_48h(posted_at_str):
    """Check if a post was made within the last 48 hours."""
    try:
        posted_at = datetime.fromisoformat(posted_at_str.replace("Z", "+00:00"))
    except Exception:
        return False
    return (datetime.now(posted_at.tzinfo) - posted_at) < timedelta(hours=48)


def refresh_metrics():
    """Fetch updated metrics for all posts made in the last 48h."""
    username = os.environ.get("INSTAGRAM_USERNAME", "")
    password = os.environ.get("INSTAGRAM_PASSWORD", "")
    if not username or not password:
        logger.error("❌ INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD env vars required")
        sys.exit(1)

    data = load_performance_data()
    posts = data.get("posts", [])
    if not posts:
        logger.info("ℹ️  No posts in performance data — nothing to refresh")
        return

    # Find posts needing refresh: made within 48h AND missing view counts
    # (or any post less than 7 days old — keep refreshing for a week)
    needs_refresh = []
    for p in posts:
        posted_at = p.get("posted_at", "")
        if not posted_at:
            continue
        try:
            dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
            age_hours = (datetime.now(dt.tzinfo) - dt).total_seconds() / 3600
        except Exception:
            continue
        if age_hours < 24 * 7:  # refresh posts up to 7 days old
            needs_refresh.append(p)

    if not needs_refresh:
        logger.info("ℹ️  No posts need metric refresh (all are >7 days old)")
        return

    logger.info(f"📊 Refreshing metrics for {len(needs_refresh)} recent posts...")

    try:
        cl = login(username, password)
    except Exception as e:
        logger.error(f"❌ Login failed: {str(e)[:120]}")
        sys.exit(1)

    refreshed_count = 0
    for post in needs_refresh:
        media_code = post.get("code") or post.get("media_code")
        if not media_code:
            logger.warning("   ⚠️  Post has no 'code' — skipping")
            continue

        # Convert short code → media PK → full media ID
        try:
            media_pk = cl.media_pk_from_code(media_code)
            media_id = cl.media_id(media_pk) if hasattr(cl, 'media_id') else media_pk
        except Exception as e:
            logger.warning(f"   ⚠️  Could not resolve code {media_code}: {str(e)[:80]}")
            continue

        try:
            info = cl.media_info(media_id)
            if not info:
                continue

            # Update the post record with fresh metrics.
            # instagrapi's MediaInfo has: view_count, like_count, comment_count, play_count, taken_at
            post["plays"] = getattr(info, "view_count", None) or getattr(info, "play_count", None) or 0
            post["likes"] = getattr(info, "like_count", None) or 0
            post["comments"] = getattr(info, "comment_count", None) or 0
            post["updated_at"] = datetime.utcnow().isoformat()

            logger.info(
                f"   ✅ {media_code}: plays={post['plays']} "
                f"likes={post['likes']} comments={post['comments']}"
            )
            refreshed_count += 1

            # Be polite to Instagram — small delay between lookups
            import time; time.sleep(2.0)

        except Exception as e:
            logger.warning(f"   ⚠️  Could not fetch info for {media_code}: {str(e)[:80]}")

    # Save the updated data back to disk
    save_performance_data(data)
    logger.info(f"💾 Refreshed {refreshed_count}/{len(needs_refresh)} posts → {PERFORMANCE_FILE}")


if __name__ == "__main__":
    refresh_metrics()
