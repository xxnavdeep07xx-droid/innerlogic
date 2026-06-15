#!/usr/bin/env python3
"""
Image Generator — Fetches dark cinematic background images.
Uses Pexels API (free, requires API key) for stunning dark photos.
Falls back to dark gradient if API is unavailable.
"""

import requests
import time
import random
import os
from urllib.parse import quote as url_encode


# Pexels API endpoint
PEXELS_API_URL = "https://api.pexels.com/v1/search"

# Search terms for dark cinematic photos
DARK_SEARCH_TERMS = [
    "dark cinematic landscape",
    "moody forest fog",
    "dark ocean waves",
    "storm clouds dramatic",
    "dark mountain night",
    "abandoned cathedral",
    "dark lake reflection",
    "misty forest path",
    "dramatic sunset silhouette",
    "dark cave light",
    "ancient ruins dark",
    "dark ocean horizon",
    "moody night sky stars",
    "dark desert night",
    "foggy mountain dawn",
    "dark waterfall",
    "mysterious forest dark",
    "lighthouse storm dark",
    "dark river mist",
    "abandoned castle dark",
    "snow mountain dark",
    "dark alley night",
    "old library dark",
    "dark bridge fog",
    "lonely tree storm",
]

# Category-specific search terms
CATEGORY_SEARCH_TERMS = {
    "stoicism": ["marble statue dark", "roman architecture moody", "stone columns dark"],
    "existentialism": ["empty void dark", "solitary figure dark", "abyss dark"],
    "eastern": ["zen garden dark", "bamboo forest mist", "chinese painting moody"],
    "psychology": ["mirror dark reflection", "maze dark", "eye close dark"],
    "mysticism": ["candle dark room", "sacred light dark", "stained glass dark"],
    "classical": ["greek temple dark", "ancient ruins night", "marble dark"],
    "transcendentalism": ["wilderness dark", "forest sunlight dark", "mountain dawn"],
    "romanticism": ["painting landscape dark", "castle moonlight", "storm sea"],
    "renaissance": ["cathedral dark", "painting dark moody", "chiaroscuro"],
}

# Minimum image dimensions for Instagram Reels
MIN_WIDTH = 1080
MIN_HEIGHT = 1920


