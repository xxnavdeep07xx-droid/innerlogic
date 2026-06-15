#!/usr/bin/env python3
"""
Quote Scraper — Fetches unique philosophical/psychological quotes from free sources.
No API keys needed! Scrapes from publicly accessible quote websites.

Sources (in order of priority):
1. AzQuotes — Huge philosophical collection, 25 quotes per topic page
2. Goodreads Quotes — Curated quotes with ratings, deep collection
3. Built-in collection — 130+ pre-written quotes as fallback

Deduplicates against used quotes using MD5 hashing.
"""

import requests
import json
import os
import re
import time
import random
import hashlib
from datetime import datetime
from html import unescape


# ─── Configuration ────────────────────────────────────────────────────────────

MIN_QUOTE_LENGTH = 20
MAX_QUOTE_LENGTH = 300

# AzQuotes topic pages — philosophical/psychological themes
AZQUOTES_TOPICS = [
    "philosophy", "existentialism", "stoicism", "psychology",
    "wisdom", "consciousness", "truth", "meaning-of-life",
    "suffering", "freedom", "death", "soul",
    "mind", "reality", "purpose", "silence",
    "solitude", "fear", "courage", "insanity",
    "knowledge", "belief", "destiny", "doubt",
    "inner-self", "self-awareness", "darkness", "pain",
    "human-nature", "morality", "absurdity", "despair",
    "enlightenment", "imperfection", "acceptance", "change",
    "time", "memory", "loss", "resilience",
]

# Goodreads quote tags
GOODREADS_TAGS = [
    "philosophy", "existentialism", "stoicism", "psychology",
    "wisdom", "truth", "life", "death",
    "suffering", "freedom", "consciousness", "mind",
    "inspirational", "spirituality", "deep", "meaning",
]

# HTTP headers to mimic a real browser
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

# ─── Used Quotes Tracking ────────────────────────────────────────────────────

USED_QUOTES_HASHES = set()


def _hash_quote(text):
    """Create a hash of normalized quote text for deduplication."""
    normalized = re.sub(r'[^\w\s]', '', text.lower().strip())
    normalized = re.sub(r'\s+', ' ', normalized)
    return hashlib.md5(normalized.encode()).hexdigest()


