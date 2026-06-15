#!/usr/bin/env python3
"""
Fonts Setup — Downloads high-quality Google Fonts for the reel pipeline.
Fonts are downloaded at runtime and cached in the fonts/ directory.
No API keys needed — direct Google Fonts GitHub raw URLs.

Font choices for "innerlogic" (dark cinematic philosophical aesthetic):
  - Quote text:  Cormorant Garamond (variable) — elegant literary serif
  - Author name: Montserrat (variable, italic)  — clean modern sans-serif contrast
"""

import os
import logging
import requests

logger = logging.getLogger("innerlogic")

# ─── Font Download URLs ────────────────────────────────────────────────────────
# Google Fonts now uses variable fonts with [wght] in the filename.
# URL-encoded: %5B = [  %5D = ]
# These are direct raw.githubusercontent.com links — no API key needed.

FONT_DOWNLOADS = [
    # (local_filename, remote_url, role_description)
    (
        "CormorantGaramond[wght].ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf",
        "Quote text (Cormorant Garamond variable)"
    ),
    (
        "CormorantGaramond-Italic[wght].ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/cormorantgaramond/CormorantGaramond-Italic%5Bwght%5D.ttf",
        "Quote italic (Cormorant Garamond Italic variable)"
    ),
    (
        "Montserrat[wght].ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",
        "Author text (Montserrat variable)"
    ),
    (
        "Montserrat-Italic[wght].ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat-Italic%5Bwght%5D.ttf",
        "Author italic (Montserrat Italic variable)"
    ),
]


def ensure_fonts(fonts_dir):
    """
    Download required font files if they don't already exist.
    
    Uses Google Fonts variable font files from GitHub. These support
    multiple weights in a single file — FFmpeg/libass can use them
    with the Bold/Italic flags in ASS styles.
    
    Args:
        fonts_dir: Directory to store font files (created if needed)
    
    Returns:
        dict: Mapping of font role → full file path (or system font name as fallback)
            {
                "quote": "/path/to/CormorantGaramond[wght].ttf",
                "author": "/path/to/Montserrat-Italic[wght].ttf",
            }
    """
    os.makedirs(fonts_dir, exist_ok=True)
    
    # Check which files need downloading
    needed = []
    for filename, url, desc in FONT_DOWNLOADS:
        filepath = os.path.join(fonts_dir, filename)
        if not os.path.exists(filepath):
            needed.append((filename, url, desc, filepath))
    
    if not needed:
        logger.info(f"✅ All fonts already cached in {fonts_dir}")
    else:
        logger.info(f"⬇️  Downloading {len(needed)} font files from Google Fonts...")
        success = 0
        failed = 0
        
        for filename, url, desc, filepath in needed:
            try:
                logger.info(f"   ⬇️  {desc}")
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                
                size_kb = len(resp.content) / 1024
                logger.info(f"   ✅ Downloaded {filename} ({size_kb:.0f} KB)")
                success += 1
                
            except Exception as e:
                logger.warning(f"   ❌ Failed: {e}")
                failed += 1
        
        if success > 0:
            logger.info(f"✅ Fonts: {success} downloaded, {failed} failed")
        if failed > 0:
            logger.warning(f"⚠️  {failed} fonts failed — will use system font fallback")
    
    # Build the font paths mapping
    # IMPORTANT: Use ABSOLUTE paths — FFmpeg/libass needs full paths for ASS Fontname
    # Quote: Cormorant Garamond variable (supports Regular→Bold via weight axis)
    # Author: Montserrat Italic variable (supports Light→Bold italic)
    quote_path = os.path.abspath(os.path.join(fonts_dir, "CormorantGaramond[wght].ttf"))
    author_path = os.path.abspath(os.path.join(fonts_dir, "Montserrat-Italic[wght].ttf"))
    
    if os.path.exists(quote_path) and os.path.exists(author_path):
        font_paths = {
            "quote": quote_path,
            "author": author_path,
        }
        logger.info(f"🔤 Quote font:  Cormorant Garamond (variable)")
        logger.info(f"🔤 Author font: Montserrat Italic (variable)")
    else:
        # Fallback: try alternative names or use system font names
        # Check for any Cormorant or Montserrat files
        alt_quote = os.path.abspath(os.path.join(fonts_dir, "CormorantGaramond-Italic[wght].ttf"))
        alt_author = os.path.abspath(os.path.join(fonts_dir, "Montserrat[wght].ttf"))
        
        if os.path.exists(alt_quote) and os.path.exists(alt_author):
            font_paths = {
                "quote": alt_quote,
                "author": alt_author,
            }
            logger.info(f"🔤 Quote font:  Cormorant Garamond Italic (variable)")
            logger.info(f"🔤 Author font: Montserrat (variable)")
        else:
            logger.warning("⚠️  Custom fonts unavailable — using system font fallback")
            font_paths = {
                "quote": "Cormorant Garamond",
                "author": "Montserrat",
            }
    
    return font_paths


if __name__ == "__main__":
    import sys
    test_dir = sys.argv[1] if len(sys.argv) > 1 else "fonts"
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = ensure_fonts(test_dir)
    print(f"\nFont paths: {result}")
