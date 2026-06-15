#!/usr/bin/env python3
"""
Instagram Poster — Publishes reels to Instagram using instagrapi.
No Facebook/Meta Developer account needed. No API tokens needed.
Just uses your Instagram username and password directly.

instagrapi simulates the Instagram app login, which is why it works
without the official API. This is used by thousands of automation tools.
"""

import os
import time
import json
import random
from pathlib import Path


def login(username, password):
    """
    Login to Instagram using instagrapi.
    Handles 2FA if enabled (via environment variable).
    
    Args:
        username: Instagram username
        password: Instagram password
    
    Returns:
        Client: Authenticated instagrapi Client
    """
    from instagrapi import Client
    
    cl = Client()
    
    # Randomize user agent to avoid detection
    cl.set_settings({
        "device_settings": {
            "app_version": "269.0.0.18.75",
            "android_version": 26,
            "android_release": "8.0.0",
            "dpi": "480dpi",
            "resolution": "1080x1920",
            "manufacturer": "OnePlus",
            "device": "ONEPLUS A3003",
            "model": "OnePlus3",
            "cpu": "qcom",
            "version_code": "314665256",
        },
        "user_agent": "Instagram 269.0.0.18.75 Android (26/8.0.0; 480dpi; 1080x1920; OnePlus; ONEPLUS A3003; OnePlus3; qcom; en_US; 314665256)"
    })
    
    # Try to load session from file (avoids re-login every time)
    session_file = os.path.join(os.path.dirname(__file__), "..", "data", "ig_session.json")
    session_file = os.path.abspath(session_file)
    
    if os.path.exists(session_file):
        try:
            cl.load_settings(session_file)
            cl.login(username, password)
            cl.get_timeline_feed()  # Test if session is valid
            print("   ✅ Logged in using saved session")
            return cl
        except Exception:
            print("   ⚠️  Saved session expired — re-logging in...")
    
    # Fresh login
    try:
        # Check for 2FA code
        verification_code = os.environ.get("INSTAGRAM_2FA_CODE", "")
        totp_secret = os.environ.get("INSTAGRAM_TOTP_SECRET", "")
        
        if totp_secret:
            # Generate TOTP code from secret
            try:
                import pyotp
                verification_code = pyotp.TOTP(totp_secret).now()
                print(f"   🔐 Generated 2FA code from TOTP secret")
            except ImportError:
                print("   ⚠️  pyotp not installed — cannot generate 2FA code")
        
        cl.login(username, password, verification_code=verification_code)
        
        # Save session for next time
        os.makedirs(os.path.dirname(session_file), exist_ok=True)
        cl.dump_settings(session_file)
        
        print("   ✅ Logged in successfully")
        return cl
        
    except Exception as e:
        error_msg = str(e)
        
        if "challenge" in error_msg.lower():
            print("   ⚠️  Instagram requires verification (challenge)")
            print("   📱 Check your email/phone for a verification code")
            _handle_challenge(cl, username, password)
            cl.dump_settings(session_file)
            return cl
        
        elif "two_factor" in error_msg.lower():
            print("   ⚠️  2FA is enabled on your account")
            print("   📱 You need to set INSTAGRAM_TOTP_SECRET in GitHub Secrets")
            raise RuntimeError(
                "Two-factor authentication is enabled. "
                "Set the INSTAGRAM_TOTP_SECRET environment variable with your 2FA secret key. "
                "You can find this in your authenticator app setup."
            )
        
        else:
            raise RuntimeError(f"Login failed: {error_msg}")


def _handle_challenge(cl, username, password):
    """Handle Instagram's challenge/verification requirement."""
    try:
        challenge_url = cl.challenge_url
        if challenge_url:
            print(f"   🔗 Challenge URL: {challenge_url}")
        
        # Try to send challenge code via email
        cl.challenge_resolve(cl.last_json)
        
        # Wait for user to enter code (not ideal for automation)
        # In GitHub Actions, this will fail — user needs to handle it manually
        print("   ❌ Challenge required — cannot handle automatically in CI/CD")
        print("   💡 Try logging in manually first, then re-run the pipeline")
        raise RuntimeError("Instagram challenge required — login manually first")
        
    except Exception as e:
        raise RuntimeError(f"Challenge handling failed: {e}")


def upload_reel(cl, video_path, caption):
    """
    Upload a reel to Instagram using instagrapi.
    
    Args:
        cl: Authenticated instagrapi Client
        video_path: Path to the video file
        caption: Caption text with hashtags
    
    Returns:
        dict: Upload result with media ID
    """
    from instagrapi import Client
    
    print("   📤 Uploading reel to Instagram...")
    
    try:
        # Upload the reel
        media = cl.clip_upload(
            path=video_path,
            caption=caption,
            # Extra data for better compatibility
            extra_data={
                "source_type": "4",  # Camera
                "delivery_class": "organic",
                "upload_id": str(int(time.time() * 1000)),
            }
        )
        
        if media:
            print(f"   ✅ Reel uploaded! Media ID: {media.pk}")
            print(f"   🔗 Code: {media.code}")
            return {
                "id": media.pk,
                "code": media.code,
                "status": "uploaded",
            }
        else:
            raise RuntimeError("Upload returned no media object")
            
    except Exception as e:
        error_msg = str(e)
        
        if "rate_limit" in error_msg.lower():
            raise RuntimeError(
                "Rate limited by Instagram — wait a few hours before trying again"
            )
        elif "login" in error_msg.lower() or "auth" in error_msg.lower():
            raise RuntimeError(
                "Authentication error — session may have expired. "
                "Try deleting the session file and re-running."
            )
        else:
            raise RuntimeError(f"Upload failed: {error_msg}")


def post_reel(access_token=None, ig_business_account_id=None, 
              video_url=None, caption=None, video_path=None):
    """
    Post a reel to Instagram.
    
    This is the main interface function that matches the pipeline's API.
    With instagrapi, we use username/password login instead of access tokens.
    
    Args:
        access_token: Ignored (kept for compatibility)
        ig_business_account_id: Ignored (kept for compatibility)
        video_url: Ignored (kept for compatibility, we use local file)
        caption: Instagram caption with hashtags
        video_path: Local path to the video file
    
    Returns:
        dict: Result with media ID
    """
    username = os.environ.get("INSTAGRAM_USERNAME", "")
    password = os.environ.get("INSTAGRAM_PASSWORD", "")
    
    if not username or not password:
        raise ValueError(
            "INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables are required"
        )
    
    if not video_path and video_url:
        # If only URL is provided, download the video first
        print("   📥 Downloading video from URL...")
        import requests
        response = requests.get(video_url, timeout=120)
        temp_path = os.path.join(os.path.dirname(__file__), "..", "temp", "downloaded.mp4")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(response.content)
        video_path = temp_path
    
    if not video_path or not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Login
    print(f"   🔑 Logging in as @{username}...")
    cl = login(username, password)
    
    # Upload
    result = upload_reel(cl, video_path, caption)
    
    # Random delay after upload to look natural
    delay = random.uniform(2, 5)
    time.sleep(delay)
    
    return result


if __name__ == "__main__":
    print("This module is used by main.py. Run main.py instead.")
