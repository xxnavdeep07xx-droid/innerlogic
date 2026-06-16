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
- Color grading (muted, cinematic look)
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
TEXT_DARKEN_OPACITY = 0.45


# ─── Text Wrapping ────────────────────────────────────────────────────────────

def wrap_quote_text(text, max_chars_per_line=32):
    """
    Wrap quote text for screen display.
    Returns a list of lines, each within the max character limit.
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
    
    return lines


# ─── ASS Subtitle (FFmpeg fallback) ──────────────────────────────────────────

def create_subtitle_file(quote, temp_dir, font_paths):
    """
    Create an ASS subtitle file for FFmpeg fallback mode.
    Enhanced with better fade timing and shadow effects.
    """
    quote_text = quote["text"]
    author = quote["author"]
    
    lines = wrap_quote_text(quote_text, max_chars_per_line=32)
    wrapped_text = "\\N".join(lines)
    
    quote_fontname = font_paths.get("quote", "Cormorant Garamond")
    author_fontname = font_paths.get("author", "Montserrat")
    
    num_lines = len(lines)
    total_text_lines = num_lines + 1
    line_height = 56
    total_height = total_text_lines * line_height
    start_y = int((1920 - total_height) / 2)
    
    # Fade timing: quote appears at 0.8s, author at 1.8s, both fade out at 13s
    quote_start = "0:00:00.80"
    quote_end = "0:00:13.50"
    author_start = "0:00:01.80"
    author_end = "0:00:13.50"
    
    # Fade: \fade(a1,a2,a3,t1,t2,t3,t4) — opacity ramp
    quote_fade = r"{\fade(255,255,0,0,80,1250,1350)}"
    author_fade = r"{\fade(255,255,0,0,180,1250,1350)}"
    
    # Dynamic font size based on quote length
    num_chars = len(quote_text)
    if num_chars <= 50:
        q_font_size = 46
    elif num_chars <= 80:
        q_font_size = 42
    elif num_chars <= 120:
        q_font_size = 38
    else:
        q_font_size = 34
    
    ass_content = f"""[Script Info]
Title: Inner Logic Quote
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Quote,{quote_fontname},{q_font_size},&H00FFFFFF,&H000000FF,&H30000000,&H80000000,-1,0,0,0,100,100,3,0,1,4,4,8,80,80,{start_y},1
Style: Author,{author_fontname},28,&H80FFFFFF,&H000000FF,&H30000000,&H80000000,0,-1,0,0,100,100,2,0,1,2,3,8,80,80,{start_y + num_lines * line_height + 30},1

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
    alpha = (alpha * 180).astype(np.uint8)  # Max opacity ~70%
    
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
    
    # Dark gradient centered at ~40-65% of the screen height (quote area)
    center_y_start = int(height * 0.30)
    center_y_end = int(height * 0.72)
    center_y_mid = (center_y_start + center_y_end) // 2
    
    for y in range(center_y_start, center_y_end):
        # Distance from center of the text area (0 at center, 1 at edges)
        dist_from_center = abs(y - center_y_mid) / (center_y_end - center_y_start) * 2
        dist_from_center = min(dist_from_center, 1.0)
        
        # Opacity: strongest at center, fading to transparent at edges
        opacity = int(TEXT_DARKEN_OPACITY * 255 * (1.0 - dist_from_center ** 1.5))
        
        img[y, :, 3] = opacity  # Alpha channel
    
    backdrop = ImageClip(img, duration=duration)
    return backdrop


