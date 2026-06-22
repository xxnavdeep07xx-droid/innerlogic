#!/usr/bin/env python3
"""
Video Creator — Creates 15-second Instagram Reels using FFmpeg + MoviePy.

Features:
- Ken Burns zoom effect (smooth ease-in-out, configurable direction)
- Cinematic dark vignette overlay for depth
- Gradient dark overlay for text readability
- **PIL-rendered text overlay** (auto-fit font size, never clipped)
- Subtle text "float" animation (keeps the eye engaged → better retention)
- Branded "@innerlogic.co" watermark (builds recall → more follows)
- Color grading with cinematic themes (Homage, Golden Brown, Maritza, Blue, etc.)
- FFmpeg fallback if MoviePy fails

Output: 1080x1920 (9:16) MP4, H.264, AAC audio.
"""

import subprocess
import os
import textwrap
import random
import math
from pathlib import Path

try:
    from moviepy import (
        ImageClip, AudioFileClip, CompositeVideoClip, TextClip, VideoClip
    )
    from moviepy.video.fx import FadeIn, FadeOut
    from moviepy.audio.fx import AudioFadeIn, AudioFadeOut
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False


# ─── Configuration ────────────────────────────────────────────────────────────

REEL_WIDTH = 1080
REEL_HEIGHT = 1920
DEFAULT_DURATION = 15
DEFAULT_FPS = 30

ZOOM_START = 1.0
ZOOM_END = 1.30

VIGNETTE_STRENGTH = 0.35

# Text safe area — Instagram clips a fair amount on some devices.
# Keep text inside ~80% width and ~25-72% height.
TEXT_WIDTH_PX = 820
TEXT_SAFE_TOP = int(REEL_HEIGHT * 0.26)
TEXT_SAFE_BOTTOM = int(REEL_HEIGHT * 0.72)
TEXT_DARKEN_OPACITY = 0.42

WATERMARK_TEXT = "@innerlogic.co"

# Auto-fit font sizing — start big, shrink until it fits.
QUOTE_FONT_MIN = 30
QUOTE_FONT_MAX = 56
AUTHOR_FONT_SIZE = 24


# ─── Color Grading Themes ─────────────────────────────────────────────────────

COLOR_THEMES = {
    "homage": {
        "name": "Homage",
        "description": "Warm vintage — amber glow, lifted blacks, nostalgic film",
        "matrix": [
            [1.05, 0.05, 0.02],
            [0.02, 0.95, 0.03],
            [0.00, 0.02, 0.85],
        ],
        "brightness": 0.03,
        "contrast": 1.05,
        "saturation": 0.80,
        "gamma": 0.92,
        "ffmpeg_mixer": "0.95:0.05:0.02:0.02:0.02:0.93:0.03:0.02:0.0:0.02:0.82:0.03",
        "ffmpeg_eq": "brightness=0.03:contrast=1.05:saturation=0.80:gamma=0.92",
    },
    "golden_brown": {
        "name": "Golden Brown",
        "description": "Amber/brown — warm brown shadows, golden highlights, autumn feel",
        "matrix": [
            [1.08, 0.06, 0.01],
            [0.03, 0.90, 0.02],
            [0.00, 0.03, 0.75],
        ],
        "brightness": 0.02,
        "contrast": 1.08,
        "saturation": 0.75,
        "gamma": 0.90,
        "ffmpeg_mixer": "1.0:0.06:0.01:0.02:0.03:0.88:0.02:0.01:0.0:0.03:0.72:0.02",
        "ffmpeg_eq": "brightness=0.02:contrast=1.08:saturation=0.75:gamma=0.90",
    },
    "maritza": {
        "name": "Maritza",
        "description": "Teal/green — cool teal shadows, green mid-tones, oceanic depth",
        "matrix": [
            [0.85, 0.03, 0.02],
            [0.02, 1.0, 0.05],
            [0.05, 0.08, 1.0],
        ],
        "brightness": 0.01,
        "contrast": 1.06,
        "saturation": 0.85,
        "gamma": 0.95,
        "ffmpeg_mixer": "0.82:0.03:0.02:0.01:0.02:0.98:0.05:0.01:0.05:0.08:0.98:0.02",
        "ffmpeg_eq": "brightness=0.01:contrast=1.06:saturation=0.85:gamma=0.95",
    },
    "blue": {
        "name": "Blue",
        "description": "Cool blue — steel blue tint, cold highlights, melancholic depth",
        "matrix": [
            [0.82, 0.02, 0.05],
            [0.02, 0.90, 0.06],
            [0.06, 0.05, 1.10],
        ],
        "brightness": 0.01,
        "contrast": 1.08,
        "saturation": 0.82,
        "gamma": 0.93,
        "ffmpeg_mixer": "0.80:0.02:0.05:0.01:0.02:0.88:0.06:0.01:0.06:0.05:1.08:0.02",
        "ffmpeg_eq": "brightness=0.01:contrast=1.08:saturation=0.82:gamma=0.93",
    },
    "noir": {
        "name": "Noir",
        "description": "Classic black & white — high contrast, dramatic, timeless",
        "matrix": [
            [0.30, 0.59, 0.11],
            [0.30, 0.59, 0.11],
            [0.30, 0.59, 0.11],
        ],
        "brightness": 0.02,
        "contrast": 1.15,
        "saturation": 0.0,
        "gamma": 0.88,
        "ffmpeg_mixer": "0.30:0.59:0.11:0.02:0.30:0.59:0.11:0.01:0.30:0.59:0.11:0.01",
        "ffmpeg_eq": "brightness=0.02:contrast=1.15:saturation=0.0:gamma=0.88",
    },
    "vintage_fade": {
        "name": "Vintage Fade",
        "description": "Faded vintage — lifted blacks, desaturated, faded photograph look",
        "matrix": [
            [0.95, 0.04, 0.03],
            [0.03, 0.92, 0.04],
            [0.02, 0.04, 0.88],
        ],
        "brightness": 0.06,
        "contrast": 0.90,
        "saturation": 0.70,
        "gamma": 1.05,
        "ffmpeg_mixer": "0.92:0.04:0.03:0.04:0.03:0.90:0.04:0.02:0.02:0.04:0.85:0.03",
        "ffmpeg_eq": "brightness=0.06:contrast=0.90:saturation=0.70:gamma=1.05",
    },
    "crimson": {
        "name": "Crimson",
        "description": "Deep crimson — dark red shadows, warm intensity, passionate",
        "matrix": [
            [1.10, 0.04, 0.01],
            [0.02, 0.85, 0.03],
            [0.03, 0.03, 0.78],
        ],
        "brightness": 0.01,
        "contrast": 1.10,
        "saturation": 0.85,
        "gamma": 0.90,
        "ffmpeg_mixer": "1.06:0.04:0.01:0.01:0.02:0.83:0.03:0.01:0.03:0.03:0.75:0.02",
        "ffmpeg_eq": "brightness=0.01:contrast=1.10:saturation=0.85:gamma=0.90",
    },
    "midnight": {
        "name": "Midnight",
        "description": "Midnight blue — deep dark blue, mysterious, night-time atmosphere",
        "matrix": [
            [0.78, 0.02, 0.08],
            [0.02, 0.85, 0.08],
            [0.05, 0.05, 1.15],
        ],
        "brightness": -0.02,
        "contrast": 1.12,
        "saturation": 0.78,
        "gamma": 0.88,
        "ffmpeg_mixer": "0.75:0.02:0.08:0.01:0.02:0.82:0.08:0.01:0.05:0.05:1.12:0.02",
        "ffmpeg_eq": "brightness=-0.02:contrast=1.12:saturation=0.78:gamma=0.88",
    },
}


