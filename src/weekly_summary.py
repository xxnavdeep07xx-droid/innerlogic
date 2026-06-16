#!/usr/bin/env python3
"""
Weekly Summary Generator — Creates a .md report every Sunday.

The summary covers:
  - Posts made this week (Mon-Sat)
  - Music sources used (AI vs Insta)
  - Performance metrics (if available)
  - Insights & improvements for next week

Saves to: data/weekly_summaries/YYYY-WNN.md
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path


# ─── Configuration ────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"
SUMMARIES_DIR = DATA_DIR / "weekly_summaries"
PERFORMANCE_FILE = DATA_DIR / "post_performance.json"
SCHEDULE_FILE = DATA_DIR / "schedule_state.json"
MUSIC_HISTORY_FILE = DATA_DIR / "music_history.json"

IST_OFFSET = timedelta(hours=5, minutes=30)


def _get_ist_now():
    return datetime.utcnow() + IST_OFFSET


def _load_json(path):
    """Load a JSON file safely."""
    try:
        if Path(path).exists():
            with open(path, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _get_week_number(date_str):
    """Get ISO week number from a date string."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.isocalendar()[1]
    except Exception:
        return 0


def _count_by_mode(week_posts):
    """Count posts by mode (ai vs insta)."""
    ai_count = sum(1 for p in week_posts if p.get("mode") == "ai")
    insta_count = sum(1 for p in week_posts if p.get("mode") == "insta")
    error_count = sum(1 for p in week_posts if p.get("error"))
    return ai_count, insta_count, error_count


def _get_performance_for_week(week_posts, performance_data):
    """Get performance metrics for this week's posts."""
    posts_data = performance_data.get("posts", [])
    week_codes = {p.get("post_code") for p in week_posts if p.get("post_code")}
    
    total_plays = 0
    total_likes = 0
    matched = 0
    
    for post in posts_data:
        if post.get("code") in week_codes:
            total_plays += post.get("plays", 0) or 0
            total_likes += post.get("likes", 0) or 0
            matched += 1
    
    return {
        "total_plays": total_plays,
        "total_likes": total_likes,
        "posts_tracked": matched,
    }


def _get_music_summary(week_posts, music_history):
    """Summarize music sources used this week."""
    ai_styles = []
    insta_tracks = []
    
    for post in week_posts:
        source = post.get("music_source", "unknown")
        detail = post.get("music_detail", "unknown")
        if source == "ffmpeg":
            ai_styles.append(detail)
        elif source == "instagram":
            insta_tracks.append(detail)
    
    # Also check music history
    recent_styles = music_history.get("recent_styles", [])
    recent_insta_ids = music_history.get("recent_insta_track_ids", [])
    
    return {
        "ai_styles_used": ai_styles,
        "insta_tracks_used": insta_tracks,
        "total_ai": len(ai_styles),
        "total_insta": len(insta_tracks),
        "all_recent_ai_styles": recent_styles,
        "all_recent_insta_ids": recent_insta_ids,
    }


def _generate_improvements(week_posts, perf, music):
    """Generate improvement suggestions based on week's data."""
    improvements = []
    
    # Performance-based improvements
    if perf["posts_tracked"] > 0:
        avg_plays = perf["total_plays"] / perf["posts_tracked"]
        avg_likes = perf["total_likes"] / perf["posts_tracked"]
        
        if avg_likes < 3:
            improvements.append(
                "- **Captions**: Consider more engaging call-to-actions in captions — "
                "average likes are low this week"
            )
        if avg_plays < 50:
            improvements.append(
                "- **Posting time**: Low average views — experiment with different "
                "posting hours next week"
            )
    
    # Music diversity
    ai_styles = music.get("ai_styles_used", [])
    unique_ai = len(set(ai_styles))
    if unique_ai < len(ai_styles) * 0.7:
        improvements.append(
            "- **AI Music**: Some FFmpeg styles repeated — increase variety "
            "by adding more style parameters"
        )
    
    # Error tracking
    errors = [p for p in week_posts if p.get("error")]
    if errors:
        improvements.append(
            f"- **Reliability**: {len(errors)} day(s) had errors — review error logs "
            f"and fix before next week"
        )
    
    # Balance check
    ai_count, insta_count, _ = _count_by_mode(week_posts)
    if ai_count > insta_count + 1:
        improvements.append(
            "- **Balance**: More AI days than Insta days this week — "
            "ensure Instagram music integration is working properly"
        )
    elif insta_count > ai_count + 1:
        improvements.append(
            "- **Balance**: More Insta days than AI days — check if "
            "FFmpeg generation is failing"
        )
    
    if not improvements:
        improvements.append(
            "- **Status**: Everything looks balanced this week — keep it up! 🎯"
        )
    
    return improvements