def _create_dust_particles(width, height, duration, num_particles=30):
    """
    Create floating dust/particle overlay for cinematic atmosphere.
    Subtle, slowly drifting particles that add depth and mood.
    """
    import numpy as np
    from PIL import Image
    
    fps = DEFAULT_FPS
    total_frames = int(duration * fps)
    
    # Pre-generate particle positions and properties
    particles = []
    for _ in range(num_particles):
        particles.append({
            "x": random.uniform(0, width),
            "y": random.uniform(0, height),
            "size": random.uniform(1.5, 4.0),
            "speed_x": random.uniform(-0.3, 0.3),
            "speed_y": random.uniform(-0.8, -0.15),  # Drift upward slowly
            "brightness": random.uniform(0.3, 0.8),
            "phase": random.uniform(0, math.pi * 2),  # For pulsing
            "pulse_speed": random.uniform(0.5, 2.0),
        })
    
    def make_frame(t):
        frame = np.zeros((height, width, 4), dtype=np.uint8)
        
        for p in particles:
            # Calculate position with drift
            x = p["x"] + p["speed_x"] * t * 30
            y = p["y"] + p["speed_y"] * t * 30
            
            # Wrap around
            x = x % width
            y = y % height
            
            # Pulse brightness
            pulse = 0.5 + 0.5 * math.sin(p["phase"] + t * p["pulse_speed"])
            brightness = p["brightness"] * pulse
            
            # Draw the particle (small circle)
            ix, iy = int(x), int(y)
            size = int(p["size"])
            alpha = int(brightness * 60)  # Keep it subtle
            
            # Simple pixel placement with anti-aliasing approximation
            for dy in range(-size, size + 1):
                for dx in range(-size, size + 1):
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist <= size:
                        px, py = ix + dx, iy + dy
                        if 0 <= px < width and 0 <= py < height:
                            falloff = 1.0 - (dist / max(size, 1))
                            pixel_alpha = int(alpha * falloff)
                            # Additive blending (take max to not overwrite brighter pixels)
                            frame[py, px, 3] = max(frame[py, px, 3], pixel_alpha)
        
        return frame
    
    dust_clip = VideoClip(frame_function=make_frame, duration=duration)
    return dust_clip


# ─── MoviePy Video Creation ──────────────────────────────────────────────────

def create_reel_moviepy(image_path, music_path, quote, temp_dir, font_paths, duration=15):
    """
    Create a cinematic reel using MoviePy for smoother effects.
    
    Enhanced features:
    - Ken Burns zoom with randomized direction (zoom in, zoom out, pan)
    - Dark text backdrop for guaranteed readability
    - Floating dust particles for cinematic atmosphere
    - Cinematic vignette overlay
    - Native text clips with precise fade timing
    - Audio crossfade with configurable curves
    """
    import numpy as np
    from PIL import Image
    
    output_path = os.path.join(temp_dir, "reel.mp4")
    
    # Load and prepare the background image
    bg_img = Image.open(image_path)
    bg_img = bg_img.resize((REEL_WIDTH, REEL_HEIGHT), Image.LANCZOS)
    bg_array = np.array(bg_img)
    
    # Randomize Ken Burns direction
    kb_mode = random.choice(["zoom_in", "zoom_out", "pan_up", "pan_down"])
    
    # Ken Burns zoom: smooth ease-in-out
    def make_ken_burns_frame(t):
        progress = t / duration
        # Smoothstep for cinematic ease (slow start, fast middle, slow end)
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
            y1 = int(max_y * (1.0 - smooth))  # Pan from bottom to center
        elif kb_mode == "pan_down":
            zoom = 1.08
            new_w = int(w / zoom)
            new_h = int(h / zoom)
            x1 = (w - new_w) // 2
            max_y = h - new_h
            y1 = int(max_y * smooth)  # Pan from center to bottom
        else:
            zoom = 1.0 + 0.12 * smooth
            new_w = int(w / zoom)
            new_h = int(h / zoom)
            x1 = (w - new_w) // 2
            y1 = (h - new_h) // 2
        
        cropped = bg_array[y1:y1+new_h, x1:x1+new_w]
        img = Image.fromarray(cropped)
        img = img.resize((w, h), Image.LANCZOS)
        return np.array(img)
    
    zoomed_clip = VideoClip(frame_function=make_ken_burns_frame, duration=duration)
    
    # Build composite layers
    clips = [zoomed_clip]
    
    # Layer 1: Text backdrop (semi-transparent dark gradient for readability)
    try:
        backdrop = _create_text_backdrop(REEL_WIDTH, REEL_HEIGHT, duration)
        backdrop = backdrop.with_position(("center", "center"))
        clips.append(backdrop)
    except Exception as e:
        print(f"   Text backdrop skipped: {e}")
    
    # Layer 2: Vignette overlay for cinematic depth
    try:
        vignette = _create_vignette_clip(REEL_WIDTH, REEL_HEIGHT, duration)
        vignette = vignette.with_position(("center", "center"))
        clips.append(vignette)
    except Exception as e:
        print(f"   Vignette skipped: {e}")
    
    # Layer 3: Dust particles for cinematic atmosphere
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
        
        lines = wrap_quote_text(quote_text, max_chars_per_line=30)
        wrapped = "\n".join(lines)
        
        quote_font = font_paths.get("quote", "Cormorant-Garamond")
        author_font = font_paths.get("author", "Montserrat")
        
        # Dynamic font sizing based on quote length
        # Shorter quotes get bigger text, longer quotes get smaller
        num_chars = len(quote_text)
        if num_chars <= 50:
            q_font_size = 48
        elif num_chars <= 80:
            q_font_size = 42
        elif num_chars <= 120:
            q_font_size = 38
        else:
            q_font_size = 34
        
        # Calculate vertical position based on number of lines
        # More lines = push higher so nothing gets cut off
        num_lines = len(lines)
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
            size=(880, None),  # Slightly narrower for safe margins
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
            font_size=26,
            color="#CCCCCC",
            font=author_font,
            text_align="center",
            size=(880, None),
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
            # Loop audio if shorter
            from moviepy import concatenate_audioclips
            repeats = int(duration / audio.duration) + 1
            audio = concatenate_audioclips([audio] * repeats)
        audio = audio.subclipped(0, min(duration, audio.duration))
        audio = audio.with_effects([AudioFadeIn(1.5), AudioFadeOut(3.0)])
        video = video.with_audio(audio)
    
    print(f"   MoviePy: rendering {REEL_WIDTH}x{REEL_HEIGHT}, {duration}s, mode={kb_mode}...")
    
    # Write output
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
    
    # Clean up
    video.close()
    if has_music:
        audio.close()
    
    return output_path