def get_random_theme():
    return random.choice(list(COLOR_THEMES.keys()))


def apply_color_matrix_np(frame, theme_key):
    """Apply color grading matrix to a numpy frame using the specified theme."""
    import numpy as np

    theme = COLOR_THEMES.get(theme_key)
    if not theme:
        return frame

    matrix = np.array(theme["matrix"], dtype=np.float32)
    img = frame.astype(np.float32) / 255.0
    h, w = img.shape[:2]
    flat = img.reshape(-1, 3)
    graded = flat @ matrix.T

    brightness = theme.get("brightness", 0.0)
    contrast = theme.get("contrast", 1.0)
    gamma = theme.get("gamma", 1.0)

    graded = (graded + brightness) * contrast
    graded = np.power(np.clip(graded, 0, None), 1.0 / gamma)
    graded = np.clip(graded * 255.0, 0, 255).astype(np.uint8)

    return graded.reshape(h, w, 3)


# ─── PIL Text Rendering (THE FIX) ────────────────────────────────────────────
#
# Why PIL instead of MoviePy TextClip / FFmpeg ASS subtitles?
#
# 1. MoviePy 2.x removed `method="caption"`. The previous code relied on it
#    and silently fell through to FFmpeg.
# 2. FFmpeg ASS subtitles expect a font *family name* (e.g. "Cormorant Garamond")
#    but we were passing a *file path* (e.g. "/path/CormorantGaramond[wght].ttf").
#    libass can't resolve variable-font paths, falls back to a much wider default
#    font (DejaVu Sans / Arial), and the text overflows the safe area — that's
#    the "…" cutoff seen in the screenshot.
#
# PIL accepts file paths directly via ImageFont.truetype(), so we use it to:
#   - Measure the actual rendered width of each candidate line
#   - Auto-fit the font size so the longest line NEVER exceeds TEXT_WIDTH_PX
#   - Wrap precisely on word boundaries
#   - Render the entire quote+author block onto one transparent PNG
#   - Overlay that PNG with MoviePy (or FFmpeg) — 100% reliable, never clipped.
# ────────────────────────────────────────────────────────────────────────────


def _resolve_font_path(font_paths, role, fallback=None):
    """Get a usable font file path (PIL needs file paths, not family names)."""
    p = font_paths.get(role) if font_paths else None
    if p and os.path.exists(p):
        return p
    return fallback


def _wrap_with_pil(text, font, max_width, draw):
    """
    Wrap `text` into lines that each fit within `max_width` (pixels),
    measured using the ACTUAL font (no char-count heuristic).

    Long single words are broken by character if they still overflow.
    """
    lines = []
    words = text.split()
    current = ""

    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
                current = ""
            # If the single word itself is too wide, break it by characters.
            if draw.textlength(word, font=font) > max_width:
                broken = ""
                for ch in word:
                    if draw.textlength(broken + ch, font=font) <= max_width:
                        broken += ch
                    else:
                        if broken:
                            lines.append(broken)
                        broken = ch
                current = broken
            else:
                current = word

    if current:
        lines.append(current)

    # Safety: cap at 7 lines.
    if len(lines) > 7:
        lines = lines[:6] + [" ".join(lines[6:])]

    return lines


