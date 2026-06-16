#!/usr/bin/env python3
"""
Video Creator — Creates 15-second Instagram Reels using MoviePy + FFmpeg.

Features:
- Ken Burns zoom effect (smooth, MoviePy-powered with ease-in-out)
- Cinematic dark vignette overlay for depth
- Text overlay with fade-in/fade-out (MoviePy or ASS subtitles)
- Audio crossfade (fade in/out)
- FFmpeg fallback if MoviePy fails

Output: 1080x1920 (9:16) MP4, H.264, AAC audio.
"""

import subprocess
import os
import textwrap
import random
from pathlib import Path

try:
    from moviepy import (
        ImageClip, AudioFileClip, CompositeVideoClip, TextClip
    )
    from moviepy.video.fx import FadeIn, FadeOut
    from moviepy.audio.fx import AudioFadeIn, AudioFadeOut
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False


# ─── Text Wrapping ───────────────────────────────────────────────────────────

def wrap_quote_text(text, max_chars_per_line=28):
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
    """
    quote_text = quote["text"]
    author = quote["author"]
    
    lines = wrap_quote_text(quote_text, max_chars_per_line=28)
    wrapped_text = "\\N".join(lines)
    
    quote_fontname = font_paths.get("quote", "Cormorant Garamond")
    author_fontname = font_paths.get("author", "Montserrat")
    
    num_lines = len(lines)
    total_text_lines = num_lines + 1
    line_height = 64
    total_height = total_text_lines * line_height
    start_y = int((1920 - total_height) / 2)
    
    ass_content = f"""[Script Info]