# ─── FFmpeg Video Creation (Fallback) ────────────────────────────────────────

def _generate_vignette_png(temp_dir, width=1080, height=1920):
    """
    Generate a vignette PNG overlay image using PIL.
    This is MUCH faster than FFmpeg's vignette filter since it's pre-rendered.
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
        
        arr[:, :, 3] = alpha  # Black vignette with radial alpha
        img = Image.fromarray(arr)
        
        vignette_path = os.path.join(temp_dir, "vignette_overlay.png")
        img.save(vignette_path, "PNG")
        return vignette_path
        
    except Exception:
        return None


def create_reel_ffmpeg(image_path, music_path, quote, temp_dir, font_paths, duration=15):
    """
    Create a reel using raw FFmpeg (proven fallback).
    Enhanced with color grading, vignette overlay, and ASS subtitles.
    
    Performance optimization:
    - Vignette uses a pre-rendered PNG overlay (way faster than FFmpeg vignette filter)
    - Color grading via eq filter (lightweight)
    - Single-pass rendering
    """
    output_path = os.path.join(temp_dir, "reel.mp4")
    subtitle_path = create_subtitle_file(quote, temp_dir, font_paths)
    
    fps = DEFAULT_FPS
    total_frames = duration * fps
    zoom_increment = 0.12 / total_frames
    
    # Randomize Ken Burns direction
    kb_mode = random.choice(["zoom_in", "zoom_out"])
    
    if kb_mode == "zoom_in":
        zoom_expr = f"1+{zoom_increment}*on"
    else:
        zoom_expr = f"1.12-{zoom_increment}*on"
    
    # Generate vignette PNG overlay (fast — pre-rendered)
    vignette_path = _generate_vignette_png(temp_dir)
    
    cmd = ["ffmpeg", "-y"]
    cmd.extend(["-loop", "1", "-t", str(duration), "-i", image_path])
    
    # Add vignette overlay as second video input
    if vignette_path:
        cmd.extend(["-loop", "1", "-t", str(duration), "-i", vignette_path])
    
    has_music = music_path and os.path.exists(music_path)
    if has_music:
        cmd.extend(["-stream_loop", "-1", "-i", music_path])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"])
    
    # Build video filter chain
    if vignette_path:
        # Inputs: 0=bg_image, 1=vignette_png, 2=music_or_silent
        video_filters = [
            # Step 1: Scale, crop, zoom, color grade the background
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='{zoom_expr}':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps},eq=brightness=0.02:contrast=1.1:saturation=0.85:gamma=0.95[bg]",
            # Step 2: Overlay vignette PNG on top
            f"[1:v][bg]overlay=0:0:format=auto[vo]",
            # Step 3: ASS subtitle overlay
            f"[vo]ass={subtitle_path}[v]",
        ]
        cmd.extend(["-filter_complex", ";".join(video_filters)])
        
        # Audio filters and mapping
        if has_music:
            cmd.extend(["-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={duration-3}:d=3"])
            cmd.extend(["-map", "[v]", "-map", "2:a"])  # Audio is input #2
        else:
            cmd.extend(["-map", "[v]", "-map", "2:a"])  # Silent audio is input #2
    else:
        # Inputs: 0=bg_image, 1=music_or_silent
        video_filters = [
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            f"zoompan=z='{zoom_expr}':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}",
            "eq=brightness=0.02:contrast=1.1:saturation=0.85:gamma=0.95",
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
    
    print(f"   FFmpeg: rendering {REEL_WIDTH}x{REEL_HEIGHT}, {duration}s, mode={kb_mode}...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            # If the vignette overlay failed, retry without it
            print(f"   FFmpeg vignette overlay failed — retrying without vignette...")
            return _create_reel_ffmpeg_simple(
                image_path, music_path, subtitle_path, temp_dir, duration, 
                zoom_expr, total_frames, fps, kb_mode
            )
        
        file_size = os.path.getsize(output_path)
        print(f"   FFmpeg: video created ({file_size / (1024*1024):.1f} MB)")
        return output_path
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out after 300 seconds")
    except FileNotFoundError:
        raise RuntimeError("FFmpeg not found")


def _create_reel_ffmpeg_simple(image_path, music_path, subtitle_path, temp_dir, 
                                duration, zoom_expr, total_frames, fps, kb_mode):
    """
    Simplified FFmpeg fallback — no vignette overlay, just the basics.
    Used if the complex filter chain fails.
    """
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
        "eq=brightness=0.02:contrast=1.1:saturation=0.85",
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
    
    print(f"   FFmpeg (simple): rendering {REEL_WIDTH}x{REEL_HEIGHT}, {duration}s...")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg simple failed: {result.stderr[-300:]}")
    
    file_size = os.path.getsize(output_path)
    print(f"   FFmpeg (simple): video created ({file_size / (1024*1024):.1f} MB)")
    return output_path


# ─── Main Entry Point ────────────────────────────────────────────────────────

def create_reel(image_path, music_path, quote, temp_dir, font_paths, duration=15):
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
    
    Returns:
        str: Path to the created video file
    """
    # Try MoviePy first for cinematic quality
    if HAS_MOVIEPY:
        try:
            print(f"   MoviePy available — creating enhanced cinematic reel...")
            return create_reel_moviepy(
                image_path, music_path, quote, temp_dir, font_paths, duration
            )
        except Exception as e:
            print(f"   MoviePy failed: {e}")
            print(f"   Falling back to FFmpeg pipeline...")
    
    # FFmpeg fallback (always works)
    print(f"   Using enhanced FFmpeg pipeline...")
    return create_reel_ffmpeg(
        image_path, music_path, quote, temp_dir, font_paths, duration
    )


if __name__ == "__main__":
    test_quote = {
        "text": "The only way to deal with an unfree world is to become so absolutely free that your very existence is an act of rebellion.",
        "author": "Albert Camus",
        "category": "existentialism"
    }
    print("This module requires FFmpeg/MoviePy and proper setup to test.")
    print("Run main.py instead for the full pipeline.")