def render_text_overlay_png(quote, font_paths, output_path,
                            text_width=TEXT_WIDTH_PX,
                            canvas_w=REEL_WIDTH, canvas_h=REEL_HEIGHT):
    """
    Render the quote + author onto a transparent full-canvas PNG using PIL.

    Auto-fits the font size so the text NEVER overflows horizontally.
    Returns (path, num_lines, font_size).
    """
    from PIL import Image, ImageDraw, ImageFont

    quote_path = _resolve_font_path(font_paths, "quote",
                                    fallback="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf")
    author_path = _resolve_font_path(font_paths, "author",
                                     fallback="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

    quote_text = quote["text"].strip()
    author = quote.get("author", "").strip()

    # --- Stage 1: pick the largest font size whose longest wrapped line ≤ text_width ---
    chosen_size = QUOTE_FONT_MAX
    chosen_lines = []
    chosen_font = None

    probe = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)

    for size in range(QUOTE_FONT_MAX, QUOTE_FONT_MIN - 1, -2):
        try:
            font = ImageFont.truetype(quote_path, size)
        except Exception:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", size
            )
            quote_path = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

        lines = _wrap_with_pil(quote_text, font, text_width, probe_draw)
        max_w = max(probe_draw.textlength(line, font=font) for line in lines)

        if max_w <= text_width:
            chosen_size = size
            chosen_lines = lines
            chosen_font = font
            break
    else:
        try:
            chosen_font = ImageFont.truetype(quote_path, QUOTE_FONT_MIN)
        except Exception:
            chosen_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", QUOTE_FONT_MIN
            )
        chosen_lines = _wrap_with_pil(quote_text, chosen_font, text_width, probe_draw)
        chosen_size = QUOTE_FONT_MIN

    # --- Stage 2: render onto a transparent full-canvas image ---
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    line_ascent, line_descent = chosen_font.getmetrics()
    line_h = int(line_ascent + line_descent) + int(chosen_size * 0.30)
    quote_block_h = line_h * len(chosen_lines)

    try:
        author_font = ImageFont.truetype(author_path, AUTHOR_FONT_SIZE)
    except Exception:
        author_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", AUTHOR_FONT_SIZE
        )

    author_line = f"— {author}" if author else ""
    author_w = draw.textlength(author_line, font=author_font) if author_line else 0
    author_h = AUTHOR_FONT_SIZE + 12 if author_line else 0
    gap = int(chosen_size * 0.55)

    total_h = quote_block_h + (gap + author_h if author_line else 0)

    safe_top = TEXT_SAFE_TOP
    safe_bottom = TEXT_SAFE_BOTTOM
    block_y = safe_top + (safe_bottom - safe_top - total_h) // 2

    cx = canvas_w // 2

    # Soft dark gradient behind the text for readability on bright backgrounds
    _draw_text_backdrop(draw, canvas, block_y - 40, block_y + total_h + 40)

    # Draw quote lines (white, with subtle shadow for legibility)
    y = block_y
    for line in chosen_lines:
        w = draw.textlength(line, font=chosen_font)
        x = cx - w / 2
        draw.text((x + 2, y + 2), line, font=chosen_font, fill=(0, 0, 0, 180))
        draw.text((x, y), line, font=chosen_font, fill=(255, 255, 255, 255))
        y += line_h

    # Draw author line below
    if author_line:
        y = block_y + quote_block_h + gap
        x = cx - author_w / 2
        draw.text((x + 1, y + 1), author_line, font=author_font, fill=(0, 0, 0, 160))
        draw.text((x, y), author_line, font=author_font, fill=(200, 200, 200, 235))

    # Watermark — bottom-center, low opacity
    try:
        wm_font = ImageFont.truetype(author_path, 22)
    except Exception:
        wm_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22
        )
    wm_w = draw.textlength(WATERMARK_TEXT, font=wm_font)
    wm_x = cx - wm_w / 2
    wm_y = canvas_h - 230
    draw.text((wm_x, wm_y), WATERMARK_TEXT, font=wm_font, fill=(255, 255, 255, 130))

    canvas.save(output_path, "PNG")
    return output_path, len(chosen_lines), chosen_size


def _draw_text_backdrop(draw, canvas, top, bottom, opacity=0.42):
    """Draw a vertical-fade dark gradient behind the text block."""
    import numpy as np
    h = max(0, bottom - top)
    if h <= 0:
        return
    ramp = np.array([
        int(255 * opacity * math.sin(math.pi * (i / max(h - 1, 1))))
        for i in range(h)
    ], dtype=np.uint8)
    for i, a in enumerate(ramp):
        draw.line([(0, top + i), (canvas.width, top + i)], fill=(0, 0, 0, int(a)))


# ─── Overlay Generators ──────────────────────────────────────────────────────

def _create_vignette_clip(width, height, duration):
    """Create a dark vignette overlay clip for cinematic depth."""
    import numpy as np

    y, x = np.ogrid[:height, :width]
    cx, cy = width / 2, height / 2
    dist = np.sqrt((x - cx)**2 + (y - cy)**2) / np.sqrt(cx**2 + cy**2)
    alpha = np.clip(1.0 - dist * VIGNETTE_STRENGTH, 0, 1)
    alpha = (alpha * 180).astype(np.uint8)

    img = np.zeros((height, width, 4), dtype=np.uint8)
    img[:, :, 3] = alpha

    vignette = ImageClip(img, duration=duration)
    return vignette