def fetch_from_pexels(api_key, search_query, temp_dir):
    """
    Fetch a dark cinematic photo from Pexels API.
    
    Args:
        api_key: Pexels API key
        search_query: Search term for the image
        temp_dir: Directory to save the image
    
    Returns:
        str: Path to the downloaded image, or None if failed
    """
    headers = {"Authorization": api_key}
    params = {
        "query": search_query,
        "per_page": 15,
        "orientation": "portrait",
        "size": "large",
    }
    
    try:
        response = requests.get(PEXELS_API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        photos = data.get("photos", [])
        if not photos:
            return None
        
        # Filter for high-resolution portrait photos
        suitable = [
            p for p in photos
            if p["width"] >= MIN_WIDTH and p["height"] >= MIN_HEIGHT
        ]
        
        # If no exact match, use any photo (FFmpeg will resize)
        if not suitable:
            suitable = photos
        
        if not suitable:
            return None
        
        # Pick a random photo
        photo = random.choice(suitable)
        image_url = photo["src"]["large2x"] or photo["src"]["large"]
        
        # Download the image
        output_path = os.path.join(temp_dir, "background.jpg")
        img_response = requests.get(image_url, timeout=60, stream=True)
        img_response.raise_for_status()
        
        with open(output_path, "wb") as f:
            for chunk in img_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(output_path)
        if file_size > 10000:
            print(f"   ✅ Image from Pexels ({file_size / 1024:.0f} KB)")
            return output_path
        
    except Exception as e:
        print(f"   ⚠️  Pexels API error: {e}")
    
    return None


def generate_image(quote_data, temp_dir, width=1080, height=1920):
    """
    Generate a dark cinematic background image.
    
    Strategy:
    1. Try Pexels API (if PEXELS_API_KEY is set)
    2. Try Pollinations.ai (free AI generation)
    3. Fall back to dark gradient
    
    Args:
        quote_data: Dict with 'text', 'author', 'category' keys
        temp_dir: Directory to save the image
        width: Image width (default 1080 for Instagram Reels)
        height: Image height (default 1920 for Instagram Reels)
    
    Returns:
        str: Path to the downloaded image file
    """
    category = quote_data.get("category", "philosophy")
    
    # Build search query
    category_terms = CATEGORY_SEARCH_TERMS.get(category, [])
    if category_terms:
        search_query = random.choice(category_terms)
    else:
        search_query = random.choice(DARK_SEARCH_TERMS)
    
    print(f"   🎨 Searching for: {search_query}")
    
    # Method 1: Try Pexels API
    pexels_key = os.environ.get("PEXELS_API_KEY", "")
    if pexels_key:
        print(f"   🔗 Trying Pexels API...")
        result = fetch_from_pexels(pexels_key, search_query, temp_dir)
        if result:
            return result
    
    # Method 2: Try Pollinations.ai (free AI image generation)
    print(f"   🔗 Trying Pollinations.ai...")
    result = _fetch_from_pollinations(quote_data, temp_dir, width, height)
    if result:
        return result
    
    # Method 3: Dark gradient fallback
    print("   🔄 All methods failed — creating dark gradient fallback...")
    output_path = os.path.join(temp_dir, "background.jpg")
    _create_fallback_image(output_path, width, height)
    return output_path


def _fetch_from_pollinations(quote_data, temp_dir, width, height):
    """Try to generate an AI image using Pollinations.ai."""
    subjects = [
        "dark cinematic landscape with dramatic clouds",
        "moody foggy forest with deep shadows",
        "dark ocean waves under stormy sky",
        "abandoned cathedral with light streaming through",
        "dark mountain lake at twilight",
        "mysterious dark cave with single light source",
        "dark dramatic cliff edge at sunset",
    ]
    
    subject = random.choice(subjects)
    category = quote_data.get("category", "philosophy")
    
    prompt = f"dark cinematic painting of {subject}, dramatic chiaroscuro lighting, deep shadows, moody atmosphere, film noir aesthetic, oil on canvas, masterpiece"
    
    if category == "eastern":
        prompt = f"dark ink wash painting of {subject}, zen minimalist, japanese art style, moody atmospheric"
    elif category == "stoicism":
        prompt = f"dark classical painting of {subject}, roman marble, stoic, dramatic lighting, oil painting"
    
    encoded_prompt = url_encode(prompt)
    image_url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={width}&height={height}&nologo=true&seed={random.randint(1, 999999)}"
    )
    
    output_path = os.path.join(temp_dir, "background.jpg")
    
    for attempt in range(2):
        try:
            response = requests.get(image_url, timeout=90, stream=True)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                file_size = os.path.getsize(output_path)
                if file_size > 10000:
                    print(f"   ✅ AI image from Pollinations ({file_size / 1024:.0f} KB)")
                    return output_path
            else:
                print(f"   ⚠️  Pollinations returned {response.status_code}")
        except Exception as e:
            print(f"   ⚠️  Pollinations attempt {attempt + 1} failed: {e}")
        time.sleep(3)
    
    return None


def _create_fallback_image(output_path, width=1080, height=1920):
    """Create a dark gradient image as fallback when all methods fail."""
    try:
        from PIL import Image, ImageDraw
        
        img = Image.new("RGB", (width, height), (10, 10, 15))
        draw = ImageDraw.Draw(img)
        
        # Create a subtle dark gradient
        for y in range(height):
            r = int(10 + (y / height) * 15)
            g = int(10 + (y / height) * 8)
            b = int(15 + (y / height) * 25)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Add a subtle vignette effect
        from PIL import ImageFilter
        vignette = Image.new("RGB", (width, height), (0, 0, 0))
        v_draw = ImageDraw.Draw(vignette)
        center_x, center_y = width // 2, height // 2
        for r in range(max(width, height) // 2, 0, -1):
            alpha = int(255 * (1 - (r / (max(width, height) / 2)) ** 2))
            v_draw.ellipse(
                [center_x - r, center_y - r, center_x + r, center_y + r],
                fill=(alpha, alpha, alpha)
            )
        
        # Blend vignette with gradient
        img = Image.blend(img, vignette, 0.3)
        img.save(output_path, "JPEG", quality=95)
        print(f"   ✅ Dark gradient with vignette created")
        
    except ImportError:
        # If Pillow is not available, create a minimal valid JPEG
        import base64
        minimal_jpeg = base64.b64decode(
            "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkS"
            "Ew8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJ"
            "CQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
            "MjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8AKwA//9k="
        )
        with open(output_path, "wb") as f:
            f.write(minimal_jpeg)
        print(f"   ✅ Minimal fallback image created")


if __name__ == "__main__":
    test_quote = {"text": "Test quote", "author": "Test", "category": "stoicism"}
    path = generate_image(test_quote, "temp")
    print(f"Image saved to: {path}")