def generate_weekly_summary():
    """
    Generate the weekly summary markdown file.
    Called on Sundays (rest day).
    
    Returns:
        str: Path to the generated .md file, or None on failure
    """
    ist_now = _get_ist_now()
    
    # Calculate last week's Monday-Saturday
    days_since_monday = ist_now.weekday()
    # On Sunday, weekday=6, so last Monday was 6 days ago
    if days_since_monday == 6:
        last_monday = ist_now - timedelta(days=6)
        last_saturday = ist_now - timedelta(days=1)
    else:
        # Shouldn't normally be called on non-Sunday, but handle it
        last_monday = ist_now - timedelta(days=days_since_monday)
        last_saturday = ist_now
    
    week_key = last_monday.strftime("%Y-%m-%d")
    week_num = last_monday.isocalendar()[1]
    year = last_monday.year
    
    # Load data
    schedule_state = _load_json(SCHEDULE_FILE)
    performance_data = _load_json(PERFORMANCE_FILE)
    music_history = _load_json(MUSIC_HISTORY_FILE)
    
    # Get this week's posts
    week_posts = schedule_state.get("week_posts", {}).get(week_key, [])
    
    # Calculate metrics
    ai_count, insta_count, error_count = _count_by_mode(week_posts)
    perf = _get_performance_for_week(week_posts, performance_data)
    music = _get_music_summary(week_posts, music_history)
    improvements = _generate_improvements(week_posts, perf, music)
    
    total_posts = ai_count + insta_count
    
    # ─── Build Markdown ──────────────────────────────────────────────────
    
    md_lines = [
        f"# Inner Logic — Weekly Summary",
        f"",
        f"**Week {week_num}** ({last_monday.strftime('%b %d')} – {last_saturday.strftime('%b %d, %Y')})",
        f"",
        f"---",
        f"",
        f"## Overview",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Posts | {total_posts} |",
        f"| AI Music Days | {ai_count} |",
        f"| Insta Music Days | {insta_count} |",
        f"| Errors | {error_count} |",
        f"| Total Plays | {perf['total_plays']} |",
        f"| Total Likes | {perf['total_likes']} |",
        f"| Avg Plays/Post | {perf['total_plays'] / max(perf['posts_tracked'], 1):.0f} |",
        f"| Avg Likes/Post | {perf['total_likes'] / max(perf['posts_tracked'], 1):.1f} |",
        f"",
        f"---",
        f"",
        f"## Daily Breakdown",
        f"",
        f"| Day | Mode | Quote | Music | Status |",
        f"|-----|------|-------|-------|--------|",
    ]
    
    # Day-by-day rows
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    for day_name in day_order:
        day_entries = [p for p in week_posts if p.get("day_name") == day_name]
        if day_entries:
            entry = day_entries[-1]  # Take last entry for that day
            mode_icon = "🤖 AI" if entry.get("mode") == "ai" else "🎵 Insta"
            quote = entry.get("quote", "—")
            if len(quote) > 50:
                quote = quote[:47] + "..."
            music_detail = entry.get("music_detail", "—")
            if len(music_detail) > 30:
                music_detail = music_detail[:27] + "..."
            status = "❌ Error" if entry.get("error") else "✅ Posted"
            md_lines.append(
                f"| {day_name} | {mode_icon} | {quote} | {music_detail} | {status} |"
            )
        else:
            md_lines.append(f"| {day_name} | — | No post | — | — |")
    
    md_lines.extend([
        f"",
        f"---",
        f"",
        f"## Music Report",
        f"",
        f"### AI-Generated Tracks (FFmpeg)",
        f"",
    ])
    
    if music["ai_styles_used"]:
        md_lines.append(f"Styles used this week:")
        for style in music["ai_styles_used"]:
            md_lines.append(f"- `{style}`")
    else:
        md_lines.append(f"No AI music used this week.")
    
    md_lines.extend([
        f"",
        f"### Instagram Native Tracks",
        f"",
    ])
    
    if music["insta_tracks_used"]:
        md_lines.append(f"Tracks used this week:")
        for track in music["insta_tracks_used"]:
            md_lines.append(f"- {track}")
    else:
        md_lines.append(f"No Instagram music used this week.")
    
    md_lines.extend([
        f"",
        f"---",
        f"",
        f"## Performance Insights",
        f"",
    ])
    
    if perf["posts_tracked"] > 0:
        best_plays = 0
        best_day = "—"
        for post in week_posts:
            if post.get("post_code"):
                for perf_post in performance_data.get("posts", []):
                    if perf_post.get("code") == post.get("post_code"):
                        p = perf_post.get("plays", 0) or 0
                        if p > best_plays:
                            best_plays = p
                            best_day = post.get("day_name", "—")
        
        md_lines.extend([
            f"- **Best performing day**: {best_day} ({best_plays} plays)",
            f"- **Total engagement**: {perf['total_plays']} plays, {perf['total_likes']} likes",
            f"- **Engagement rate**: {perf['total_likes'] / max(perf['total_plays'], 1) * 100:.1f}% likes-to-plays",
            f"",
        ])
    else:
        md_lines.extend([
            f"- No performance data available for this week yet.",
            f"  Metrics will populate as Instagram updates view counts.",
            f"",
        ])
    
    md_lines.extend([
        f"---",
        f"",
        f"## Improvements for Next Week",
        f"",
    ])
    
    for improvement in improvements:
        md_lines.append(improvement)
    
    md_lines.extend([
        f"",
        f"---",
        f"",
        f"*Generated on {ist_now.strftime('%Y-%m-%d %H:%M')} IST by Inner Logic Bot*",
    ])
    
    # ─── Save to File ────────────────────────────────────────────────────
    
    try:
        SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{year}-W{week_num:02d}.md"
        filepath = SUMMARIES_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
        
        print(f"   ✅ Weekly summary saved: {filepath}")
        return str(filepath)
        
    except Exception as e:
        print(f"   ❌ Could not save weekly summary: {e}")
        return None


if __name__ == "__main__":
    path = generate_weekly_summary()
    if path:
        print(f"\nSummary saved to: {path}")
    else:
        print("\nFailed to generate summary")
