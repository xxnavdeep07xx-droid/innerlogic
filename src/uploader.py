#!/usr/bin/env python3
"""
DEPRECATED — This module is no longer used by the pipeline.
With instagrapi, videos are uploaded directly from the local file.
No public URL is needed anymore. This file is kept for reference only.

Uploader — Uploads video to temporary file hosting for Instagram API access.
Instagram requires a publicly accessible video URL for reel publishing.
Uses multiple free hosting services with fallbacks.
"""

import requests
import os
import time


def upload_to_fileio(file_path):
    """
    Upload to file.io — free, simple, auto-deletes after download.
    Perfect for Instagram's one-time download requirement.
    """
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://file.io",
                files={"file": f},
                data={"expires": "1d"},  # Auto-delete after 1 day
                timeout=120
            )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("link"):
                print(f"   ✅ Uploaded to file.io")
                return data["link"]
        
        print(f"   ⚠️  file.io upload failed: {response.text[:200]}")
        
    except Exception as e:
        print(f"   ⚠️  file.io error: {e}")
    
    return None


def upload_to_0x0st(file_path):
    """
    Upload to 0x0.st — free, simple, no-registration file hosting.
    """
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://0x0.st",
                files={"file": f},
                timeout=120
            )
        
        if response.status_code == 200:
            url = response.text.strip()
            if url.startswith("https://"):
                print(f"   ✅ Uploaded to 0x0.st")
                return url
        
        print(f"   ⚠️  0x0.st upload failed: {response.text[:200]}")
        
    except Exception as e:
        print(f"   ⚠️  0x0.st error: {e}")
    
    return None


def upload_to_catbox(file_path):
    """
    Upload to catbox.moe — free, reliable, no-registration file hosting.
    """
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=120
            )
        
        if response.status_code == 200:
            url = response.text.strip()
            if url.startswith("https://"):
                print(f"   ✅ Uploaded to catbox.moe")
                return url
        
        print(f"   ⚠️  catbox.moe upload failed: {response.text[:200]}")
        
    except Exception as e:
        print(f"   ⚠️  catbox.moe error: {e}")
    
    return None


def upload_video(file_path):
    """
    Upload video to temporary file hosting.
    Tries multiple services with fallbacks.
    
    Args:
        file_path: Path to the video file to upload
    
    Returns:
        str: Public URL of the uploaded video
    
    Raises:
        RuntimeError: If all upload methods fail
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Video file not found: {file_path}")
    
    file_size = os.path.getsize(file_path)
    print(f"   📤 Uploading video ({file_size / (1024*1024):.1f} MB)...")
    
    # Try each upload service in order
    upload_methods = [
        ("file.io", upload_to_fileio),
        ("catbox.moe", upload_to_catbox),
        ("0x0.st", upload_to_0x0st),
    ]
    
    for name, method in upload_methods:
        print(f"   🔗 Trying {name}...")
        url = method(file_path)
        if url:
            return url
        time.sleep(2)  # Brief pause between attempts
    
    # All methods failed
    raise RuntimeError(
        "All upload methods failed! The video could not be hosted publicly. "
        "Instagram requires a publicly accessible video URL to publish reels."
    )


if __name__ == "__main__":
    # Quick test
    import sys
    if len(sys.argv) > 1:
        url = upload_video(sys.argv[1])
        print(f"Video URL: {url}")
    else:
        print("Usage: python uploader.py <video_file_path>")