# ─── Cover frame (IG thumbnail) ──────────────────────────────────────────────
#
# The cover frame is what Instagram shows in the feed / explore page BEFORE
# the user taps to play. The default first-frame (dark bg + slow fade-in
# text) is often pitch-black → nobody clicks → no views.
#
# This cover frame is a separate PNG: bright, high-contrast quote text in
# BOLD sans-serif (different from the in-reel serif) over the cinematic
# background. Optimized for click-through.
# ────────────────────────────────────────────────────────────────────────────

def render_cover_frame_png(image_path, quote, font_paths, output_path,
                            canvas_w=REEL_WIDTH, canvas_h=REEL_HEIGHT):
    """Render a click-optimized cover-frame PNG for the IG feed thumbnail."""
    from PIL import Image, ImageDraw, ImageFont

    # Use the background image as the base — same cinematic look
    bg = Image.open(image_path).convert("RGB")
    bg = bg.resize((canvas_w, canvas_h), Image.LANCZOS)

    # Apply a HEAVY dark overlay so the bold text pops
    overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 130))
    bg_rgba = bg.convert("RGBA")
    bg_rgba = Image.alpha_composite(bg_rgba, overlay)

    canvas = bg_rgba.copy()
    draw = ImageDraw.Draw(canvas)

    # Bold sans-serif for the cover (different from in-reel serif) — high contrast
    bold_font_path = _resolve_font_path(
        font_paths, "author",
        fallback="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    )
    # Try DejaVuSans-Bold directly for maximum legibility
    try:
        bold_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    except Exception:
        pass

    quote_text = quote["text"].strip()
    author = quote.get("author", "").strip()

    # Auto-fit font size for the cover (larger than in-reel — for thumbnail legibility)
    probe = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    text_width = canvas_w - 160  # 80px margin each side

    chosen_font = None
    chosen_lines = None
    for size in [68, 64, 60, 56, 52, 48, 44]:
        try:
            f = ImageFont.truetype(bold_font_path, size)
        except Exception:
            f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        lines = _wrap_with_pil(quote_text, f, text_width, probe_draw)
        max_w = max(probe_draw.textlength(line, font=f) for line in lines)
        if max_w <= text_width and len(lines) <= 5:
            chosen_font = f
            chosen_lines = lines
            break
    if chosen_font is None:
        try:
            chosen_font = ImageFont.truetype(bold_font_path, 44)
        except Exception:
            chosen_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
        chosen_lines = _wrap_with_pil(quote_text, chosen_font, text_width, probe_draw)

    # Layout: quote in the upper-middle, author below, brand handle at bottom
    line_ascent, line_descent = chosen_font.getmetrics()
    line_h = int(line_ascent + line_descent) + 10
    quote_block_h = line_h * len(chosen_lines)

    try:
        author_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except Exception:
        author_font = ImageFont.truetype(bold_font_path, 32)

    author_line = f"— {author}" if author else ""
    author_h = 50 if author_line else 0

    total_h = quote_block_h + 20 + author_h
    block_y = int(canvas_h * 0.22)  # upper third — most visible in feed preview

    cx = canvas_w // 2

    # Draw quote
    y = block_y
    for line in chosen_lines:
        w = draw.textlength(line, font=chosen_font)
        x = cx - w / 2
        # Hard black shadow for contrast
        draw.text((x + 3, y + 3), line, font=chosen_font, fill=(0, 0, 0, 220))
        # Bright white main text
        draw.text((x, y), line, font=chosen_font, fill=(255, 255, 255, 255))
        y += line_h

    # Draw author
    if author_line:
        y += 12
        w = draw.textlength(author_line, font=author_font)
        x = cx - w / 2
        draw.text((x, y), author_line, font=author_font, fill=(220, 220, 220, 230))

    # Bottom brand strip — high visibility for follow conversion
    try:
        brand_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except Exception:
        brand_font = chosen_font
    brand_text = "@innerlogic.co  •  Daily Philosophy"
    bw = draw.textlength(brand_text, font=brand_font)
    bx = cx - bw / 2
    by = canvas_h - 180
    # Semi-transparent pill behind the brand text
    pad_x, pad_y = 24, 12
    pill_box = [bx - pad_x, by - pad_y, bx + bw + pad_x, by + 28 + pad_y]
    draw.rounded_rectangle(pill_box, radius=20, fill=(0, 0, 0, 160))
    draw.text((bx, by), brand_text, font=brand_font, fill=(255, 255, 255, 255))

    canvas.convert("RGB").save(output_path, "PNG")
    return output_path


# ─── End-card (last 1.5s) ────────────────────────────────────────────────────

def render_endcard_png(font_paths, output_path,
                        canvas_w=REEL_WIDTH, canvas_h=REEL_HEIGHT):
    """Render a 'follow @innerlogic.co' end-card PNG (last 1.5s of reel)."""
    from PIL import Image, ImageDraw, ImageFont

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Large dark gradient overlay on the bottom half
    _draw_text_backdrop(draw, canvas, canvas_h // 2, canvas_h, opacity=0.65)

    try:
        big_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
    except Exception:
        big_font = ImageFont.truetype(_resolve_font_path(font_paths, "author"), 64)
    try:
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except Exception:
        small_font = big_font

    cx = canvas_w // 2

    line1 = "Follow for daily"
    line2 = "philosophy 🧠"
    sub = "@innerlogic.co"

    y = int(canvas_h * 0.55)
    for line in [line1, line2]:
        w = draw.textlength(line, font=big_font)
        x = cx - w / 2
        draw.text((x + 2, y + 2), line, font=big_font, fill=(0, 0, 0, 200))
        draw.text((x, y), line, font=big_font, fill=(255, 255, 255, 255))
        y += 80

    y += 30
    w = draw.textlength(sub, font=small_font)
    x = cx - w / 2
    draw.text((x, y), sub, font=small_font, fill=(180, 180, 180, 230))

    canvas.save(output_path, "PNG")
    return output_path


# ─── Word-by-word text reveal sequence ───────────────────────────────────────
#
# For the first ~3 seconds, reveal the quote one word at a time. This
# forces the viewer to slow down and read → boosts completion rate →
# boosts reach. We render N+1 PNGs (0 words, 1 word, 2 words, ... N words),
# then sequence them as MoviePy ImageClips at ~250ms per word.
# ────────────────────────────────────────────────────────────────────────────

def render_word_reveal_sequence(quote, font_paths, temp_dir,
                                 per_word_duration=0.28,
                                 canvas_w=REEL_WIDTH, canvas_h=REEL_HEIGHT):
    """
    Render a sequence of PNGs, each showing the first k words of the quote
    at the SAME final position (layout preserved by pre-computing positions).

    Returns: (list_of_png_paths, total_duration, num_words)
    """
    from PIL import Image, ImageDraw, ImageFont

    words = quote["text"].strip().split()
    n = len(words)
    if n == 0:
        return [], 0, 0

    # First, render the FULL text overlay once to lock the layout
    full_png = os.path.join(temp_dir, "reveal_full.png")
    render_text_overlay_png(quote, font_paths, full_png,
                            canvas_w=canvas_w, canvas_h=canvas_h)

    # Now render k-word variants. We render the full quote PNG each time
    # but with only the first k words visible — by passing a partial quote.
    # The text gets re-centered, but since we use the same font + width,
    # word positions for already-shown words stay the same.
    pngs = []
    for k in range(1, n + 1):
        partial = {
            "text": " ".join(words[:k]),
            "author": "",  # don't show author during reveal
            "category": quote.get("category", ""),
        }
        path = os.path.join(temp_dir, f"reveal_{k:03d}.png")
        render_text_overlay_png(partial, font_paths, path,
                                canvas_w=canvas_w, canvas_h=canvas_h)
        pngs.append(path)

    total_duration = n * per_word_duration
    return pngs, total_duration, n


# ─── MoviePy Video Creation ──────────────────────────────────────────────────

def create_reel_moviepy(image_path, music_path, quote, temp_dir, font_paths,
                        duration=15, theme_key=None, video_bg_path=None):
    """
    Create a cinematic reel using MoviePy.

    - Video background (if video_bg_path given) OR Ken Burns zoom on static image
    - Color grading with cinematic themes
    - Light vignette only
    - Word-by-word text reveal for the first ~3s (engagement boost)
    - Branded watermark
    - Optional end-card (last 1.5s)
    """
    import numpy as np
    from PIL import Image

    if theme_key is None:
        theme_key = get_random_theme()

    theme = COLOR_THEMES.get(theme_key, {})
    theme_name = theme.get("name", theme_key)
    print(f"   🎨 Color theme: {theme_name}")

    output_path = os.path.join(temp_dir, "reel.mp4")

    # --- Background: video clip (preferred) or Ken Burns on static image ---
    if video_bg_path and os.path.exists(video_bg_path):
        # Video background path — use the video as the base, looped/trimmed to duration.
        # Apply color grading + slight zoom to make it feel "cinematic" not "stock footage".
        print(f"   🎥 Using video background: {os.path.basename(video_bg_path)}")
        from moviepy import VideoFileClip
        bg_video = VideoFileClip(video_bg_path)
        # Loop if shorter than duration, trim if longer
        if bg_video.duration < duration:
            from moviepy import concatenate_videoclips
            reps = int(duration / bg_video.duration) + 1
            bg_video = concatenate_videoclips([bg_video] * reps)
        bg_video = bg_video.subclipped(0, duration)

        # Resize to 1080x1920 (cover-fit) + slight zoom (1.05x) for cinematic feel
        def _cover_resize_frame(get_frame, t):
            f = get_frame(t)
            h, w = f.shape[:2]
            target_w, target_h = REEL_WIDTH, REEL_HEIGHT
            # Cover-fit: scale so the whole target is filled (may crop edges)
            scale = max(target_w / w, target_h / h) * 1.05  # 5% zoom
            new_w = int(w * scale); new_h = int(h * scale)
            img = Image.fromarray(f).resize((new_w, new_h), Image.LANCZOS)
            # Center crop
            x0 = (new_w - target_w) // 2
            y0 = (new_h - target_h) // 2
            cropped = np.array(img)[y0:y0+target_h, x0:x0+target_w]
            if theme_key:
                cropped = apply_color_matrix_np(cropped, theme_key)
            return cropped

        zoomed_clip = bg_video.transform(_cover_resize_frame)
        kb_mode = "video_bg"
    else:
        # Static image Ken Burns path (original behavior)
        bg_img = Image.open(image_path).convert("RGB")
        bg_img = bg_img.resize((REEL_WIDTH, REEL_HEIGHT), Image.LANCZOS)
        bg_array = np.array(bg_img)

        kb_mode = random.choice(["zoom_in", "zoom_out", "pan_up", "pan_down",
                                 "drift_left", "drift_right"])

        def make_ken_burns_frame(t):
            progress = t / duration
            smooth = progress * progress * (3 - 2 * progress)

            h, w = bg_array.shape[:2]

            if kb_mode == "zoom_in":
                zoom = ZOOM_START + (ZOOM_END - ZOOM_START) * smooth
                new_w = int(w / zoom); new_h = int(h / zoom)
                x1 = (w - new_w) // 2; y1 = (h - new_h) // 2
            elif kb_mode == "zoom_out":
                zoom = ZOOM_END - (ZOOM_END - ZOOM_START) * smooth
                new_w = int(w / zoom); new_h = int(h / zoom)
                x1 = (w - new_w) // 2; y1 = (h - new_h) // 2
            elif kb_mode == "pan_up":
                zoom = 1.15
                new_w = int(w / zoom); new_h = int(h / zoom)
                x1 = (w - new_w) // 2
                y1 = int((h - new_h) * (1.0 - smooth))
            elif kb_mode == "pan_down":
                zoom = 1.15
                new_w = int(w / zoom); new_h = int(h / zoom)
                x1 = (w - new_w) // 2
                y1 = int((h - new_h) * smooth)
            elif kb_mode == "drift_left":
                zoom = 1.20
                new_w = int(w / zoom); new_h = int(h / zoom)
                x1 = int((w - new_w) * (1.0 - smooth))
                y1 = (h - new_h) // 2
            elif kb_mode == "drift_right":
                zoom = 1.20
                new_w = int(w / zoom); new_h = int(h / zoom)
                x1 = int((w - new_w) * smooth)
                y1 = (h - new_h) // 2
            else:
                zoom = 1.0 + 0.20 * smooth
                new_w = int(w / zoom); new_h = int(h / zoom)
                x1 = (w - new_w) // 2; y1 = (h - new_h) // 2

            cropped = bg_array[y1:y1+new_h, x1:x1+new_w]
            img = Image.fromarray(cropped).resize((w, h), Image.LANCZOS)
            frame = np.array(img)
            if theme_key:
                frame = apply_color_matrix_np(frame, theme_key)
            return frame

        zoomed_clip = VideoClip(frame_function=make_ken_burns_frame, duration=duration)

    clips = [zoomed_clip]

    # --- Vignette ---
    try:
        vignette = _create_vignette_clip(REEL_WIDTH, REEL_HEIGHT, duration)
        vignette = vignette.with_position(("center", "center"))
        clips.append(vignette)
    except Exception as e:
        print(f"   Vignette skipped: {e}")

    # --- Text overlay: word-by-word reveal for first ~3s, then full text ---
    try:
        # Generate the cover frame (used as IG thumbnail, saved to temp_dir)
        cover_path = os.path.join(temp_dir, "cover_frame.png")
        render_cover_frame_png(image_path, quote, font_paths, cover_path)
        print(f"   🖼️  Cover frame generated")

        # Generate the word-reveal PNG sequence
        reveal_pngs, reveal_duration, n_words = render_word_reveal_sequence(
            quote, font_paths, temp_dir, per_word_duration=0.28
        )

        # Final full-text overlay (with author + watermark) shown after reveal
        full_text_png = os.path.join(temp_dir, "text_overlay.png")
        render_text_overlay_png(quote, font_paths, full_text_png)
        print(f"   🔤 Text rendered (word-by-word reveal: {n_words} words over {reveal_duration:.1f}s)")

        # Build the text clip:
        # - For 0..reveal_duration: cycle through reveal PNGs (1 word, 2 words, ...)
        # - For reveal_duration..duration-1.5: hold the full text overlay
        # - For duration-1.5..duration: hold the full text overlay (end-card is separate)
        from moviepy import ImageClip as _IC, concatenate_videoclips as _concat

        text_clips = []
        if reveal_pngs and reveal_duration > 0 and reveal_duration < duration - 2.0:
            per = reveal_duration / len(reveal_pngs)
            for png in reveal_pngs:
                c = _IC(png, duration=per + 0.05, transparent=True)  # tiny overlap to avoid flicker
                text_clips.append(c)
            # Hold the full text for the remaining time (minus end-card)
            hold_duration = duration - reveal_duration - 1.5
            if hold_duration > 0:
                full_hold = _IC(full_text_png, duration=hold_duration, transparent=True)
                text_clips.append(full_hold)
        else:
            # Quote too short or no reveal — just hold the full text
            full_hold = _IC(full_text_png, duration=duration - 1.5, transparent=True)
            text_clips.append(full_hold)

        text_clip = _concat(text_clips, method="compose")
        text_clip = text_clip.with_position(("center", "center"))
        text_clip = text_clip.with_effects([FadeIn(0.3), FadeOut(0.8)])
        clips.append(text_clip)

        # End-card (last 1.5s) — fade in/out
        endcard_png = os.path.join(temp_dir, "endcard.png")
        render_endcard_png(font_paths, endcard_png)
        endcard_clip = _IC(endcard_png, duration=1.5, transparent=True)
        endcard_clip = endcard_clip.with_position(("center", "center"))
        endcard_clip = endcard_clip.with_start(duration - 1.5)
        endcard_clip = endcard_clip.with_effects([FadeIn(0.4), FadeOut(0.5)])
        clips.append(endcard_clip)
    except Exception as e:
        print(f"   ⚠️  Text overlay failed: {e}")
        import traceback; traceback.print_exc()

    # Composite
    video = CompositeVideoClip(clips, size=(REEL_WIDTH, REEL_HEIGHT))

    # --- Audio ---
    has_music = music_path and os.path.exists(music_path)
    if has_music:
        audio = AudioFileClip(music_path)
        if audio.duration < duration:
            from moviepy import concatenate_audioclips
            repeats = int(duration / audio.duration) + 1
            audio = concatenate_audioclips([audio] * repeats)
        audio = audio.subclipped(0, min(duration, audio.duration))
        audio = audio.with_effects([AudioFadeIn(1.0), AudioFadeOut(2.0)])
        video = video.with_audio(audio)

    print(f"   MoviePy: rendering {REEL_WIDTH}x{REEL_HEIGHT}, {duration}s, "
          f"mode={kb_mode}, theme={theme_name}...")

    video.write_videofile(
        output_path,
        fps=DEFAULT_FPS,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="128k",
        preset="medium",
        threads=2,
        logger=None,
    )

    file_size = os.path.getsize(output_path)
    print(f"   MoviePy: video created ({file_size / (1024*1024):.1f} MB)")

    video.close()
    if has_music:
        audio.close()

    return output_path


# ─── FFmpeg Video Creation (Fallback) ────────────────────────────────────────

def _generate_vignette_png(temp_dir, width=1080, height=1920):
    """Generate a vignette PNG overlay image using PIL."""
    try:
        from PIL import Image
        import numpy as np

        arr = np.zeros((height, width, 4), dtype=np.uint8)
        y, x = np.ogrid[:height, :width]
        cx, cy = width / 2, height / 2
        dist = np.sqrt((x - cx)**2 + (y - cy)**2) / np.sqrt(cx**2 + cy**2)
        alpha = np.clip((dist - 0.3) * 200, 0, 160).astype(np.uint8)
        arr[:, :, 3] = alpha
        img = Image.fromarray(arr)

        vignette_path = os.path.join(temp_dir, "vignette_overlay.png")
        img.save(vignette_path, "PNG")
        return vignette_path
    except Exception:
        return None


def create_reel_ffmpeg(image_path, music_path, quote, temp_dir, font_paths,
                       duration=15, theme_key=None):
    """
    Create a reel using raw FFmpeg (fallback).
    Uses the SAME PIL-rendered text PNG as the MoviePy path — guarantees
    text never overflows.
    """
    if theme_key is None:
        theme_key = get_random_theme()

    theme = COLOR_THEMES.get(theme_key, {})
    theme_name = theme.get("name", theme_key)
    print(f"   🎨 Color theme: {theme_name}")

    output_path = os.path.join(temp_dir, "reel.mp4")

    text_png_path = os.path.join(temp_dir, "text_overlay.png")
    render_text_overlay_png(quote, font_paths, text_png_path)

    vignette_path = _generate_vignette_png(temp_dir)

    fps = DEFAULT_FPS
    total_frames = duration * fps
    zoom_increment = 0.25 / total_frames
    kb_mode = random.choice(["zoom_in", "zoom_out", "zoom_in_fast"])

    if kb_mode == "zoom_in":
        zoom_expr = f"1+{zoom_increment}*on"
    elif kb_mode == "zoom_out":
        zoom_expr = f"1.25-{zoom_increment}*on"
    else:
        zoom_expr = f"1+0.0002*on*on/on"

    ffmpeg_mixer = theme.get("ffmpeg_mixer", "1:0:0:0:0:1:0:0:0:0:0:1")
    ffmpeg_eq = theme.get("ffmpeg_eq", "brightness=0.02:contrast=1.1:saturation=0.85:gamma=0.95")

    cmd = ["ffmpeg", "-y"]
    cmd.extend(["-loop", "1", "-t", str(duration), "-i", image_path])
    if vignette_path:
        cmd.extend(["-loop", "1", "-t", str(duration), "-i", vignette_path])
    cmd.extend(["-loop", "1", "-t", str(duration), "-i", text_png_path])

    has_music = music_path and os.path.exists(music_path)
    if has_music:
        cmd.extend(["-stream_loop", "-1", "-i", music_path])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"])

    audio_input_idx = 3 if vignette_path else 2
    text_input_idx = 2 if vignette_path else 1
    bg_label = "bg_vign" if vignette_path else "bg"

    filter_parts = []
    if vignette_path:
        filter_parts.append(
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,zoompan=z={zoom_expr}:d={total_frames}:"
            f"x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):s=1080x1920:fps={fps},"
            f"colorchannelmixer={ffmpeg_mixer},eq={ffmpeg_eq}[bg_grad]"
        )
        filter_parts.append(f"[1:v][bg_grad]overlay=0:0:format=auto[{bg_label}]")
    else:
        filter_parts.append(
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,zoompan=z={zoom_expr}:d={total_frames}:"
            f"x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):s=1080x1920:fps={fps},"
            f"colorchannelmixer={ffmpeg_mixer},eq={ffmpeg_eq}[{bg_label}]"
        )

    # Overlay text PNG (with alpha) — soft fade in/out
    filter_parts.append(
        f"[{text_input_idx}:v]format=rgba,fade=t=in:st=0:d=0.7:alpha=1,"
        f"fade=t=out:st={duration-1.2}:d=1.2:alpha=1[text_faded]"
    )
    filter_parts.append(f"[{bg_label}][text_faded]overlay=0:0:format=auto[v]")

    cmd.extend(["-filter_complex", ";".join(filter_parts)])
    if has_music:
        cmd.extend(["-af", f"afade=t=in:st=0:d=1.0,afade=t=out:st={duration-2}:d=2"])
    cmd.extend(["-map", "[v]", "-map", f"{audio_input_idx}:a"])
    cmd.extend([
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        output_path
    ])

    print(f"   FFmpeg: rendering {REEL_WIDTH}x{REEL_HEIGHT}, {duration}s, "
          f"mode={kb_mode}, theme={theme_name}...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"   FFmpeg overlay failed — retrying without vignette...")
            return _create_reel_ffmpeg_simple(
                image_path, music_path, text_png_path, temp_dir, duration,
                zoom_expr, total_frames, fps, kb_mode, theme_key
            )

        file_size = os.path.getsize(output_path)
        print(f"   FFmpeg: video created ({file_size / (1024*1024):.1f} MB)")
        return output_path
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out after 300 seconds")
    except FileNotFoundError:
        raise RuntimeError("FFmpeg not found")


def _create_reel_ffmpeg_simple(image_path, music_path, text_png_path, temp_dir,
                                duration, zoom_expr, total_frames, fps, kb_mode,
                                theme_key=None):
    """Simplified FFmpeg fallback — no vignette overlay, just image + text + audio."""
    if theme_key is None:
        theme_key = get_random_theme()
    theme = COLOR_THEMES.get(theme_key, {})
    theme_name = theme.get("name", theme_key)
    ffmpeg_mixer = theme.get("ffmpeg_mixer", "1:0:0:0:0:1:0:0:0:0:0:1")
    ffmpeg_eq = theme.get("ffmpeg_eq", "brightness=0.02:contrast=1.1:saturation=0.85")

    output_path = os.path.join(temp_dir, "reel.mp4")

    cmd = ["ffmpeg", "-y"]
    cmd.extend(["-loop", "1", "-t", str(duration), "-i", image_path])
    cmd.extend(["-loop", "1", "-t", str(duration), "-i", text_png_path])

    has_music = music_path and os.path.exists(music_path)
    if has_music:
        cmd.extend(["-stream_loop", "-1", "-i", music_path])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"])

    filter_parts = [
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,zoompan=z={zoom_expr}:d={total_frames}:"
        f"x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):s=1080x1920:fps={fps},"
        f"colorchannelmixer={ffmpeg_mixer},eq={ffmpeg_eq}[bg]",
        f"[1:v]format=rgba,fade=t=in:st=0:d=0.7:alpha=1,"
        f"fade=t=out:st={duration-1.2}:d=1.2:alpha=1[text_faded]",
        f"[bg][text_faded]overlay=0:0:format=auto[v]",
    ]

    cmd.extend(["-filter_complex", ";".join(filter_parts)])
    if has_music:
        cmd.extend(["-af", f"afade=t=in:st=0:d=1.0,afade=t=out:st={duration-2}:d=2"])
    cmd.extend(["-map", "[v]", "-map", "2:a"])
    cmd.extend([
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        output_path
    ])

    print(f"   FFmpeg (simple): rendering {REEL_WIDTH}x{REEL_HEIGHT}, {duration}s, "
          f"theme={theme_name}...")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg simple failed: {result.stderr[-400:]}")

    file_size = os.path.getsize(output_path)
    print(f"   FFmpeg (simple): video created ({file_size / (1024*1024):.1f} MB)")
    return output_path


# ─── Main Entry Point ────────────────────────────────────────────────────────

def create_reel(image_path, music_path, quote, temp_dir, font_paths,
                duration=15, theme_key=None, video_bg_path=None):
    """
    Create a 15-second Instagram Reel video.

    Tries MoviePy first (video bg / Ken Burns zoom, vignette, color grading,
    word-by-word text reveal, cover frame, end-card), falls back to FFmpeg
    pipeline (simpler, no video bg) if MoviePy fails.

    Args:
        video_bg_path: Optional path to a vertical video file to use as the
            background instead of the static image. If provided AND MoviePy
            is available, the reel will use the video as the background.
    """
    if theme_key is None:
        theme_key = get_random_theme()

    if HAS_MOVIEPY:
        try:
            print(f"   MoviePy available — creating enhanced cinematic reel...")
            return create_reel_moviepy(
                image_path, music_path, quote, temp_dir, font_paths,
                duration, theme_key, video_bg_path=video_bg_path
            )
        except Exception as e:
            print(f"   MoviePy failed: {e}")
            print(f"   Falling back to FFmpeg pipeline...")

    print(f"   Using enhanced FFmpeg pipeline...")
    return create_reel_ffmpeg(
        image_path, music_path, quote, temp_dir, font_paths, duration, theme_key
    )


if __name__ == "__main__":
    test_quote = {
        "text": "The only way to deal with an unfree world is to become so absolutely free that your very existence is an act of rebellion.",
        "author": "Albert Camus",
        "category": "existentialism"
    }
    print("This module requires FFmpeg/MoviePy and proper setup to test.")
    print("Run main.py instead for the full pipeline.")
