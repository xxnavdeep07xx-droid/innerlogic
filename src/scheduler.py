#!/usr/bin/env python3
"""
Weekly Scheduler — Determines the daily mode for Inner Logic pipeline.

Weekly Schedule (simplified — Instagram native audio only, every day):
    Monday    = Insta Day  (Instagram's native trending music)
    Tuesday   = Insta Day  (Instagram's native trending music)
    Wednesday = Insta Day  (Instagram's native trending music)
    Thursday  = Insta Day  (Instagram's native trending music)
    Friday    = Insta Day  (Instagram's native trending music)
    Saturday  = Insta Day  (Instagram's native trending music)
    Sunday    = Rest Day   (No posting — weekly summary only)

All times are in IST (UTC+5:30).

Why no more "AI Days" (FFmpeg-synthesized music)?
  - Instagram's algorithm strongly favors reels that use trending native
    audio. Reels with original/synthesized audio get ~3-5x less reach.
  - The user explicitly requested full dependence on Instagram's song catalog.
  - Removing the FFmpeg music path also simplifies the pipeline and removes
    a class of failures (no more silent-audio fallback edge cases).
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path


# ─── Configuration ────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"
SCHEDULE_FILE = DATA_DIR / "schedule_state.json"

IST_OFFSET = timedelta(hours=5, minutes=30)

# Day modes: 0=Monday ... 6=Sunday
# Mon-Sat = insta (Instagram native trending music)
# Sun     = rest (weekly summary only)
DAY_MODES = {
    0: "insta",   # Monday
    1: "insta",   # Tuesday
    2: "insta",   # Wednesday
    3: "insta",   # Thursday
    4: "insta",   # Friday
    5: "insta",   # Saturday
    6: "rest",    # Sunday
}

DAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

MODE_EMOJI = {
    "insta": "🎵",
    "rest": "📊",
}

MODE_LABELS = {
    "insta": "Insta Day — Instagram Native Music",
    "rest": "Rest Day — Weekly Summary Only",
}


# ─── IST Helpers ──────────────────────────────────────────────────────────────

def get_ist_now():
    """Get current IST datetime."""
    return datetime.utcnow() + IST_OFFSET


def get_today_mode():
    """
    Get today's mode based on the day of the week (IST).
    
    Returns:
        str: "ai", "insta", or "rest"
    """
    ist_now = get_ist_now()
    weekday = ist_now.weekday()  # 0=Monday ... 6=Sunday
    return DAY_MODES[weekday]


def get_today_info():
    """
    Get full info about today's schedule.
    
    Returns:
        dict with keys: mode, day_name, emoji, label, date_ist
    """
    ist_now = get_ist_now()
    weekday = ist_now.weekday()
    mode = DAY_MODES[weekday]
    
    return {
        "mode": mode,
        "day_name": DAY_NAMES[weekday],
        "emoji": MODE_EMOJI[mode],
        "label": MODE_LABELS[mode],
        "date_ist": ist_now.strftime("%Y-%m-%d"),
        "weekday": weekday,
    }


def is_rest_day():
    """Check if today is a rest day (Sunday)."""
    return get_today_mode() == "rest"


def should_post_today():
    """Check if we should create and post a reel today."""
    return get_today_mode() != "rest"


def should_use_instagram_music():
    """Check if today uses Instagram's native music catalog."""
    return get_today_mode() == "insta"




def get_week_summary_dates():
    """
    Get the date range for the current week (Monday to Saturday).
    Sunday generates the summary for the previous Mon-Sat.
    
    Returns:
        tuple: (start_date, end_date) as YYYY-MM-DD strings
    """
    ist_now = get_ist_now()
    # If it's Sunday, summarize the past week (Mon-Sat just ended)
    if ist_now.weekday() == 6:
        # Last Monday was 6 days ago
        last_monday = ist_now - timedelta(days=6)
        last_saturday = ist_now - timedelta(days=1)
        return (
            last_monday.strftime("%Y-%m-%d"),
            last_saturday.strftime("%Y-%m-%d"),
        )
    else:
        # Current week (Mon up to today)
        days_since_monday = ist_now.weekday()
        monday = ist_now - timedelta(days=days_since_monday)
        return (
            monday.strftime("%Y-%m-%d"),
            ist_now.strftime("%Y-%m-%d"),
        )


# ─── Schedule State Tracking ─────────────────────────────────────────────────

def _load_schedule_state():
    """Load schedule state from file."""
    try:
        if SCHEDULE_FILE.exists():
            with open(SCHEDULE_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "daily_log": [],  # List of daily entries
        "week_posts": {},  # week_start_date -> list of posts
    }


def _save_schedule_state(state):
    """Save schedule state to file."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def record_daily_run(mode, quote_text=None, quote_author=None, 
                     music_source=None, music_detail=None,
                     video_path=None, post_result=None, error=None):
    """
    Record today's pipeline run in the schedule state.
    
    Args:
        mode: Today's mode ("ai", "insta", "rest")
        quote_text: The quote used (if posted)
        quote_author: Quote author
        music_source: Music source ("ffmpeg" or "instagram")
        music_detail: Details about the music (style name or track name)
        video_path: Path to generated video
        post_result: Result dict from posting (id, code, status)
        error: Error message if pipeline failed
    """
    state = _load_schedule_state()
    
    ist_now = get_ist_now()
    today = ist_now.strftime("%Y-%m-%d")
    
    entry = {
        "date": today,
        "day_name": DAY_NAMES[ist_now.weekday()],
        "mode": mode,
        "timestamp": ist_now.isoformat(),
    }
    
    if quote_text:
        entry["quote"] = f"{quote_text} — {quote_author}" if quote_author else quote_text
    if music_source:
        entry["music_source"] = music_source
    if music_detail:
        entry["music_detail"] = music_detail
    if post_result:
        entry["post_id"] = post_result.get("id", "")
        entry["post_code"] = post_result.get("code", "")
        entry["status"] = post_result.get("status", "")
    if error:
        entry["error"] = error
    
    # Add to daily log (keep last 30 days)
    state["daily_log"].append(entry)
    state["daily_log"] = state["daily_log"][-30:]
    
    # Also organize by week
    days_since_monday = ist_now.weekday()
    week_monday = ist_now - timedelta(days=days_since_monday)
    week_key = week_monday.strftime("%Y-%m-%d")
    
    if week_key not in state["week_posts"]:
        state["week_posts"][week_key] = []
    state["week_posts"][week_key].append(entry)
    
    # Keep only last 8 weeks
    week_keys = sorted(state["week_posts"].keys())
    if len(week_keys) > 8:
        for old_key in week_keys[:-8]:
            del state["week_posts"][old_key]
    
    _save_schedule_state(state)


def get_week_posts(week_start_date=None):
    """
    Get all posts for a given week.
    
    Args:
        week_start_date: Monday date as "YYYY-MM-DD" (defaults to current week)
    
    Returns:
        list: Daily entries for the week
    """
    state = _load_schedule_state()
    
    if week_start_date is None:
        ist_now = get_ist_now()
        days_since_monday = ist_now.weekday()
        week_monday = ist_now - timedelta(days=days_since_monday)
        week_start_date = week_monday.strftime("%Y-%m-%d")
    
    return state.get("week_posts", {}).get(week_start_date, [])


if __name__ == "__main__":
    info = get_today_info()
    print(f"📅 Today: {info['day_name']}, {info['date_ist']}")
    print(f"{info['emoji']} Mode: {info['label']}")
    print(f"   Should post: {should_post_today()}")
    print(f"   Use IG music: {should_use_instagram_music()}")
    print(f"   Week summary: {get_week_summary_dates()}")
