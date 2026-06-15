#!/usr/bin/env python3
"""
Smart Scheduler — Calculates the best time to post on Instagram
based on historical performance data.

Strategy:
1. Fetch past reel performance (plays, likes) from Instagram
2. Analyze performance by hour of day (IST)
3. Calculate the optimal posting time
4. Track and learn from each post's performance over time
5. Weight recent posts more heavily than older ones
"""

import os
import json
import time
import random
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path


# ─── Configuration ────────────────────────────────────────────────────────────

# Minimum hours between when the pipeline triggers and when it posts
# This gives us a window to delay the post
MIN_POST_HOUR_IST = 6    # Don't post before 6 AM IST
MAX_POST_HOUR_IST = 23   # Don't post after 11 PM IST

# Weight decay for older posts (0.0-1.0) — how much less weight to give older data
RECENCY_DECAY = 0.85     # Each older day gets 85% of the previous day's weight

# Data file for tracking post performance over time
PERFORMANCE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "post_performance.json"
)
PERFORMANCE_FILE = os.path.abspath(PERFORMANCE_FILE)

# Indian timezone offset
IST_OFFSET_HOURS = 5
IST_OFFSET_MINUTES = 30


def _utc_to_ist_hour(dt):
    """Convert a UTC datetime to IST hour (0-23)."""
    ist_dt = dt + timedelta(hours=IST_OFFSET_HOURS, minutes=IST_OFFSET_MINUTES)
    return ist_dt.hour


def _get_current_ist_hour():
    """Get current hour in IST."""
    return _utc_to_ist_hour(datetime.utcnow())


def _get_current_ist_time():
    """Get current IST datetime."""
    return datetime.utcnow() + timedelta(hours=IST_OFFSET_HOURS, minutes=IST_OFFSET_MINUTES)


