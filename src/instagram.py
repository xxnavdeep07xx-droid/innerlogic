#!/usr/bin/env python3
"""
Instagram Poster — Publishes reels to Instagram via the Graph API.
Uses the Content Publishing API to create and publish Reels.
"""

import requests
import time
import json


# Instagram Graph API base URL
GRAPH_API_BASE = "https://graph.facebook.com/v18.0"

# Maximum wait time for video processing (seconds)
MAX_PROCESSING_WAIT = 300  # 5 minutes


def create_media_container(access_token, ig_business_account_id, video_url, caption):
    """
    Step 1: Create a media container for the reel.
    This tells Instagram to download and process the video.
    
    Returns:
        str: Container ID for the media
    """
    url = f"{GRAPH_API_BASE}/{ig_business_account_id}/media"
    
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": access_token,
    }
    
    print("   📦 Creating media container...")
    response = requests.post(url, data=payload, timeout=60)
    
    if response.status_code != 200:
        error_data = response.json().get("error", {})
        error_msg = error_data.get("message", response.text)
        error_code = error_data.get("code", "unknown")
        raise RuntimeError(
            f"Failed to create media container (code {error_code}): {error_msg}"
        )
    
    data = response.json()
    container_id = data.get("id")
    
    if not container_id:
        raise RuntimeError(f"No container ID in response: {response.text}")
    
    print(f"   ✅ Container created: {container_id}")
    return container_id


def check_container_status(access_token, container_id):
    """
    Check the processing status of a media container.
    
    Returns:
        str: Status code (IN_PROGRESS, FINISHED, ERROR, etc.)
    """
    url = f"{GRAPH_API_BASE}/{container_id}"
    params = {
        "fields": "status_code,status",
        "access_token": access_token,
    }
    
    response = requests.get(url, params=params, timeout=30)
    
    if response.status_code != 200:
        raise RuntimeError(f"Failed to check container status: {response.text}")
    
    data = response.json()
    return data.get("status_code", "UNKNOWN")


def wait_for_processing(access_token, container_id):
    """
    Wait for Instagram to finish processing the video.
    Polls the container status every 10 seconds.
    
    Returns:
        bool: True if processing completed successfully
    """
    print("   ⏳ Waiting for Instagram to process the video...")
    
    start_time = time.time()
    
    while time.time() - start_time < MAX_PROCESSING_WAIT:
        status = check_container_status(access_token, container_id)
        
        if status == "FINISHED":
            print(f"   ✅ Video processed successfully!")
            return True
        elif status == "ERROR":
            # Get error details
            url = f"{GRAPH_API_BASE}/{container_id}"
            params = {"fields": "status", "access_token": access_token}
            response = requests.get(url, params=params, timeout=30)
            error_details = response.json()
            raise RuntimeError(
                f"Video processing failed: {json.dumps(error_details, indent=2)}"
            )
        elif status == "IN_PROGRESS":
            elapsed = int(time.time() - start_time)
            print(f"   ⏳ Still processing... ({elapsed}s elapsed)")
        else:
            print(f"   ⚠️  Unknown status: {status}")
        
        time.sleep(10)
    
    raise RuntimeError(
        f"Video processing timed out after {MAX_PROCESSING_WAIT} seconds"
    )


def publish_reel(access_token, ig_business_account_id, container_id):
    """
    Step 3: Publish the processed reel.
    This makes the reel visible on the Instagram account.
    
    Returns:
        dict: Response from Instagram API with the media ID
    """
    url = f"{GRAPH_API_BASE}/{ig_business_account_id}/media_publish"
    
    payload = {
        "creation_id": container_id,
        "access_token": access_token,
    }
    
    print("   📱 Publishing reel...")
    response = requests.post(url, data=payload, timeout=60)
    
    if response.status_code != 200:
        error_data = response.json().get("error", {})
        error_msg = error_data.get("message", response.text)
        raise RuntimeError(f"Failed to publish reel: {error_msg}")
    
    data = response.json()
    print(f"   🎉 Reel published! Media ID: {data.get('id')}")
    return data


def post_reel(access_token, ig_business_account_id, video_url, caption):
    """
    Complete reel posting pipeline:
    1. Create media container
    2. Wait for processing
    3. Publish the reel
    
    Args:
        access_token: Valid Instagram Graph API access token
        ig_business_account_id: Instagram Business Account ID
        video_url: Publicly accessible URL of the video
        caption: Instagram caption with hashtags
    
    Returns:
        dict: Response from Instagram API
    """
    # Validate inputs
    if not access_token:
        raise ValueError("Access token is required")
    if not ig_business_account_id:
        raise ValueError("Instagram Business Account ID is required")
    if not video_url:
        raise ValueError("Video URL is required")
    if not caption:
        raise ValueError("Caption is required")
    
    print(f"   🔗 Video URL: {video_url[:60]}...")
    print(f"   📝 Caption length: {len(caption)} chars")
    
    # Step 1: Create container
    container_id = create_media_container(
        access_token, ig_business_account_id, video_url, caption
    )
    
    # Step 2: Wait for processing
    wait_for_processing(access_token, container_id)
    
    # Step 3: Publish
    result = publish_reel(
        access_token, ig_business_account_id, container_id
    )
    
    return result


if __name__ == "__main__":
    print("This module is used by main.py. Run main.py instead.")