def load_used_hashes(used_file):
    """Load previously used quote hashes."""
    global USED_QUOTES_HASHES

    if not os.path.exists(used_file):
        USED_QUOTES_HASHES = set()
        return

    try:
        with open(used_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            USED_QUOTES_HASHES = set(data.get("hashes", []))
        print(f"   📋 Loaded {len(USED_QUOTES_HASHES)} previously used quotes")
    except (json.JSONDecodeError, KeyError):
        USED_QUOTES_HASHES = set()


def save_used_hash(used_file, quote_hash, quote_text, author, source):
    """Save a new used quote hash."""
    if not os.path.exists(used_file):
        data = {"hashes": [], "quotes": []}
    else:
        try:
            with open(used_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {"hashes": [], "quotes": []}

    data["hashes"].append(quote_hash)
    data["quotes"].append({
        "hash": quote_hash,
        "text": quote_text[:100],
        "author": author,
        "source": source,
        "used_at": datetime.now().isoformat()
    })

    # Keep the file from growing too large
    if len(data["hashes"]) > 500:
        data["hashes"] = data["hashes"][-500:]
        data["quotes"] = data["quotes"][-500:]

    dir_name = os.path.dirname(used_file)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(used_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _is_duplicate(text):
    """Check if a quote has already been used."""
    return _hash_quote(text) in USED_QUOTES_HASHES


def _is_valid_quote(quote_text):
    """Check if a quote meets quality criteria."""
    if len(quote_text) < MIN_QUOTE_LENGTH or len(quote_text) > MAX_QUOTE_LENGTH:
        return False

    word_count = len(quote_text.split())
    if word_count < 4:
        return False

    # Skip questions, requests, and URLs
    bad_starters = [
        "how do", "what do", "why do", "can someone", "help me",
        "does anyone", "what is the", "how can i", "i need",
        "looking for", "recommend me", "where can",
    ]
    if any(quote_text.lower().startswith(q) for q in bad_starters):
        return False

    if "http://" in quote_text or "https://" in quote_text:
        return False

    # Skip if mostly special characters
    special_count = sum(1 for c in quote_text if not c.isalnum() and c not in ' .,;:!?\'"-—')
    if special_count > len(quote_text) * 0.2:
        return False

    # Skip if too few unique words
    unique_words = set(quote_text.lower().split())
    if len(unique_words) < 4:
        return False

    return True


def _categorize_quote(text):
    """Assign a category based on quote content."""
    text_lower = text.lower()

    if any(w in text_lower for w in ["stoic", "marcus", "seneca", "epictetus", "virtue", "duty"]):
        return "stoicism"
    elif any(w in text_lower for w in ["nietzsche", "camus", "sartre", "kierkegaard", "absurd", "existential", "existence"]):
        return "existentialism"
    elif any(w in text_lower for w in ["buddha", "zen", "tao", "mindful", "meditat", "impermanence"]):
        return "eastern"
    elif any(w in text_lower for w in ["jung", "unconscious", "shadow", "psyche", "freud", "neurosis", "ego"]):
        return "psychology"
    elif any(w in text_lower for w in ["socrates", "plato", "aristotle", "reason", "logic"]):
        return "classical"
    elif any(w in text_lower for w in ["meaning", "purpose", "life", "death", "mortal"]):
        return "philosophy"
    elif any(w in text_lower for w in ["love", "heart", "passion", "beauty"]):
        return "romanticism"
    elif any(w in text_lower for w in ["create", "art", "imagination", "inspire"]):
        return "creativity"
    else:
        return "wisdom"


# ─── AzQuotes Scraper ────────────────────────────────────────────────────────

def _scrape_azquotes(topic):
    """
    Scrape quotes from AzQuotes topic page.
    Returns up to 25 quotes per page. No API key needed.

    Args:
        topic: Topic slug (e.g., 'philosophy', 'stoicism')

    Returns:
        list: List of dicts with 'text' and 'author' keys
    """
    url = f"https://www.azquotes.com/quotes/topics/{topic}.html"

    try:
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=20)
        if response.status_code != 200:
            return []

        html = response.text
        quotes = []

        # AzQuotes uses <a class="title"> for quote text
        # and <a class="author"> for author name
        quote_matches = re.findall(
            r'<a[^>]*class="title"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        author_matches = re.findall(
            r'<a[^>]*class="author"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )

        for i, raw_quote in enumerate(quote_matches):
            # Clean HTML
            clean_quote = unescape(re.sub(r'<[^>]+>', '', raw_quote)).strip()

            # Get matching author
            if i < len(author_matches):
                clean_author = unescape(re.sub(r'<[^>]+>', '', author_matches[i])).strip()
            else:
                clean_author = "Unknown"

            # Remove trailing comma from author (AzQuotes adds book titles after comma)
            clean_author = clean_author.split(",")[0].strip()

            if _is_valid_quote(clean_quote):
                quotes.append({
                    "text": clean_quote,
                    "author": clean_author,
                })

        return quotes

    except Exception as e:
        print(f"      ⚠️  AzQuotes error for '{topic}': {e}")
        return []


# ─── Goodreads Scraper ───────────────────────────────────────────────────────

def _scrape_goodreads(tag):
    """
    Scrape quotes from a Goodreads quotes page by tag.
    Returns up to 30 quotes per page. No API key needed.

    Args:
        tag: Tag name (e.g., 'philosophy', 'stoicism')

    Returns:
        list: List of dicts with 'text' and 'author' keys
    """
    url = f"https://www.goodreads.com/quotes/tag/{tag}"

    try:
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=20)
        if response.status_code != 200:
            return []

        html = response.text
        quotes = []

        # Goodreads format:
        # <div class="quoteText"> "Quote" — <a>Author</a> </div>
        # We extract quote text and author separately

        quote_blocks = re.findall(
            r'class="quoteText"[^>]*>(.*?)</div>',
            html, re.DOTALL
        )

        for block in quote_blocks:
            # Extract the quote text (before the dash/author)
            # Goodreads uses &ldquo; and &rdquo; for quotes, and &mdash; for dash
            raw = unescape(block)

            # Pattern: "Quote text" — Author Name
            m = re.match(
                r'[\u201c"\s]*(.+?)[\u201d"\s]*\s*[\u2014—–-]+\s*(.+)',
                raw, re.DOTALL
            )

            if m:
                quote_text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                author_part = re.sub(r'<[^>]+>', '', m.group(2)).strip()
                # Clean author — remove trailing commas, book titles
                author = author_part.split(",")[0].strip().split("\n")[0].strip()
            else:
                # Try without dash — clean everything
                quote_text = re.sub(r'<[^>]+>', '', raw).strip()
                author = "Unknown"

            # Remove surrounding quotes
            quote_text = quote_text.strip('\u201c\u201d"')

            if _is_valid_quote(quote_text):
                quotes.append({
                    "text": quote_text,
                    "author": author,
                })

        return quotes

    except Exception as e:
        print(f"      ⚠️  Goodreads error for '{tag}': {e}")
        return []


# ─── Main Scrape Function ────────────────────────────────────────────────────

def pick_quote_from_web(used_file):
    """
    Main function: Scrape free quote websites for a unique philosophical quote.

    Strategy:
    1. Scrape AzQuotes (random philosophical topics) — 25 quotes per page
    2. Scrape Goodreads (philosophical tags) — 30 quotes per page
    3. Fall back to built-in 130+ quotes collection

    No API keys needed for any source!

    Args:
        used_file: Path to the used quotes tracking file

    Returns:
        dict: Quote object with 'text', 'author', 'category', 'source' keys
    """
    load_used_hashes(used_file)

    all_candidates = []

    # ── Source 1: AzQuotes ────────────────────────────────────────────────
    print("   📚 Scraping AzQuotes for philosophical quotes...")
    az_topics = random.sample(AZQUOTES_TOPICS, min(3, len(AZQUOTES_TOPICS)))

    for topic in az_topics:
        print(f"      🔍 Checking '{topic}'...")
        quotes = _scrape_azquotes(topic)

        for q in quotes:
            if not _is_duplicate(q["text"]):
                q["category"] = _categorize_quote(q["text"])
                q["source"] = f"azquotes.com ({topic})"
                all_candidates.append(q)

        if quotes:
            print(f"      ✅ Found {len(quotes)} quotes, {sum(1 for q in quotes if not _is_duplicate(q['text']))} new")
        time.sleep(0.5)  # Be polite

    if all_candidates:
        print(f"   📊 AzQuotes: {len(all_candidates)} unique candidates")

    # ── Source 2: Goodreads (if not enough from AzQuotes) ─────────────────
    if len(all_candidates) < 15:
        print("   📖 Scraping Goodreads for more quotes...")
        gr_tags = random.sample(GOODREADS_TAGS, min(3, len(GOODREADS_TAGS)))

        for tag in gr_tags:
            print(f"      🔍 Checking #{tag}...")
            quotes = _scrape_goodreads(tag)

            for q in quotes:
                if not _is_duplicate(q["text"]):
                    q["category"] = _categorize_quote(q["text"])
                    q["source"] = f"goodreads.com (#{tag})"
                    all_candidates.append(q)

            if quotes:
                print(f"      ✅ Found {len(quotes)} quotes, {sum(1 for q in quotes if not _is_duplicate(q['text']))} new")
            time.sleep(1)  # Be polite

        if all_candidates:
            print(f"   📊 Total unique candidates: {len(all_candidates)}")

    # ── Fallback: Built-in collection ─────────────────────────────────────
    if not all_candidates:
        print("   ⚠️  No unique quotes found online — using built-in collection")
        return _fallback_builtin_quote(used_file)

    # Pick a random quote weighted toward shorter, punchier quotes
    # Shorter quotes work better for 15-second reels
    for candidate in all_candidates:
        candidate["_weight"] = max(1, 120 - len(candidate["text"]))

    total_weight = sum(c["_weight"] for c in all_candidates)
    r = random.uniform(0, total_weight)
    cumulative = 0
    chosen = all_candidates[0]
    for c in all_candidates:
        cumulative += c["_weight"]
        if cumulative >= r:
            chosen = c
            break

    # Build final quote
    final_quote = {
        "text": chosen["text"],
        "author": chosen["author"],
        "category": chosen.get("category", "wisdom"),
        "source": chosen.get("source", "web"),
    }

    # Track the used quote
    quote_hash = _hash_quote(chosen["text"])
    USED_QUOTES_HASHES.add(quote_hash)
    save_used_hash(used_file, quote_hash, chosen["text"], chosen["author"], chosen.get("source", ""))

    print(f"   🎯 Picked from {len(all_candidates)} candidates")
    print(f"   🔗 Source: {chosen.get('source', 'web')}")

    return final_quote


def _fallback_builtin_quote(used_file):
    """Fall back to the built-in quotes collection if web scraping fails."""
    from quote_picker import pick_quote

    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "quotes.json"),
        "data/quotes.json",
    ]

    quotes_file = None
    for path in possible_paths:
        if os.path.exists(path):
            quotes_file = path
            break

    if not quotes_file:
        return {
            "text": "The only true wisdom is in knowing you know nothing.",
            "author": "Socrates",
            "category": "classical",
            "source": "built-in fallback",
        }

    quote = pick_quote(quotes_file, used_file)
    quote["source"] = "built-in collection"
    return quote


# Backward compatibility: keep the old function name working
def pick_quote_from_reddit(used_file):
    """Legacy function name — now scrapes from free web sources instead of Reddit."""
    return pick_quote_from_web(used_file)


if __name__ == "__main__":
    quote = pick_quote_from_web("temp/used_quotes.json")
    print(f"\n📝 \"{quote['text'][:80]}...\"")
    print(f"   — {quote['author']} ({quote['category']})")
    print(f"   Source: {quote.get('source', 'unknown')}")