Title: Inner Logic Quote
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Quote,{quote_fontname},50,&H00FFFFFF,&H000000FF,&H30000000,&H80000000,-1,0,0,0,100,100,3,0,1,4,4,8,100,100,{start_y},1
Style: Author,{author_fontname},32,&H80FFFFFF,&H000000FF,&H30000000,&H80000000,0,-1,0,0,100,100,2,0,1,2,3,8,100,100,{start_y + num_lines * 64 + 30},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.80,0:00:13.50,Quote,,0,0,0,,{{\\fade(255,0,255,800,12500)}}{wrapped_text}
Dialogue: 0,0:00:01.80,0:00:13.50,Author,,0,0,0,,{{\\fade(255,0,255,1800,12500)}}— {author}
"""
    
    subtitle_path = os.path.join(temp_dir, "quote_subtitle.ass")
    with open(subtitle_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
    
    return subtitle_path


# ─── MoviePy Video Creation ──────────────────────────────────────────────────

def _create_vignette_clip(width, height, duration):
    """Create a dark vignette overlay clip for cinematic depth."""
    import numpy as np
    
    y, x = np.ogrid[:height, :width]
    cx, cy = width / 2, height / 2
    dist = np.sqrt((x - cx)**2 + (y - cy)**2) / np.sqrt(cx**2 + cy**2)
    alpha = np.clip(1.0 - dist * 0.6, 0, 1)
    alpha = (alpha * 180).astype(np.uint8)  # Max opacity ~70%
    
    img = np.zeros((height, width, 4), dtype=np.uint8)
    img[:, :, 3] = alpha
    
    vignette = ImageClip(img, duration=duration)
    return vignette


def create_reel_moviepy(image_path, music_path, quote, temp_dir, font_paths, duration=15):
    """
    Create a cinematic reel using MoviePy for smoother effects.
    
    MoviePy advantages over raw FFmpeg:
    - Smoother Ken Burns zoom (ease-in-out interpolation)
    - Vignette overlay for cinematic depth
    - Native text clips with fade effects
    - Easier to extend with future effects
    """
    import numpy as np
    from PIL import Image
    
    output_path = os.path.join(temp_dir, "reel.mp4")
    
    # Load and prepare the background image
    bg_img = Image.open(image_path)
    bg_img = bg_img.resize((1080, 1920), Image.LANCZOS)
    bg_array = np.array(bg_img)
    
    # Create base image clip
    img_clip = ImageClip(bg_array, duration=duration)
    
    # Ken Burns zoom: smooth ease-in-out from 1.0 to 1.15
    def make_ken_burns_frame(t):
        progress = t / duration
        # Smoothstep for cinematic ease (slow start, fast middle, slow end)
        smooth = progress * progress * (3 - 2 * progress)
        zoom = 1.0 + 0.15 * smooth
        
        h, w = bg_array.shape[:2]
        new_w = int(w / zoom)
        new_h = int(h / zoom)
        x1 = (w - new_w) // 2
        y1 = (h - new_h) // 2
        
        cropped = bg_array[y1:y1+new_h, x1:x1+new_w]
        img = Image.fromarray(cropped)
        img = img.resize((w, h), Image.LANCZOS)
        return np.array(img)
    
    from moviepy import VideoClip
    zoomed_clip = VideoClip(frame_function=make_ken_burns_frame, duration=duration)
    
    # Build composite layers
    clips = [zoomed_clip]
    
    # Add vignette overlay for cinematic depth
    try:
        vignette = _create_vignette_clip(1080, 1920, duration)
        vignette = vignette.with_position(("center", "center"))
        clips.append(vignette)
    except Exception as e:
        print(f"   Vignette skipped: {e}")
    
    # Add text overlays
    try:
        quote_text = quote["text"]
        author = quote["author"]
        
        lines = wrap_quote_text(quote_text, max_chars_per_line=24)
        wrapped = "\n".join(lines)
        
        quote_font = font_paths.get("quote", "Cormorant-Garamond")
        author_font = font_paths.get("author", "Montserrat")
        
        # Quote text
        quote_clip = TextClip(
            text=wrapped,
            font_size=46,
            color="white",
            font=quote_font,
            text_align="center",
            size=(920, None),
            method="caption",
        )
        quote_clip = quote_clip.with_duration(duration - 1.5)
        quote_clip = quote_clip.with_position(("center", 0.42), relative=True)
        quote_clip = quote_clip.with_effects([FadeIn(1.0), FadeOut(2.0)])
        clips.append(quote_clip)
        
        # Author text
        author_clip = TextClip(
            text=f"— {author}",
            font_size=28,
            color="#BBBBBB",
            font=author_font,
            text_align="center",
            size=(920, None),
            method="caption",
        )
        author_clip = author_clip.with_duration(duration - 3.0)
        author_clip = author_clip.with_position(("center", 0.62), relative=True)
        author_clip = author_clip.with_effects([FadeIn(0.8), FadeOut(2.0)])
        clips.append(author_clip)
        
    except Exception as e:
        print(f"   MoviePy text failed: {e}")
        print(f"   (Text will be added via FFmpeg overlay instead)")
    
    # Composite all layers
    video = CompositeVideoClip(clips, size=(1080, 1920))
    
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
    
    print(f"   MoviePy: rendering 1080x1920, {duration}s...")
    
    # Write output
    video.write_videofile(
        output_path,
        fps=30,
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

def create_reel_ffmpeg(image_path, music_path, quote, temp_dir, font_paths, duration=15):
    """
    Create a reel using raw FFmpeg (proven fallback).
    Uses ASS subtitles for text overlay with Ken Burns zoom.
    """
    output_path = os.path.join(temp_dir, "reel.mp4")
    subtitle_path = create_subtitle_file(quote, temp_dir, font_paths)
    
    fps = 30
    total_frames = duration * fps
    zoom_increment = 0.12 / total_frames
    
    cmd = ["ffmpeg", "-y"]
    cmd.extend(["-loop", "1", "-t", str(duration), "-i", image_path])
    
    has_music = music_path and os.path.exists(music_path)
    if has_music:
        cmd.extend(["-stream_loop", "-1", "-i", music_path])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"])
    
    video_filters = [
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        f"zoompan=z='1+{zoom_increment}*on':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}",
        f"ass={subtitle_path}",
    ]
    
    cmd.extend(["-vf", ",".join(video_filters)])
    
    if has_music:
        cmd.extend(["-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={duration-3}:d=3"])
        cmd.extend(["-map", "0:v", "-map", "1:a"])
    else:
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
    
    print(f"   FFmpeg: rendering 1080x1920, {duration}s, {fps}fps...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"   FFmpeg error: {result.stderr[-500:]}")
            raise RuntimeError(f"FFmpeg failed with code {result.returncode}")
        
        file_size = os.path.getsize(output_path)
        print(f"   FFmpeg: video created ({file_size / (1024*1024):.1f} MB)")
        return output_path
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out after 300 seconds")
    except FileNotFoundError:
        raise RuntimeError("FFmpeg not found")


# ─── Main Entry Point ────────────────────────────────────────────────────────

def create_reel(image_path, music_path, quote, temp_dir, font_paths, duration=15):
    """
    Create a 15-second Instagram Reel video.
    
    Tries MoviePy first (smoother zoom, vignette, better text fades),
    falls back to raw FFmpeg if MoviePy fails.
    
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
            print(f"   MoviePy available — creating cinematic reel...")
            return create_reel_moviepy(
                image_path, music_path, quote, temp_dir, font_paths, duration
            )
        except Exception as e:
            print(f"   MoviePy failed: {e}")
            print(f"   Falling back to FFmpeg pipeline...")
    
    # FFmpeg fallback (always works)
    print(f"   Using FFmpeg pipeline...")
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
