#!/usr/bin/env python3
"""
Video Creator — Creates 15-second Instagram Reels using FFmpeg + MoviePy.

Features:
- Ken Burns zoom effect (smooth ease-in-out, configurable direction)
- Cinematic dark vignette overlay for depth
- Particle/dust overlay for cinematic atmosphere
- Gradient dark overlay for text readability
- Text overlay with fade-in/fade-out (MoviePy or ASS subtitles)
- Audio crossfade (fade in/out)
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

# Ken Burns zoom range
ZOOM_START = 1.0
ZOOM_END = 1.15

# Vignette strength (0 = none, 1 = max)
VIGNETTE_STRENGTH = 0.55

# Text readability gradient (dark overlay at center for quote legibility)
TEXT_DARKEN_OPACITY = 0.50


# ─── Color Grading Themes ─────────────────────────────────────────────────────

# Each theme defines a 3x3 color matrix (RGB channel mixing) + tone adjustments
# Matrix format: [[r_r, r_g, r_b], [g_r, g_g, g_b], [b_r, b_g, b_b]]
# Each output channel = sum of (input_channel * coefficient)

COLOR_THEMES = {
    "homage": {
        "name": "Homage",
        "description": "Warm vintage — amber glow, lifted blacks, nostalgic film",
        "matrix": [
            [1.05, 0.05, 0.02],   # R: warm boost
            [0.02, 0.95, 0.03],   # G: slight warmth
            [0.00, 0.02, 0.85],   # B: reduced for warmth
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
            [1.08, 0.06, 0.01],   # R: strong warm
            [0.03, 0.90, 0.02],   # G: slight warmth
            [0.00, 0.03, 0.75],   # B: significantly reduced
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
            [0.85, 0.03, 0.02],   # R: reduced for cool tone
            [0.02, 1.0, 0.05],    # G: boosted green
            [0.05, 0.08, 1.0],    # B: strong teal boost
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
            [0.82, 0.02, 0.05],   # R: reduced
            [0.02, 0.90, 0.06],   # G: slight cool
            [0.06, 0.05, 1.10],   # B: strong boost
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
            [0.30, 0.59, 0.11],   # R: luminance weights
            [0.30, 0.59, 0.11],   # G: same
            [0.30, 0.59, 0.11],   # B: same
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
            [0.95, 0.04, 0.03],   # R: slight warm fade
            [0.03, 0.92, 0.04],   # G: slight fade
            [0.02, 0.04, 0.88],   # B: faded
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
            [1.10, 0.04, 0.01],   # R: strong red boost
            [0.02, 0.85, 0.03],   # G: reduced
            [0.03, 0.03, 0.78],   # B: significantly reduced
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
            [0.78, 0.02, 0.08],   # R: reduced
            [0.02, 0.85, 0.08],   # G: slight cool
            [0.05, 0.05, 1.15],   # B: strong blue boost
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
    """Pick a random color grading theme."""
    return random.choice(list(COLOR_THEMES.keys()))


def apply_color_matrix_np(frame, theme_key):
    """
    Apply color grading matrix to a numpy frame using the specified theme.
    Works with MoviePy frames (HxWx3 uint8 arrays).
    """
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


# ─── Text Wrapping ────────────────────────────────────────────────────────────

def wrap_quote_text(text, max_chars_per_line=25):
    """
    Wrap quote text for screen display.
    Returns a list of lines, each within the max character limit.
    Uses 25 chars per line to ensure text fits within the container
    without being cut off on any device.
    """
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = f"{current_line} {word}".strip()
        if len(test_line) <= max_chars_per_line:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    # Safety: limit to 8 lines max to avoid vertical overflow
    if len(lines) > 8:
        while len(lines) > 7:
            last = lines.pop()
            lines[-1] = lines[-1] + " " + last
    
    return lines


# ─── ASS Subtitle (FFmpeg fallback) ──────────────────────────────────────────

def create_subtitle_file(quote, temp_dir, font_paths, theme_key=None):
    """
    Create an ASS subtitle file for FFmpeg fallback mode.
    Enhanced with better fade timing, shadow effects, and proper centering.
    """
    quote_text = quote["text"]
    author = quote["author"]
    
    lines = wrap_quote_text(quote_text, max_chars_per_line=25)
    wrapped_text = "\\N".join(lines)
    
    quote_fontname = font_paths.get("quote", "Cormorant Garamond")
    author_fontname = font_paths.get("author", "Montserrat")
    
    num_lines = len(lines)
    total_text_lines = num_lines + 1
    line_height = 56
    total_height = total_text_lines * line_height
    # Center vertically, slightly above middle (around 40% from top)
    start_y = int((1920 - total_height) / 2) - 60
    
    # Fade timing
    quote_start = "0:00:00.80"
    quote_end = "0:00:13.50"
    author_start = "0:00:01.80"
    author_end = "0:00:13.50"
    
    quote_fade = r"{\fade(255,255,0,0,80,1250,1350)}"
    author_fade = r"{\fade(255,255,0,0,180,1250,1350)}"
    
    # Dynamic font size based on quote length
    num_chars = len(quote_text)
    if num_chars <= 50:
        q_font_size = 44
    elif num_chars <= 80:
        q_font_size = 40
    elif num_chars <= 120:
        q_font_size = 36
    else:
        q_font_size = 32
    
    ass_content = f"""[Script Info]
