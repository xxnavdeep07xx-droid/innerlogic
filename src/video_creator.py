#!/usr/bin/env python3
"""
Video Creator — Creates 15-second Instagram Reels using FFmpeg.
Combines background image (with Ken Burns zoom), quote text overlay, and music.
Output: 1080x1920 (9:16) MP4, H.264, AAC audio.
"""

import subprocess
import os
import textwrap
import random
from pathlib import Path


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


def create_subtitle_file(quote, temp_dir, fonts_dir):
    """
    Create an ASS (Advanced SubStation Alpha) subtitle file
    for the quote text overlay with fade-in/fade-out animation.
    """
    quote_text = quote["text"]
    author = quote["author"]
    
    # Wrap the quote text
    lines = wrap_quote_text(quote_text, max_chars_per_line=28)
    wrapped_text = "\\N".join(lines)  # \N is ASS newline
    
    # Determine font path
    font_name = "PlayfairDisplay-Regular"
    font_italic = "PlayfairDisplay-Italic"
    
    # Check if custom fonts exist
    regular_font = os.path.join(fonts_dir, f"{font_name}.ttf")
    italic_font = os.path.join(fonts_dir, f"{font_italic}.ttf")
    
    if os.path.exists(regular_font):
        quote_fontname = regular_font
    else:
        quote_fontname = "Playfair Display"
    
    if os.path.exists(italic_font):
        author_fontname = italic_font
    else:
        author_fontname = "Playfair Display"
    
    # Calculate vertical position based on number of lines
    num_lines = len(lines)
    # Center vertically, accounting for author line
    total_text_lines = num_lines + 1  # quote lines + author line
    line_height = 60  # pixels between lines
    total_height = total_text_lines * line_height
    start_y = int((1920 - total_height) / 2)
    
    # Build ASS subtitle content
    ass_content = f"""[Script Info]
Title: Inner Logic Quote
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Quote,{quote_fontname},48,&H00FFFFFF,&H000000FF,&H40000000,&HC0000000,-1,0,0,0,100,100,2,0,1,3,3,8,80,80,{start_y},1
Style: Author,{author_fontname},34,&H90FFFFFF,&H000000FF,&H40000000,&HC0000000,-1,-1,0,0,100,100,2,0,1,2,2,8,80,80,{start_y + num_lines * 60 + 20},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.80,0:00:13.50,Quote,,0,0,0,,{{\\fade(255,0,255,800,12500)}}{wrapped_text}
Dialogue: 0,0:00:01.80,0:00:13.50,Author,,0,0,0,,{{\\fade(255,0,255,1800,12500)}}— {author}
"""
    
    subtitle_path = os.path.join(temp_dir, "quote_subtitle.ass")
    with open(subtitle_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
    
    return subtitle_path


def create_reel(image_path, music_path, quote, temp_dir, fonts_dir, duration=15):
    """
    Create a 15-second Instagram Reel video.
    
    Args:
        image_path: Path to the background image
        music_path: Path to the background music (can be None)
        quote: Dict with 'text', 'author', 'category' keys
        temp_dir: Directory for temporary files
        fonts_dir: Directory containing font files
        duration: Video duration in seconds (default 15)
    
    Returns:
        str: Path to the created video file
    """
    output_path = os.path.join(temp_dir, "reel.mp4")
    subtitle_path = create_subtitle_file(quote, temp_dir, fonts_dir)
    
    # Calculate Ken Burns zoom parameters
    # Slow zoom from 1.0 to 1.12 over the duration
    fps = 30
    total_frames = duration * fps
    zoom_increment = 0.12 / total_frames  # ~0.000267 per frame
    
    # Build FFmpeg command
    cmd = ["ffmpeg", "-y"]
    
    # Input 1: Background image (looped for the full duration)
    cmd.extend(["-loop", "1", "-t", str(duration), "-i", image_path])
    
    # Input 2: Music (if available) — loop it if shorter than duration
    has_music = music_path and os.path.exists(music_path)
    if has_music:
        cmd.extend(["-stream_loop", "-1", "-i", music_path])
    
    # Video filters
    video_filters = [
        # Scale image to fit 1080x1920
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        # Ken Burns effect: slow zoom in, centered
        f"zoompan=z='1+{zoom_increment}*on':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}",
        # Subtitle overlay (quote text with fade animation)
        f"ass={subtitle_path}",
    ]
    
    cmd.extend(["-vf", ",".join(video_filters)])
    
    if has_music:
        # Audio filters: fade in/out, limit to duration
        cmd.extend(["-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={duration-3}:d=3"])
        cmd.extend(["-map", "0:v", "-map", "1:a"])
    else:
        # No music — add silent audio track (Instagram requires audio)
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"])
        cmd.extend(["-map", "0:v", "-map", "2:a"])
    
    # Output settings — explicitly set duration, NO -shortest
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
    
    print(f"   🔧 Running FFmpeg...")
    print(f"   📐 Resolution: 1080x1920 | Duration: {duration}s | FPS: {fps}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            print(f"   ❌ FFmpeg stderr: {result.stderr[-500:]}")
            raise RuntimeError(f"FFmpeg failed with code {result.returncode}")
        
        file_size = os.path.getsize(output_path)
        print(f"   ✅ Video created ({file_size / (1024*1024):.1f} MB)")
        
        return output_path
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out after 300 seconds")
    except FileNotFoundError:
        raise RuntimeError("FFmpeg not found — make sure it's installed")


if __name__ == "__main__":
    test_quote = {
        "text": "The only way to deal with an unfree world is to become so absolutely free that your very existence is an act of rebellion.",
        "author": "Albert Camus",
        "category": "existentialism"
    }
    print("This module requires FFmpeg and proper setup to test.")
    print("Run main.py instead for the full pipeline.")