def load_performance_data():
    """Load historical post performance data."""
    if not os.path.exists(PERFORMANCE_FILE):
        return {"posts": [], "best_hours_cache": {}}

    try:
        with open(PERFORMANCE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return {"posts": [], "best_hours_cache": {}}


def save_performance_data(data):
    """Save performance data to file."""
    os.makedirs(os.path.dirname(PERFORMANCE_FILE), exist_ok=True)
    with open(PERFORMANCE_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def record_post(media_code, posted_at_utc, plays=0, likes=0, hour_ist=None):
    """
    Record a new post's performance data.
    Called after each post to track when it was posted and how it performed.

    Args:
        media_code: Instagram media code (e.g., 'DZmWDDFMRbA')
        posted_at_utc: UTC datetime when the post was made
        plays: Number of plays/views
        likes: Number of likes
        hour_ist: IST hour when posted (auto-calculated if not provided)
    """
    data = load_performance_data()

    if hour_ist is None:
        hour_ist = _utc_to_ist_hour(posted_at_utc)

    # Check if this post is already recorded
    existing = [p for p in data["posts"] if p.get("code") == media_code]
    if existing:
        # Update existing record
        existing[0]["plays"] = plays
        existing[0]["likes"] = likes
        existing[0]["updated_at"] = datetime.utcnow().isoformat()
    else:
        # Add new record
        data["posts"].append({
            "code": media_code,
            "posted_at": posted_at_utc.isoformat() if isinstance(posted_at_utc, datetime) else posted_at_utc,
            "hour_ist": hour_ist,
            "plays": plays,
            "likes": likes,
            "recorded_at": datetime.utcnow().isoformat(),
        })

    # Keep only last 200 posts
    if len(data["posts"]) > 200:
        data["posts"] = data["posts"][-200:]

    save_performance_data(data)


def fetch_and_record_performance(cl, user_id):
    """
    Fetch past reel performance from Instagram and record it.
    This builds up our historical data for better scheduling.

    Args:
        cl: Authenticated instagrapi Client
        user_id: Instagram user ID
    """
    try:
        medias = cl.user_clips(user_id, amount=30)
        print(f"   📊 Fetched {len(medias)} past reels for performance analysis")

        data = load_performance_data()
        existing_codes = {p["code"] for p in data["posts"]}

        new_count = 0
        for media in medias:
            if media.code in existing_codes:
                # Update existing record with latest play count
                for p in data["posts"]:
                    if p["code"] == media.code:
                        p["plays"] = getattr(media, 'play_count', 0) or 0
                        p["likes"] = media.like_count or 0
                        break
            else:
                # Add new record
                hour_ist = _utc_to_ist_hour(media.taken_at)
                data["posts"].append({
                    "code": media.code,
                    "posted_at": media.taken_at.isoformat(),
                    "hour_ist": hour_ist,
                    "plays": getattr(media, 'play_count', 0) or 0,
                    "likes": media.like_count or 0,
                    "recorded_at": datetime.utcnow().isoformat(),
                })
                new_count += 1

        # Keep only last 200 posts
        if len(data["posts"]) > 200:
            data["posts"] = data["posts"][-200:]

        save_performance_data(data)
        print(f"   ✅ Recorded {new_count} new posts, updated {len(medias) - new_count} existing")

    except Exception as e:
        print(f"   ⚠️  Could not fetch past performance: {e}")


def calculate_best_hour(use_local_data=True, cl=None, user_id=None):
    """
    Calculate the best hour to post based on historical performance data.

    Uses a weighted scoring system:
    - Recent posts are weighted more heavily
    - Each hour gets a score based on avg plays/likes at that hour
    - Hours with very few data points get a small exploration bonus
    - Top 3 hours are considered, with slight randomization

    Args:
        use_local_data: Whether to use locally tracked performance data
        cl: Optional instagrapi Client for fetching live data
        user_id: Optional user ID for fetching live data

    Returns:
        int: Best hour to post in IST (0-23)
    """
    data = load_performance_data()

    # Optionally fetch fresh data from Instagram
    if cl and user_id:
        fetch_and_record_performance(cl, user_id)
        data = load_performance_data()

    posts = data.get("posts", [])

    if not posts:
        # No data yet — use Instagram best practices for Indian audience
        print("   📋 No performance data yet — using general best practices")
        # For Indian philosophical content, 9 PM IST is typically best
        return random.choice([19, 20, 21])

    # ── Calculate weighted scores per hour ────────────────────────────────
    now = datetime.utcnow()
    hourly_scores = defaultdict(list)

    for post in posts:
        hour = post.get("hour_ist")
        if hour is None:
            continue

        plays = post.get("plays", 0) or 0
        likes = post.get("likes", 0) or 0

        # Calculate recency weight
        posted_at = post.get("posted_at", "")
        try:
            post_dt = datetime.fromisoformat(posted_at)
            days_ago = max(1, (now - post_dt).days)
            recency_weight = RECENCY_DECAY ** days_ago
        except (ValueError, TypeError):
            recency_weight = 0.5

        # Combined score: plays * 1 + likes * 3 (likes are more valuable)
        score = (plays * 1 + likes * 3) * recency_weight
        hourly_scores[hour].append(score)

    # Calculate average score per hour
    hour_avg = {}
    for hour, scores in hourly_scores.items():
        hour_avg[hour] = sum(scores) / len(scores)

    # Add exploration bonus for hours with few data points
    max_avg = max(hour_avg.values()) if hour_avg else 1
    for hour in range(MIN_POST_HOUR_IST, MAX_POST_HOUR_IST + 1):
        count = len(hourly_scores.get(hour, []))
        if count < 3:
            # Small bonus to encourage trying under-explored hours
            exploration_bonus = max_avg * 0.1 * (3 - count) / 3
            hour_avg[hour] = hour_avg.get(hour, 0) + exploration_bonus

    # Filter to reasonable posting hours
    valid_hours = {h: s for h, s in hour_avg.items()
                   if MIN_POST_HOUR_IST <= h <= MAX_POST_HOUR_IST}

    if not valid_hours:
        return 21  # Fallback to 9 PM

    # Sort by score
    sorted_hours = sorted(valid_hours.items(), key=lambda x: x[1], reverse=True)

    # Pick from top 3 hours with weighted randomization
    top_hours = sorted_hours[:3]

    print(f"   📊 Top posting hours (IST):")
    for hour, score in top_hours:
        count = len(hourly_scores.get(hour, []))
        print(f"      {hour:02d}:00 — Score: {score:.1f} ({count} data points)")

    # Weight toward the best hour but allow some variance
    weights = [3, 2, 1]  # Best hour gets 3x weight
    if len(top_hours) < 3:
        weights = weights[:len(top_hours)]

    chosen = random.choices(top_hours, weights=weights, k=1)[0]
    best_hour = chosen[0]

    return best_hour


def calculate_best_time(cl=None, user_id=None):
    """
    Calculate the best time to post today.
    Returns an IST hour (0-23) when the post should be made.

    Args:
        cl: Optional instagrapi Client for fetching live data
        user_id: Optional user ID for fetching live data

    Returns:
        int: Best hour in IST (0-23)
    """
    best_hour = calculate_best_hour(cl=cl, user_id=user_id)

    # Add slight randomization (±15 minutes) to avoid looking automated
    # This doesn't change the hour, but affects the exact minute
    print(f"   🏆 Best time to post today: {best_hour:02d}:00 IST (±15 min)")

    return best_hour


def wait_until_best_time(best_hour_ist):
    """
    Wait until the calculated best posting time.
    Called by main.py after the video is ready but before posting.

    Args:
        best_hour_ist: The IST hour (0-23) to post at
    """
    now_ist = _get_current_ist_time()

    # Target time today in IST
    # Randomize minute within 0-45 to look natural (±random offset from top of hour)
    target_ist = now_ist.replace(
        hour=best_hour_ist,
        minute=random.randint(0, 45),  # Random minute 0-45 (avoids spilling into next hour)
        second=random.randint(0, 59),
        microsecond=0
    )

    # If target is in the past, post immediately
    if target_ist <= now_ist:
        print(f"   ⏰ Target time {target_ist.strftime('%H:%M')} IST has passed — posting now!")
        return

    # Calculate wait time
    wait_seconds = (target_ist - now_ist).total_seconds()

    if wait_seconds < 60:
        print(f"   ⏰ Almost time — posting in {wait_seconds:.0f}s")
        time.sleep(wait_seconds)
        return

    if wait_seconds > 3600 * 18:  # More than 18 hours
        print(f"   ⏰ Target time is {target_ist.strftime('%H:%M')} IST — too far ahead, posting now")
        return

    # Wait in chunks, printing progress
    print(f"   ⏰ Waiting until {target_ist.strftime('%H:%M')} IST ({wait_seconds/60:.0f} minutes from now)")

    while wait_seconds > 0:
        chunk = min(wait_seconds, 300)  # Check every 5 minutes
        time.sleep(chunk)
        wait_seconds -= chunk

        if wait_seconds > 0:
            mins_left = wait_seconds / 60
            if mins_left > 60:
                print(f"   ⏳ {mins_left/60:.1f} hours until post time...")
            else:
                print(f"   ⏳ {mins_left:.0f} minutes until post time...")

    print(f"   ⏰ It's time! Posting now at {target_ist.strftime('%H:%M')} IST")


if __name__ == "__main__":
    # Test the scheduler
    best = calculate_best_time()
    print(f"\nRecommended posting time: {best:02d}:00 IST")