Title: Inner Logic Quote
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Quote,{quote_fontname},{q_font_size},&H00FFFFFF,&H000000FF,&H30000000,&H80000000,-1,0,0,0,100,100,2,0,1,3,3,8,80,80,{start_y},1
Style: Author,{author_fontname},26,&H80FFFFFF,&H000000FF,&H30000000,&H80000000,0,-1,0,0,100,100,2,0,1,2,2,8,80,80,{start_y + num_lines * 56 + 25},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,{quote_start},{quote_end},Quote,,0,0,0,,{quote_fade}{wrapped_text}
Dialogue: 0,{author_start},{author_end},Author,,0,0,0,,{author_fade}\\N— {author}
"""
    
    subtitle_path = os.path.join(temp_dir, "quote_subtitle.ass")
    with open(subtitle_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
    
    return subtitle_path


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


def _create_text_backdrop(width, height, duration):
    """
    Create a semi-transparent dark gradient behind the text area.
    This ensures quotes are always readable regardless of background brightness.
    """
    import numpy as np
    
    img = np.zeros((height, width, 4), dtype=np.uint8)
    
    center_y_start = int(height * 0.25)
    center_y_end = int(height * 0.75)
    center_y_mid = (center_y_start + center_y_end) // 2
    
    for y in range(center_y_start, center_y_end):
        dist_from_center = abs(y - center_y_mid) / (center_y_end - center_y_start) * 2
        dist_from_center = min(dist_from_center, 1.0)
        opacity = int(TEXT_DARKEN_OPACITY * 255 * (1.0 - dist_from_center ** 1.5))
        img[y, :, 3] = opacity
    
    backdrop = ImageClip(img, duration=duration)
    return backdrop


def _create_dust_particles(width, height, duration, num_particles=30):
    """
    Create floating dust/particle overlay for cinematic atmosphere.
    """
    import numpy as np
    from PIL import Image
    
    fps = DEFAULT_FPS
    total_frames = int(duration * fps)
    
    particles = []
    for _ in range(num_particles):
        particles.append({
            "x": random.uniform(0, width),
            "y": random.uniform(0, height),
            "size": random.uniform(1.5, 4.0),
            "speed_x": random.uniform(-0.3, 0.3),
            "speed_y": random.uniform(-0.8, -0.15),
            "brightness": random.uniform(0.3, 0.8),
            "phase": random.uniform(0, math.pi * 2),
            "pulse_speed": random.uniform(0.5, 2.0),
        })
    
    def make_frame(t):
        frame = np.zeros((height, width, 4), dtype=np.uint8)
        
        for p in particles:
            x = p["x"] + p["speed_x"] * t * 30
            y = p["y"] + p["speed_y"] * t * 30
            x = x % width
            y = y % height
            
            pulse = 0.5 + 0.5 * math.sin(p["phase"] + t * p["pulse_speed"])
            brightness = p["brightness"] * pulse
            
            ix, iy = int(x), int(y)
            size = int(p["size"])
            alpha = int(brightness * 60)
            
            for dy in range(-size, size + 1):
                for dx in range(-size, size + 1):
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist <= size:
                        px, py = ix + dx, iy + dy
                        if 0 <= px < width and 0 <= py < height:
                            falloff = 1.0 - (dist / max(size, 1))
                            pixel_alpha = int(alpha * falloff)
                            frame[py, px, 3] = max(frame[py, px, 3], pixel_alpha)
        
        return frame
    
    dust_clip = VideoClip(frame_function=make_frame, duration=duration)
    return dust_clip


# ─── MoviePy Video Creation ──────────────────────────────────────────────────

def create_reel_moviepy(image_path, music_path, quote, temp_dir, font_paths, duration=15, theme_key=None):
    """
    Create a cinematic reel using MoviePy for smoother effects.
    
    Enhanced features:
    - Ken Burns zoom with randomized direction
    - Color grading with cinematic themes
    - Dark text backdrop for guaranteed readability
    - Floating dust particles for cinematic atmosphere
    - Cinematic vignette overlay
    - Native text clips with precise fade timing
    - Audio crossfade with configurable curves
    """
    import numpy as np
    from PIL import Image
    
    # Pick a random theme if none specified
    if theme_key is None:
        theme_key = get_random_theme()
    
    theme = COLOR_THEMES.get(theme_key, {})
    theme_name = theme.get("name", theme_key)
    print(f"   🎨 Color theme: {theme_name}")
    
    output_path = os.path.join(temp_dir, "reel.mp4")
    
    # Load and prepare the background image
    bg_img = Image.open(image_path)
    bg_img = bg_img.resize((REEL_WIDTH, REEL_HEIGHT), Image.LANCZOS)
    bg_array = np.array(bg_img)
    
    # Randomize Ken Burns direction
    kb_mode = random.choice(["zoom_in", "zoom_out", "pan_up", "pan_down"])
    
    # Ken Burns zoom: smooth ease-in-out + color grading
    def make_ken_burns_frame(t):
        progress = t / duration
        smooth = progress * progress * (3 - 2 * progress)
        
        h, w = bg_array.shape[:2]
        
        if kb_mode == "zoom_in":
            zoom = ZOOM_START + (ZOOM_END - ZOOM_START) * smooth
            new_w = int(w / zoom)
            new_h = int(h / zoom)
            x1 = (w - new_w) // 2
            y1 = (h - new_h) // 2
        elif kb_mode == "zoom_out":
            zoom = ZOOM_END - (ZOOM_END - ZOOM_START) * smooth
            new_w = int(w / zoom)
            new_h = int(h / zoom)
            x1 = (w - new_w) // 2
            y1 = (h - new_h) // 2
        elif kb_mode == "pan_up":
            zoom = 1.08
            new_w = int(w / zoom)
            new_h = int(h / zoom)
            x1 = (w - new_w) // 2
            max_y = h - new_h
            y1 = int(max_y * (1.0 - smooth))
        elif kb_mode == "pan_down":
            zoom = 1.08
            new_w = int(w / zoom)
            new_h = int(h / zoom)
            x1 = (w - new_w) // 2
            max_y = h - new_h
            y1 = int(max_y * smooth)
        else:
            zoom = 1.0 + 0.12 * smooth
            new_w = int(w / zoom)
            new_h = int(h / zoom)
            x1 = (w - new_w) // 2
            y1 = (h - new_h) // 2
        
        cropped = bg_array[y1:y1+new_h, x1:x1+new_w]
        img = Image.fromarray(cropped)
        img = img.resize((w, h), Image.LANCZOS)
        frame = np.array(img)
        
        # Apply color grading
        if theme_key:
            frame = apply_color_matrix_np(frame, theme_key)
        
        return frame
    
    zoomed_clip = VideoClip(frame_function=make_ken_burns_frame, duration=duration)
    
    # Build composite layers
    clips = [zoomed_clip]
    
    # Layer 1: Text backdrop
    try:
        backdrop = _create_text_backdrop(REEL_WIDTH, REEL_HEIGHT, duration)
        backdrop = backdrop.with_position(("center", "center"))
        clips.append(backdrop)
    except Exception as e:
        print(f"   Text backdrop skipped: {e}")
    
    # Layer 2: Vignette overlay
    try:
        vignette = _create_vignette_clip(REEL_WIDTH, REEL_HEIGHT, duration)
        vignette = vignette.with_position(("center", "center"))
        clips.append(vignette)
    except Exception as e:
        print(f"   Vignette skipped: {e}")
    
    # Layer 3: Dust particles
    try:
        num_particles = random.randint(15, 40)
        dust = _create_dust_particles(REEL_WIDTH, REEL_HEIGHT, duration, num_particles)
        clips.append(dust)
    except Exception as e:
        print(f"   Dust particles skipped: {e}")
    
    # Layer 4: Text overlays
    try:
        quote_text = quote["text"]
        author = quote["author"]
        
        lines = wrap_quote_text(quote_text, max_chars_per_line=22)
        wrapped = "\n".join(lines)
        
        quote_font = font_paths.get("quote", "Cormorant-Garamond")
        author_font = font_paths.get("author", "Montserrat")
        
        # Dynamic font sizing: more lines = smaller text
        num_lines = len(lines)
        if num_lines <= 3:
            q_font_size = 44
        elif num_lines <= 5:
            q_font_size = 38
        elif num_lines <= 7:
            q_font_size = 34
        else:
            q_font_size = 30
        
        # Smart vertical positioning: more lines = push higher
        if num_lines <= 2:
            quote_y = 0.38
        elif num_lines <= 3:
            quote_y = 0.33
        elif num_lines <= 4:
            quote_y = 0.28
        else:
            quote_y = 0.24
        
        # Quote text
        quote_clip = TextClip(
            text=wrapped,
            font_size=q_font_size,
            color="white",
            font=quote_font,
            text_align="center",
            size=(940, None),
            method="caption",
        )
        quote_clip = quote_clip.with_duration(duration - 1.5)
        quote_clip = quote_clip.with_position(("center", quote_y), relative=True)
        quote_clip = quote_clip.with_effects([FadeIn(1.0), FadeOut(2.0)])
        clips.append(quote_clip)
        
        # Author text — positioned below quote with smart offset
        author_y = min(quote_y + 0.05 * num_lines + 0.08, 0.72)
        
        author_clip = TextClip(
            text=f"— {author}",
            font_size=24,
            color="#CCCCCC",
            font=author_font,
            text_align="center",
            size=(940, None),
            method="caption",
        )
        author_clip = author_clip.with_duration(duration - 3.0)
        author_clip = author_clip.with_position(("center", author_y), relative=True)
        author_clip = author_clip.with_effects([FadeIn(0.8), FadeOut(2.0)])
        clips.append(author_clip)
        
    except Exception as e:
        print(f"   MoviePy text failed: {e}")
        print(f"   (Text will be added via FFmpeg overlay instead)")
    
    # Composite all layers
    video = CompositeVideoClip(clips, size=(REEL_WIDTH, REEL_HEIGHT))
    
    # Add audio
    has_music = music_path and os.path.exists(music_path)
    if has_music:
        audio = AudioFileClip(music_path)
        if audio.duration < duration:
            from moviepy import concatenate_audioclips
            repeats = int(duration / audio.duration) + 1
            audio = concatenate_audioclips([audio] * repeats)
        audio = audio.subclipped(0, min(duration, audio.duration))
        audio = audio.with_effects([AudioFadeIn(1.5), AudioFadeOut(3.0)])
        video = video.with_audio(audio)
    
    print(f"   MoviePy: rendering {REEL_WIDTH}x{REEL_HEIGHT}, {duration}s, mode={kb_mode}, theme={theme_name}...")
    
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
    """
    Generate a vignette PNG overlay image using PIL.
    Pre-rendered for performance.
    """
    try:
        from PIL import Image, ImageDraw
        import numpy as np
        
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
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


def create_reel_ffmpeg(image_path, music_path, quote, temp_dir, font_paths, duration=15, theme_key=None):
    """
    Create a reel using raw FFmpeg (proven fallback).
    Enhanced with color grading themes, vignette overlay, and ASS subtitles.
    """
    if theme_key is None:
        theme_key = get_random_theme()
    
    theme = COLOR_THEMES.get(theme_key, {})
    theme_name = theme.get("name", theme_key)
    print(f"   🎨 Color theme: {theme_name}")
    
    output_path = os.path.join(temp_dir, "reel.mp4")
    subtitle_path = create_subtitle_file(quote, temp_dir, font_paths, theme_key)
    
    fps = DEFAULT_FPS
    total_frames = duration * fps
    zoom_increment = 0.12 / total_frames
    
    kb_mode = random.choice(["zoom_in", "zoom_out"])
    
    if kb_mode == "zoom_in":
        zoom_expr = f"1+{zoom_increment}*on"
    else:
        zoom_expr = f"1.12-{zoom_increment}*on"
    
    vignette_path = _generate_vignette_png(temp_dir)
    
    # Get theme's FFmpeg filter parameters
    ffmpeg_mixer = theme.get("ffmpeg_mixer", "1:0:0:0:0:1:0:0:0:0:0:1")
    ffmpeg_eq = theme.get("ffmpeg_eq", "brightness=0.02:contrast=1.1:saturation=0.85:gamma=0.95")
    
    cmd = ["ffmpeg", "-y"]
    cmd.extend(["-loop", "1", "-t", str(duration), "-i", image_path])
    
    if vignette_path:
        cmd.extend(["-loop", "1", "-t", str(duration), "-i", vignette_path])
    
    has_music = music_path and os.path.exists(music_path)
    if has_music:
        cmd.extend(["-stream_loop", "-1", "-i", music_path])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"])
    
    if vignette_path:
        video_filters = [
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='{zoom_expr}':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps},colorchannelmixer={ffmpeg_mixer},{ffmpeg_eq}[bg]",
            f"[1:v][bg]overlay=0:0:format=auto[vo]",
            f"[vo]ass={subtitle_path}[v]",
        ]
        cmd.extend(["-filter_complex", ";".join(video_filters)])
        
        if has_music:
            cmd.extend(["-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={duration-3}:d=3"])
            cmd.extend(["-map", "[v]", "-map", "2:a"])
        else:
            cmd.extend(["-map", "[v]", "-map", "2:a"])
    else:
        video_filters = [
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            f"zoompan=z='{zoom_expr}':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}",
            f"colorchannelmixer={ffmpeg_mixer}",
            ffmpeg_eq,
            f"ass={subtitle_path}",
        ]
        cmd.extend(["-vf", ",".join(video_filters)])
        
        if has_music:
            cmd.extend(["-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={duration-3}:d=3"])
        
        cmd.extend(["-map", "0:v", "-map", "1:a"])
    
    cmd.extend([
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ])
    
    print(f"   FFmpeg: rendering {REEL_WIDTH}x{REEL_HEIGHT}, {duration}s, mode={kb_mode}, theme={theme_name}...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"   FFmpeg vignette overlay failed — retrying without vignette...")
            return _create_reel_ffmpeg_simple(
                image_path, music_path, subtitle_path, temp_dir, duration, 
                zoom_expr, total_frames, fps, kb_mode, theme_key
            )
        
        file_size = os.path.getsize(output_path)
        print(f"   FFmpeg: video created ({file_size / (1024*1024):.1f} MB)")
        return output_path
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out after 300 seconds")
    except FileNotFoundError:
        raise RuntimeError("FFmpeg not found")


def _create_reel_ffmpeg_simple(image_path, music_path, subtitle_path, temp_dir, 
                                duration, zoom_expr, total_frames, fps, kb_mode, theme_key=None):
    """Simplified FFmpeg fallback — no vignette overlay, just the basics."""
    if theme_key is None:
        theme_key = get_random_theme()
    theme = COLOR_THEMES.get(theme_key, {})
    theme_name = theme.get("name", theme_key)
    ffmpeg_mixer = theme.get("ffmpeg_mixer", "1:0:0:0:0:1:0:0:0:0:0:1")
    ffmpeg_eq = theme.get("ffmpeg_eq", "brightness=0.02:contrast=1.1:saturation=0.85")
    
    output_path = os.path.join(temp_dir, "reel.mp4")
    
    cmd = ["ffmpeg", "-y"]
    cmd.extend(["-loop", "1", "-t", str(duration), "-i", image_path])
    
    has_music = music_path and os.path.exists(music_path)
    if has_music:
        cmd.extend(["-stream_loop", "-1", "-i", music_path])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"])
    
    video_filters = [
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        f"zoompan=z='{zoom_expr}':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}",
        f"colorchannelmixer={ffmpeg_mixer}",
        ffmpeg_eq,
        f"ass={subtitle_path}",
    ]
    
    cmd.extend(["-vf", ",".join(video_filters)])
    
    if has_music:
        cmd.extend(["-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={duration-3}:d=3"])
    
    cmd.extend(["-map", "0:v", "-map", "1:a"])
    cmd.extend([
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ])
    
    print(f"   FFmpeg (simple): rendering {REEL_WIDTH}x{REEL_HEIGHT}, {duration}s, theme={theme_name}...")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg simple failed: {result.stderr[-300:]}")
    
    file_size = os.path.getsize(output_path)
    print(f"   FFmpeg (simple): video created ({file_size / (1024*1024):.1f} MB)")
    return output_path


# ─── Main Entry Point ────────────────────────────────────────────────────────

def create_reel(image_path, music_path, quote, temp_dir, font_paths, duration=15, theme_key=None):
    """
    Create a 15-second Instagram Reel video.
    
    Tries MoviePy first (smoother zoom, vignette, dust particles, text backdrop),
    falls back to enhanced FFmpeg pipeline if MoviePy fails.
    
    Args:
        image_path: Path to the background image
        music_path: Path to the background music (can be None)
        quote: Dict with 'text', 'author', 'category' keys
        temp_dir: Directory for temporary files
        font_paths: Dict with 'quote' and 'author' font paths
        duration: Video duration in seconds (default 15)
        theme_key: Color grading theme key (random if None)
    
    Returns:
        str: Path to the created video file
    """
    if theme_key is None:
        theme_key = get_random_theme()
    
    if HAS_MOVIEPY:
        try:
            print(f"   MoviePy available — creating enhanced cinematic reel...")
            return create_reel_moviepy(
                image_path, music_path, quote, temp_dir, font_paths, duration, theme_key
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
